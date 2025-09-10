import os, asyncio, aiohttp, hmac, hashlib, base64, time, json
from datetime import datetime, timedelta
from backend.utils.logger import get_logger
import aiosqlite

log = get_logger("AngelEnhanced")
ANGEL_BASE = "https://apiconnect.angelbroking.com/rest/secure/"
DB_PATH = "./ajxai.db"

class AngelSession:
    def __init__(self):
        self.jwt_token = None
        self.refresh_token = None
        self.feed_token = None
        self.expires_at = None
        
    async def _init_db(self):
        """Create tokens table if not exists"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS angel_tokens (
                    id INTEGER PRIMARY KEY,
                    jwt_token TEXT,
                    refresh_token TEXT,
                    feed_token TEXT,
                    expires_at TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    def _sha256(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _totp(self, secret: str) -> str:
        timestep = int(time.time() // 30)
        key = base64.b32decode(secret.upper())
        h = hmac.new(key, timestep.to_bytes(8, "big"), hashlib.sha1).digest()
        o = h[-1] & 0x0F
        code = (int.from_bytes(h[o:o+4], "big") & 0x7FFFFFFF) % 1_000_000
        return f"{code:06d}"
    
    async def _load_tokens(self):
        """Load existing tokens from DB"""
        await self._init_db()
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT jwt_token, refresh_token, feed_token, expires_at FROM angel_tokens ORDER BY id DESC LIMIT 1") as cursor:
                row = await cursor.fetchone()
                if row:
                    self.jwt_token, self.refresh_token, self.feed_token, expires_str = row
                    if expires_str:
                        self.expires_at = datetime.fromisoformat(expires_str)
    
    async def _save_tokens(self):
        """Save tokens to DB"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO angel_tokens (id, jwt_token, refresh_token, feed_token, expires_at)
                VALUES (1, ?, ?, ?, ?)
            """, (self.jwt_token, self.refresh_token, self.feed_token, 
                  self.expires_at.isoformat() if self.expires_at else None))
            await db.commit()
    
    async def ensure_valid_token(self):
        """Auto-refresh token if expired or missing"""
        await self._load_tokens()
        
        # Check if token exists and is valid
        if self.jwt_token and self.expires_at and datetime.now() < self.expires_at:
            log.info("Using cached Angel token")
            return self.jwt_token
            
        # Need fresh login
        log.info("Angel token expired/missing, logging in...")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-APIKey": os.getenv("ANGEL_TRADING_KEY")
        }
        
        payload = {
            "clientcode": os.getenv("ANGEL_CLIENT_ID"),
            "password": self._sha256(os.getenv("ANGEL_MPIN")),
            "totp": self._totp(os.getenv("ANGEL_TOTP_SECRET")),
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ANGEL_BASE.replace('/secure/', '/auth/angelbroking/user/v1/')}loginByPassword", 
                                  json=payload, headers=headers, timeout=15) as response:
                data = await response.json()
                
                if not data.get("status"):
                    raise RuntimeError(f"Angel login failed: {data}")
                
                token_data = data["data"]
                self.jwt_token = token_data["jwtToken"]
                self.refresh_token = token_data.get("refreshToken")
                self.feed_token = token_data.get("feedToken")
                
                # Token valid for 24 hours
                self.expires_at = datetime.now() + timedelta(hours=23, minutes=30)
                
                await self._save_tokens()
                log.info("Angel login successful, token cached")
                return self.jwt_token

# Global instance
angel = AngelSession()

async def get_headers():
    """Get authenticated headers with auto-refresh"""
    token = await angel.ensure_valid_token()
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-APIKey": os.getenv("ANGEL_TRADING_KEY"),
        "Authorization": f"Bearer {token}"
    }

async def get_latest_tick(symbol: str):
    """Get latest tick data for a symbol"""
    headers = await get_headers()
    
    # Symbol mapping
    symbol_tokens = {
        "NIFTY50": "99926000",
        "BANKNIFTY": "99926009",
        "SENSEX": "99919000"
    }
    
    token = symbol_tokens.get(symbol, symbol)
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "ONE_MINUTE",
            "fromdate": datetime.now().strftime("%Y-%m-%d 09:15"),
            "todate": datetime.now().strftime("%Y-%m-%d 15:30")
        }
        async with session.post(f"{ANGEL_BASE}getCandleData", 
                              json=payload, headers=headers) as response:
            data = await response.json()
            if data.get("status") and data.get("data"):
                latest = data["data"][-1]  # Get most recent candle
                return {
                    "symbol": symbol,
                    "open": float(latest[1]),
                    "high": float(latest[2]),
                    "low": float(latest[3]),
                    "close": float(latest[4]),
                    "volume": int(latest[5]),
                    "timestamp": latest[0]
                }
            return None

async def test_market_data():
    """Test live NIFTY 50 data fetch"""
    try:
        tick = await get_latest_tick("NIFTY50")
        if tick:
            log.info(f"NIFTY 50 Latest: {tick['close']} (Volume: {tick['volume']})")
            return tick
        else:
            log.warning("No NIFTY 50 data received")
            return None
    except Exception as e:
        log.error(f"Market data test failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_market_data())
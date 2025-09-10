import httpx
import pyotp
import json
import logging
from typing import Dict, Any, Optional
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class AngelOneAPI:
    """Angel One SmartAPI integration for live market data"""
    
    def __init__(self):
        self.base_url = "https://apiconnect.angelbroking.com"
        self.client_id = os.getenv('ANGEL_CLIENT_ID')
        self.mpin = os.getenv('ANGEL_MPIN')
        self.totp_secret = os.getenv('ANGEL_TOTP_SECRET')
        
        # API Keys for different services
        self.trading_key = os.getenv('ANGEL_TRADING_KEY')
        self.publisher_key = os.getenv('ANGEL_PUBLISHER_KEY')
        self.market_key = os.getenv('ANGEL_MARKET_KEY')
        self.historical_key = os.getenv('ANGEL_HISTORICAL_KEY')
        
        self.auth_token = None
        self.feed_token = None
        self.refresh_token = None
        self.is_authenticated = False
        
        logger.info(f"Angel One API initialized with client: {self.client_id}")
    
    async def initialize(self):
        """Initialize and authenticate with Angel One API"""
        try:
            await self.login()
            await self.test_connection()
            logger.info("✅ Angel One API successfully initialized")
        except Exception as e:
            logger.error(f"❌ Angel One API initialization failed: {e}")
            raise
    
    def generate_totp(self) -> str:
        """Generate TOTP for Angel One authentication"""
        if not self.totp_secret:
            raise ValueError("TOTP secret not configured")
        
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()
    
    async def login(self):
        """Authenticate with Angel One API"""
        if not all([self.client_id, self.mpin, self.totp_secret]):
            raise ValueError("Missing Angel One credentials")
        
        totp_code = self.generate_totp()
        
        login_data = {
            "clientcode": self.client_id,
            "password": self.mpin,
            "totp": totp_code
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "192.168.1.1",
            "X-ClientPublicIP": "106.193.147.98",
            "X-MACAddress": "fe80::216:3eff:fe00:1",
            "X-PrivateKey": self.trading_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/rest/auth/angelbroking/user/v1/loginByPassword",
                json=login_data,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    self.auth_token = data['data']['jwtToken']
                    self.feed_token = data['data']['feedToken']
                    self.refresh_token = data['data']['refreshToken']
                    self.is_authenticated = True
                    logger.info("✅ Angel One authentication successful")
                else:
                    error_msg = data.get('message', 'Unknown error')
                    raise Exception(f"Login failed: {error_msg}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def test_connection(self):
        """Test Angel One API connection"""
        if not self.is_authenticated:
            raise Exception("Not authenticated")
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "192.168.1.1",
            "X-ClientPublicIP": "106.193.147.98",
            "X-MACAddress": "fe80::216:3eff:fe00:1",
            "X-PrivateKey": self.trading_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/rest/secure/angelbroking/user/v1/getProfile",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    logger.info(f"✅ Connection test passed - User: {data['data']['name']}")
                    return True
                else:
                    raise Exception(f"Profile fetch failed: {data.get('message')}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_nifty50_data(self) -> Dict[str, Any]:
        """Get live NIFTY 50 data"""
        if not self.is_authenticated:
            raise Exception("Not authenticated")
        
        # NIFTY 50 symbol for Angel One
        nifty_data = {
            "exchange": "NSE",
            "symboltoken": "99926000",  # NIFTY 50 token
            "symbol": "NIFTY"
        }
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "192.168.1.1",
            "X-ClientPublicIP": "106.193.147.98",
            "X-MACAddress": "fe80::216:3eff:fe00:1",
            "X-PrivateKey": self.market_key
        }
        
        request_data = {
            "exchange": nifty_data["exchange"],
            "symboltoken": nifty_data["symboltoken"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/rest/secure/angelbroking/market/v1/quote/",
                json=request_data,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    quote_data = data['data']
                    return {
                        "symbol": "NIFTY50",
                        "price": float(quote_data.get('ltp', 0)),
                        "change": float(quote_data.get('netchange', 0)),
                        "change_percent": float(quote_data.get('pchange', 0)),
                        "open": float(quote_data.get('open', 0)),
                        "high": float(quote_data.get('high', 0)),
                        "low": float(quote_data.get('low', 0)),
                        "volume": int(quote_data.get('volume', 0)),
                        "timestamp": datetime.now().isoformat(),
                        "source": "angel_one"
                    }
                else:
                    raise Exception(f"Quote fetch failed: {data.get('message')}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get market status"""
        if not self.is_authenticated:
            raise Exception("Not authenticated")
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "192.168.1.1",
            "X-ClientPublicIP": "106.193.147.98",
            "X-MACAddress": "fe80::216:3eff:fe00:1",
            "X-PrivateKey": self.market_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/rest/secure/angelbroking/market/v1/marketStatus",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return data['data']
                else:
                    raise Exception(f"Market status fetch failed: {data.get('message')}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
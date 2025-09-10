import httpx
import json
import logging
from typing import Dict, Any, Optional
import os
from datetime import datetime
import hashlib
import hmac
import time

logger = logging.getLogger(__name__)

class BinanceAPI:
    """Binance API integration for crypto data"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        self.is_connected = False
        
        logger.info("Binance API initialized")
    
    async def initialize(self):
        """Initialize Binance API connection"""
        try:
            await self.test_connection()
            logger.info("✅ Binance API successfully initialized")
        except Exception as e:
            logger.error(f"❌ Binance API initialization failed: {e}")
            # Don't raise - allow operation without API keys for public endpoints
            pass
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate signature for authenticated requests"""
        if not self.api_secret:
            raise ValueError("API secret required for authenticated requests")
        
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def test_connection(self):
        """Test Binance API connection"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v3/ping",
                timeout=30.0
            )
            
            if response.status_code == 200:
                self.is_connected = True
                logger.info("✅ Binance connection test passed")
                return True
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v3/exchangeInfo",
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_bitcoin_price(self) -> Dict[str, Any]:
        """Get Bitcoin live price data"""
        async with httpx.AsyncClient() as client:
            # Get 24hr ticker statistics
            response = await client.get(
                f"{self.base_url}/api/v3/ticker/24hr",
                params={"symbol": "BTCUSDT"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": "BTCUSDT",
                    "price": float(data['lastPrice']),
                    "change": float(data['priceChange']),
                    "change_percent": float(data['priceChangePercent']),
                    "open": float(data['openPrice']),
                    "high": float(data['highPrice']),
                    "low": float(data['lowPrice']),
                    "volume": float(data['volume']),
                    "quote_volume": float(data['quoteVolume']),
                    "timestamp": datetime.now().isoformat(),
                    "source": "binance"
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_top_cryptos(self, limit: int = 10) -> list:
        """Get top cryptocurrencies by volume"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v3/ticker/24hr",
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Filter USDT pairs and sort by quote volume
                usdt_pairs = [
                    item for item in data 
                    if item['symbol'].endswith('USDT') and float(item['quoteVolume']) > 0
                ]
                
                # Sort by quote volume (trading volume in USDT)
                sorted_pairs = sorted(
                    usdt_pairs, 
                    key=lambda x: float(x['quoteVolume']), 
                    reverse=True
                )
                
                # Return top N
                top_cryptos = []
                for item in sorted_pairs[:limit]:
                    top_cryptos.append({
                        "symbol": item['symbol'],
                        "price": float(item['lastPrice']),
                        "change_percent": float(item['priceChangePercent']),
                        "volume": float(item['quoteVolume']),
                        "source": "binance"
                    })
                
                return top_cryptos
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information (requires API key)"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required for account info")
        
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}"
        signature = self._generate_signature(query_string)
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        params = {
            "timestamp": timestamp,
            "signature": signature
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v3/account",
                headers=headers,
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_klines(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 24) -> list:
        """Get candlestick data"""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v3/klines",
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                raw_data = response.json()
                
                # Format kline data
                klines = []
                for kline in raw_data:
                    klines.append({
                        "open_time": int(kline[0]),
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5]),
                        "close_time": int(kline[6]),
                        "quote_volume": float(kline[7]),
                        "trades": int(kline[8])
                    })
                
                return klines
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
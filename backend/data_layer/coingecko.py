import httpx
import json
import logging
from typing import Dict, Any, Optional, List
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class CoinGeckoAPI:
    """CoinGecko API integration for crypto market data"""
    
    def __init__(self):
        self.base_url = os.getenv('COINGECKO_BASE', 'https://api.coingecko.com/api/v3')
        self.is_connected = False
        
        logger.info("CoinGecko API initialized")
    
    async def initialize(self):
        """Initialize CoinGecko API connection"""
        try:
            await self.test_connection()
            logger.info("✅ CoinGecko API successfully initialized")
        except Exception as e:
            logger.error(f"❌ CoinGecko API initialization failed: {e}")
            raise
    
    async def test_connection(self):
        """Test CoinGecko API connection"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/ping",
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('gecko_says') == '(V3) To the Moon!':
                    self.is_connected = True
                    logger.info("✅ CoinGecko connection test passed")
                    return True
                else:
                    raise Exception("Unexpected ping response")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_bitcoin_price(self) -> Dict[str, Any]:
        """Get Bitcoin price from CoinGecko"""
        params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd,inr',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/simple/price",
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                bitcoin_data = data.get('bitcoin', {})
                
                return {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "price_usd": bitcoin_data.get('usd'),
                    "price_inr": bitcoin_data.get('inr'),
                    "market_cap_usd": bitcoin_data.get('usd_market_cap'),
                    "volume_24h_usd": bitcoin_data.get('usd_24h_vol'),
                    "change_24h_percent": bitcoin_data.get('usd_24h_change'),
                    "timestamp": datetime.now().isoformat(),
                    "source": "coingecko"
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_top_cryptos(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top cryptocurrencies by market cap"""
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '24h'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/coins/markets",
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                top_cryptos = []
                for coin in data:
                    top_cryptos.append({
                        "id": coin.get('id'),
                        "symbol": coin.get('symbol', '').upper(),
                        "name": coin.get('name'),
                        "price_usd": coin.get('current_price'),
                        "market_cap": coin.get('market_cap'),
                        "market_cap_rank": coin.get('market_cap_rank'),
                        "volume_24h": coin.get('total_volume'),
                        "change_24h_percent": coin.get('price_change_percentage_24h'),
                        "image": coin.get('image'),
                        "source": "coingecko"
                    })
                
                return top_cryptos
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_global_data(self) -> Dict[str, Any]:
        """Get global cryptocurrency market data"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/global",
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                global_data = data.get('data', {})
                
                return {
                    "active_cryptocurrencies": global_data.get('active_cryptocurrencies'),
                    "markets": global_data.get('markets'),
                    "total_market_cap_usd": global_data.get('total_market_cap', {}).get('usd'),
                    "total_volume_24h_usd": global_data.get('total_volume', {}).get('usd'),
                    "market_cap_percentage": global_data.get('market_cap_percentage', {}),
                    "market_cap_change_24h_percentage": global_data.get('market_cap_change_percentage_24h_usd'),
                    "timestamp": datetime.now().isoformat(),
                    "source": "coingecko"
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def search_coins(self, query: str) -> List[Dict[str, Any]]:
        """Search for cryptocurrencies"""
        params = {'query': query}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search",
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                coins = data.get('coins', [])
                
                search_results = []
                for coin in coins[:10]:  # Limit to top 10 results
                    search_results.append({
                        "id": coin.get('id'),
                        "symbol": coin.get('symbol'),
                        "name": coin.get('name'),
                        "market_cap_rank": coin.get('market_cap_rank'),
                        "image": coin.get('large'),
                        "source": "coingecko"
                    })
                
                return search_results
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    async def get_price_history(self, coin_id: str = 'bitcoin', days: int = 7) -> Dict[str, Any]:
        """Get historical price data"""
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily' if days > 1 else 'hourly'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/coins/{coin_id}/market_chart",
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "coin_id": coin_id,
                    "prices": data.get('prices', []),
                    "market_caps": data.get('market_caps', []),
                    "total_volumes": data.get('total_volumes', []),
                    "days": days,
                    "source": "coingecko"
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
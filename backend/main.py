from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from dotenv import load_dotenv
from typing import Dict, Any
import asyncio
import logging

from data_layer.angel import AngelOneAPI
from data_layer.binance import BinanceAPI  
from data_layer.coingecko import CoinGeckoAPI

# Load environment variables
import sys
sys.path.append('..')
load_dotenv('../config/api_keys.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AJxAI Oracle Platform",
    description="Live-data oracle for market analysis and trading signals",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API clients
angel_api = None
binance_api = None
coingecko_api = None

@app.on_event("startup")
async def startup_event():
    """Initialize API connections on startup"""
    global angel_api, binance_api, coingecko_api
    
    logger.info("Initializing AJxAI Oracle Platform...")
    
    # Initialize Angel One API
    try:
        angel_api = AngelOneAPI()
        await angel_api.initialize()
        logger.info("✅ Angel One API initialized")
    except Exception as e:
        logger.error(f"❌ Angel One API failed: {e}")
    
    # Initialize Binance API
    try:
        binance_api = BinanceAPI()
        await binance_api.initialize()
        logger.info("✅ Binance API initialized")
    except Exception as e:
        logger.error(f"❌ Binance API failed: {e}")
    
    # Initialize CoinGecko API
    try:
        coingecko_api = CoinGeckoAPI()
        await coingecko_api.initialize()
        logger.info("✅ CoinGecko API initialized")
    except Exception as e:
        logger.error(f"❌ CoinGecko API failed: {e}")
    
    logger.info("🚀 AJxAI Oracle Platform ready!")

@app.get("/")
async def root():
    """Root endpoint with platform status"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AJxAI Oracle Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔮 AJxAI Oracle Platform</h1>
            <p>Live-data oracle for market analysis and trading signals</p>
            
            <h3>API Status</h3>
            <div id="status">Loading...</div>
            
            <h3>Quick Links</h3>
            <ul>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/api/market/nifty50">NIFTY 50 Data</a></li>
                <li><a href="/api/crypto/bitcoin">Bitcoin Price</a></li>
                <li><a href="/docs">API Documentation</a></li>
            </ul>
        </div>
        
        <script>
            fetch('/health')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    let html = '';
                    
                    Object.entries(data.apis).forEach(([api, status]) => {
                        const cssClass = status === 'healthy' ? 'success' : 'error';
                        html += `<div class="status ${cssClass}">${api}: ${status}</div>`;
                    });
                    
                    statusDiv.innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = '<div class="status error">Failed to load status</div>';
                });
        </script>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    apis = {
        "angel_one": "healthy" if angel_api and angel_api.is_authenticated else "error",
        "binance": "healthy" if binance_api and binance_api.is_connected else "error", 
        "coingecko": "healthy" if coingecko_api and coingecko_api.is_connected else "error"
    }
    
    overall_status = "healthy" if all(status == "healthy" for status in apis.values()) else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": "2025-09-10T12:00:00Z",
        "apis": apis
    }

@app.get("/api/market/nifty50")
async def get_nifty50():
    """Get NIFTY 50 live data from Angel One"""
    if not angel_api or not angel_api.is_authenticated:
        raise HTTPException(status_code=503, detail="Angel One API not available")
    
    try:
        data = await angel_api.get_nifty50_data()
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch NIFTY 50: {e}")

@app.get("/api/crypto/bitcoin")
async def get_bitcoin():
    """Get Bitcoin price from CoinGecko"""
    if not coingecko_api or not coingecko_api.is_connected:
        raise HTTPException(status_code=503, detail="CoinGecko API not available")
    
    try:
        data = await coingecko_api.get_bitcoin_price()
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Bitcoin: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=5000, 
        reload=True,
        log_level="info"
    )
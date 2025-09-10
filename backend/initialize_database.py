import asyncio
import aiosqlite
from backend.db import init_db
from backend.utils.logger import get_logger

log = get_logger("DBInit")

async def initialize_database():
    """Initialize SQLite database with all required tables"""
    try:
        # Initialize SQLAlchemy tables
        await init_db()
        log.info("✅ SQLAlchemy tables initialized")
        
        # Initialize additional tables for enhanced features
        async with aiosqlite.connect("./ajxai.db") as db:
            # Angel tokens table
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
            
            # Bot configuration table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    id INTEGER PRIMARY KEY,
                    key TEXT UNIQUE,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert default configuration
            await db.execute("""
                INSERT OR IGNORE INTO bot_config (key, value) VALUES 
                ('public_channel', '@AJxAI_Oracle'),
                ('admin_group', ''),
                ('api_id', ''),
                ('api_hash', ''),
                ('last_signal_id', '0')
            """)
            
            await db.commit()
            log.info("✅ Additional tables and config initialized")
        
        log.info("🎯 Database initialization complete")
        return True
        
    except Exception as e:
        log.error(f"❌ Database initialization failed: {e}")
        return False

async def add_sample_data():
    """Add sample data for testing"""
    try:
        async with aiosqlite.connect("./ajxai.db") as db:
            # Add sample signal
            await db.execute("""
                INSERT OR REPLACE INTO signals (
                    id, symbol, signal_type, confidence, target_price, stop_loss, 
                    reasoning, data_points_used, is_active, created_at
                ) VALUES (
                    1, 'NIFTY50', 'BUY', 0.85, 25000.0, 24500.0,
                    'Strong bullish momentum with high volume breakout above resistance', 
                    15, 1, datetime('now')
                )
            """)
            
            # Add sample article
            await db.execute("""
                INSERT OR REPLACE INTO articles (
                    id, source, category, title, summary, link, published_at, 
                    tickers, sentiment_score, created_at
                ) VALUES (
                    1, 'cnbc', 'markets', 'NIFTY 50 Reaches New Heights',
                    'Indian stock market continues bullish trend with strong institutional buying',
                    'https://example.com/news', datetime('now'), 'NIFTY50', 0.7, datetime('now')
                )
            """)
            
            # Add sample tick
            await db.execute("""
                INSERT OR REPLACE INTO ticks (
                    id, symbol, source, timestamp, open_price, high_price, 
                    low_price, close_price, volume, raw_data, created_at
                ) VALUES (
                    1, 'NIFTY50', 'angel', datetime('now'), 24900.0, 25100.0,
                    24850.0, 25050.0, 1250000, '{"test": true}', datetime('now')
                )
            """)
            
            await db.commit()
            log.info("✅ Sample data added for testing")
        
        return True
        
    except Exception as e:
        log.error(f"❌ Sample data creation failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(initialize_database())
    asyncio.run(add_sample_data())
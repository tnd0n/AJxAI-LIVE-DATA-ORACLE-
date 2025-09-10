import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User
from dotenv import load_dotenv
import aiosqlite

from backend.models import Signal, Tick, Article
from backend.data_layer.angel_enhanced import get_latest_tick, angel
from backend.data_layer.binance import BinanceAPI  
from backend.data_layer.coingecko import CoinGeckoAPI
from backend.utils.rate_limiter import throttle
from backend.utils.logger import get_logger

# Load environment variables
load_dotenv("config/api_keys.env")

log = get_logger("TelegramBot")

class AJxAITelegramBot:
    """AJxAI Telegram Bot for signals and market data"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.api_id = int(os.getenv('TELEGRAM_API_ID', '29506100'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH', 'a4f18c0a6fb07fe992b792ce6291524d')
        
        # Channel/Chat configuration
        self.public_channel = os.getenv('TELEGRAM_CHANNEL', '@ajxai1')
        self.admin_group = None  # To be set: AJxAI Ops group chat_id
        
        self.client: Optional[TelegramClient] = None
        self.is_running = False
        
        # Rate limiting: 20 messages per minute
        self.last_message_times = []
        
        # Data source instances
        self.binance = BinanceAPI()
        self.coingecko = CoinGeckoAPI()
        
        log.info("AJxAI Telegram Bot initialized")
    
    async def initialize(self, api_id: int, api_hash: str, admin_group_id: int = None):
        """Initialize Telegram client with credentials"""
        if not self.bot_token:
            log.error("❌ TELEGRAM_BOT_TOKEN not found in environment")
            return False
        
        try:
            self.api_id = api_id
            self.api_hash = api_hash
            self.admin_group = admin_group_id
            
            # Initialize Telegram client
            self.client = TelegramClient('ajxai_bot_session', api_id, api_hash)
            await self.client.start(bot_token=self.bot_token)
            
            # Register event handlers
            self._register_handlers()
            
            log.info(f"✅ AJxAI Telegram Bot initialized")
            log.info(f"📢 Public channel: {self.public_channel}")
            log.info(f"🔧 Admin group: {self.admin_group}")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Telegram bot initialization failed: {e}")
            return False
    
    def _register_handlers(self):
        """Register command and message handlers"""
        
        @self.client.on(events.NewMessage(pattern='/price'))
        async def price_handler(event):
            await self._handle_price_command(event)
        
        @self.client.on(events.NewMessage(pattern='/signal'))
        async def signal_handler(event):
            await self._handle_signal_command(event)
        
        @self.client.on(events.NewMessage(pattern='/sentiment'))
        async def sentiment_handler(event):
            await self._handle_sentiment_command(event)
        
        @self.client.on(events.NewMessage(pattern='/news'))
        async def news_handler(event):
            await self._handle_news_command(event)
        
        # Admin-only commands
        @self.client.on(events.NewMessage(pattern='/reload'))
        async def reload_handler(event):
            if await self._is_admin(event):
                await self._handle_reload_command(event)
        
        @self.client.on(events.NewMessage(pattern='/dbsnap'))
        async def dbsnap_handler(event):
            if await self._is_admin(event):
                await self._handle_dbsnap_command(event)
        
        @self.client.on(events.NewMessage(pattern='/loglevel'))
        async def loglevel_handler(event):
            if await self._is_admin(event):
                await self._handle_loglevel_command(event)
        
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            await self._handle_help_command(event)
    
    async def _is_admin(self, event) -> bool:
        """Check if user is admin (from admin group or specific users)"""
        chat_id = event.chat_id
        return chat_id == self.admin_group or await self._is_owner(event.sender_id)
    
    async def _is_owner(self, user_id: int) -> bool:
        """Check if user is bot owner"""
        # Add your Telegram user ID here for admin access
        owner_ids = [123456789]  # Replace with actual owner user IDs
        return user_id in owner_ids
    
    @throttle(calls_per_minute=20)
    async def send_message(self, chat, message: str, parse_mode='md'):
        """Send rate-limited message"""
        if not self.client:
            log.warning("⚠️ Telegram client not initialized")
            return False
        
        try:
            await self.client.send_message(chat, message, parse_mode=parse_mode)
            log.info(f"✅ Message sent to {chat}: {message[:50]}...")
            return True
        except Exception as e:
            log.error(f"❌ Failed to send message to {chat}: {e}")
            return False
    
    async def _handle_price_command(self, event):
        """Handle /price <symbol> command"""
        try:
            args = event.message.text.split()
            if len(args) < 2:
                await event.reply("Usage: `/price <symbol>`\n\nExamples:\n• `/price NIFTY50`\n• `/price BTCUSDT`\n• `/price BTC`", parse_mode='md')
                return
            
            symbol = args[1].upper()
            
            # Try different data sources based on symbol
            tick_data = None
            
            if symbol in ["NIFTY50", "BANKNIFTY", "SENSEX"]:
                # Angel One for Indian markets
                tick_data = await get_latest_tick(symbol)
                source = "Angel One"
            elif "USDT" in symbol or symbol in ["BTC", "ETH", "BNB"]:
                # Binance for crypto
                if "USDT" not in symbol:
                    symbol += "USDT"
                tick_data = await self.binance.get_last_trade(symbol)
                source = "Binance"
            else:
                # CoinGecko fallback
                tick_data = await self.coingecko.get_price(symbol.lower())
                source = "CoinGecko"
            
            if tick_data:
                # Calculate changes (simplified)
                change_1min = "+0.00%"  # Would need historical data
                change_1day = "+0.00%"  # Would need historical data
                
                message = f"""
📊 **{symbol} Price Data**

**Price**: ${tick_data.get('close', tick_data.get('price', 'N/A')):,.2f}
**High**: ${tick_data.get('high', 'N/A')}
**Low**: ${tick_data.get('low', 'N/A')}
**Volume**: {tick_data.get('volume', 'N/A'):,}

**Changes**:
• 1min: {change_1min}
• 1day: {change_1day}

**Source**: {source}
**Time**: {datetime.now().strftime('%H:%M:%S')}

_Live data from AJxAI Oracle_
"""
                await event.reply(message.strip(), parse_mode='md')
            else:
                await event.reply(f"❌ No price data found for {symbol}")
                
        except Exception as e:
            log.error(f"Price command error: {e}")
            await event.reply("❌ Error fetching price data")
    
    async def _handle_signal_command(self, event):
        """Handle /signal <symbol> command"""
        try:
            args = event.message.text.split()
            if len(args) < 2:
                await event.reply("Usage: `/signal <symbol>`\n\nExample: `/signal NIFTY50`", parse_mode='md')
                return
            
            symbol = args[1].upper()
            
            # Query latest signal from database
            async with aiosqlite.connect("./ajxai.db") as db:
                async with db.execute(
                    "SELECT signal_type, confidence, target_price, stop_loss, reasoning, created_at "
                    "FROM signals WHERE symbol = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
                    (symbol,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        signal_type, confidence, target_price, stop_loss, reasoning, created_at = row
                        
                        emoji_map = {
                            "BUY": "🟢📈",
                            "SELL": "🔴📉", 
                            "HOLD": "🟡⏸️",
                            "ALERT": "⚠️🔔"
                        }
                        
                        emoji = emoji_map.get(signal_type, "📊")
                        
                        message = f"""
{emoji} **Latest Signal for {symbol}**

**Action**: {signal_type}
**Confidence**: {confidence:.1%}
**Target**: ${target_price:.2f}
**Stop Loss**: ${stop_loss:.2f}

**Analysis**: {reasoning[:200]}{"..." if len(reasoning) > 200 else ""}

**Generated**: {created_at}

_AJxAI Oracle Signal_
"""
                        await event.reply(message.strip(), parse_mode='md')
                    else:
                        await event.reply(f"❌ No active signals found for {symbol}")
                        
        except Exception as e:
            log.error(f"Signal command error: {e}")
            await event.reply("❌ Error fetching signal data")
    
    async def _handle_sentiment_command(self, event):
        \"\"\"Handle /sentiment <symbol> command\"\"\"
        try:
            args = event.message.text.split()
            if len(args) < 2:
                await event.reply("Usage: `/sentiment <symbol>`\\n\\nExample: `/sentiment BTC`", parse_mode='md')
                return
            
            symbol = args[1].upper()
            
            # Query sentiment from articles
            async with aiosqlite.connect("./ajxai.db") as db:
                async with db.execute(
                    "SELECT AVG(sentiment_score), COUNT(*) FROM articles "
                    "WHERE tickers LIKE ? AND sentiment_score IS NOT NULL "
                    "AND datetime(published_at) > datetime('now', '-24 hours')",
                    (f'%{symbol}%',)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row and row[0] is not None:
                        avg_sentiment, article_count = row
                        
                        if avg_sentiment > 0.2:
                            mood = "🚀 Bullish"
                            color = "🟢"
                        elif avg_sentiment < -0.2:
                            mood = "🐻 Bearish"
                            color = "🔴"
                        else:
                            mood = "😐 Neutral"
                            color = "🟡"
                        
                        sentiment_bar = "█" * int(abs(avg_sentiment) * 10)
                        
                        message = f"""
📊 **{symbol} Sentiment Analysis**

**Overall Mood**: {color} {mood}
**Score**: {avg_sentiment:.2f} (-1 to +1)
**Meter**: {sentiment_bar}

**Based on**: {article_count} articles (24h)
**Updated**: {datetime.now().strftime('%H:%M:%S')}

_Sentiment analysis by AJxAI_
"""
                        await event.reply(message.strip(), parse_mode='md')
                    else:
                        await event.reply(f"❌ No sentiment data found for {symbol}")
                        
        except Exception as e:
            log.error(f"Sentiment command error: {e}")
            await event.reply("❌ Error fetching sentiment data")
    
    async def _handle_news_command(self, event):
        \"\"\"Handle /news <symbol> command\"\"\"
        try:
            args = event.message.text.split()
            if len(args) < 2:
                await event.reply("Usage: `/news <symbol>`\\n\\nExample: `/news BTC`", parse_mode='md')
                return
            
            symbol = args[1].upper()
            
            # Query latest news from database
            async with aiosqlite.connect("./ajxai.db") as db:
                async with db.execute(
                    "SELECT title, summary, link, published_at, source FROM articles "
                    "WHERE tickers LIKE ? ORDER BY published_at DESC LIMIT 3",
                    (f'%{symbol}%',)
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    if rows:
                        message = f"📰 **Latest News for {symbol}**\\n\\n"
                        
                        for i, (title, summary, link, published_at, source) in enumerate(rows, 1):
                            message += f"**{i}. {title[:60]}{'...' if len(title) > 60 else ''}**\\n"
                            if summary:
                                message += f"{summary[:100]}{'...' if len(summary) > 100 else ''}\\n"
                            message += f"📅 {published_at} | 📰 {source}\\n"
                            if link:
                                message += f"🔗 [Read more]({link})\\n"
                            message += "\\n"
                        
                        message += "_Curated by AJxAI Oracle_"
                        await event.reply(message.strip(), parse_mode='md')
                    else:
                        await event.reply(f"❌ No recent news found for {symbol}")
                        
        except Exception as e:
            log.error(f"News command error: {e}")
            await event.reply("❌ Error fetching news data")
    
    async def _handle_reload_command(self, event):
        \"\"\"Handle /reload admin command\"\"\"
        try:
            # Force refresh Angel token
            await angel.ensure_valid_token()
            await event.reply("✅ Angel One token refreshed and data streams reloaded")
        except Exception as e:
            log.error(f"Reload command error: {e}")
            await event.reply(f"❌ Reload failed: {e}")
    
    async def _handle_dbsnap_command(self, event):
        \"\"\"Handle /dbsnap admin command\"\"\"
        try:
            import zipfile
            
            # Create zip of database
            zip_path = f"ajxai_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write('./ajxai.db', 'ajxai.db')
            
            await self.client.send_file(event.chat_id, zip_path)
            
            # Clean up
            os.remove(zip_path)
            
            await event.reply("✅ Database backup sent")
        except Exception as e:
            log.error(f"DB snap command error: {e}")
            await event.reply(f"❌ Database backup failed: {e}")
    
    async def _handle_loglevel_command(self, event):
        \"\"\"Handle /loglevel admin command\"\"\"
        try:
            args = event.message.text.split()
            if len(args) < 2:
                await event.reply("Usage: `/loglevel <INFO|DEBUG|WARNING|ERROR>`", parse_mode='md')
                return
            
            level = args[1].upper()
            if level in ['INFO', 'DEBUG', 'WARNING', 'ERROR']:
                logging.getLogger().setLevel(getattr(logging, level))
                await event.reply(f"✅ Log level set to {level}")
            else:
                await event.reply("❌ Invalid log level. Use INFO, DEBUG, WARNING, or ERROR")
                
        except Exception as e:
            log.error(f"Log level command error: {e}")
            await event.reply(f"❌ Log level change failed: {e}")
    
    async def _handle_help_command(self, event):
        \"\"\"Handle /help command\"\"\"
        help_text = \"\"\"
🤖 **AJxAI Oracle Bot Commands**

**Market Data**:
• `/price <symbol>` - Get latest price and volume
• `/signal <symbol>` - Get latest trading signal
• `/sentiment <symbol>` - Get sentiment analysis
• `/news <symbol>` - Get latest news

**Examples**:
• `/price NIFTY50` - NIFTY 50 price
• `/price BTCUSDT` - Bitcoin price
• `/signal BTC` - Latest BTC signal
• `/sentiment AAPL` - Apple sentiment

**Supported Markets**:
• Indian: NIFTY50, BANKNIFTY, SENSEX
• Crypto: BTC, ETH, BNB, BTCUSDT, etc.
• Global: Major stocks and indices

_Powered by AJxAI Oracle Platform_
\"\"\"
        await event.reply(help_text.strip(), parse_mode='md')
    
    async def broadcast_signal(self, signal_data: dict):
        \"\"\"Broadcast new trading signal to public channel\"\"\"
        try:
            emoji_map = {
                "BUY": "🟢📈",
                "SELL": "🔴📉", 
                "HOLD": "🟡⏸️",
                "ALERT": "⚠️🔔"
            }
            
            signal_type = signal_data.get('signal_type', 'UNKNOWN')
            emoji = emoji_map.get(signal_type, "📊")
            
            message = f\"\"\"
{emoji} **AJxAI Trading Signal**

**Symbol**: {signal_data.get('symbol')}
**Action**: {signal_type}
**Confidence**: {signal_data.get('confidence', 0):.1%}
**Price**: ${signal_data.get('target_price', 0):.2f}
**Stop Loss**: ${signal_data.get('stop_loss', 0):.2f}

**Analysis**: {signal_data.get('reasoning', 'No details available')[:200]}

**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

_Generated by AJxAI Oracle Platform_
\"\"\"
            
            # Broadcast to public channel
            await self.send_message(self.public_channel, message.strip())
            
            # Also send to admin group if configured
            if self.admin_group:
                await self.send_message(self.admin_group, f"📤 Signal broadcasted: {signal_data.get('symbol')} {signal_type}")
            
            log.info(f"Signal broadcasted: {signal_data.get('symbol')} {signal_type}")
            
        except Exception as e:
            log.error(f"Signal broadcast failed: {e}")
    
    async def start_signal_watcher(self):
        \"\"\"Start database watcher for new signals\"\"\"
        log.info("🔍 Starting signal watcher...")
        
        last_signal_id = 0
        
        while self.is_running:
            try:
                async with aiosqlite.connect("./ajxai.db") as db:
                    async with db.execute(
                        "SELECT id, symbol, signal_type, confidence, target_price, stop_loss, reasoning "
                        "FROM signals WHERE id > ? AND is_active = 1 ORDER BY id ASC",
                        (last_signal_id,)
                    ) as cursor:
                        rows = await cursor.fetchall()
                        
                        for row in rows:
                            signal_id, symbol, signal_type, confidence, target_price, stop_loss, reasoning = row
                            
                            signal_data = {
                                'symbol': symbol,
                                'signal_type': signal_type,
                                'confidence': confidence,
                                'target_price': target_price,
                                'stop_loss': stop_loss,
                                'reasoning': reasoning
                            }
                            
                            await self.broadcast_signal(signal_data)
                            last_signal_id = signal_id
                
                # Wait 10 seconds before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                log.error(f"Signal watcher error: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def run(self):
        \"\"\"Start the bot and run until disconnected\"\"\"
        if not self.client:
            log.error("❌ Bot not initialized")
            return
        
        self.is_running = True
        log.info("🚀 AJxAI Telegram Bot starting...")
        
        # Start signal watcher task
        watcher_task = asyncio.create_task(self.start_signal_watcher())
        
        try:
            # Run the bot
            await self.client.run_until_disconnected()
        finally:
            self.is_running = False
            watcher_task.cancel()
            log.info("🔌 AJxAI Telegram Bot stopped")
    
    async def disconnect(self):
        \"\"\"Disconnect the bot\"\"\"
        self.is_running = False
        if self.client:
            await self.client.disconnect()
            log.info("🔌 AJxAI Telegram Bot disconnected")

# Global bot instance
bot = AJxAITelegramBot()

async def main():
    \"\"\"Main function for testing\"\"\"
    # Replace with your actual credentials
    API_ID = 123456  # From my.telegram.org
    API_HASH = "your_api_hash"  # From my.telegram.org
    ADMIN_GROUP_ID = -123456789  # Your admin group chat ID
    
    if await bot.initialize(API_ID, API_HASH, ADMIN_GROUP_ID):
        await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
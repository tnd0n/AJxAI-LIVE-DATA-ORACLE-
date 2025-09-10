from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Tick(Base):
    __tablename__ = "ticks"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)  # BTCUSDT, NIFTY50, etc.
    source = Column(String(20), nullable=False)  # binance, angel, coingecko
    timestamp = Column(DateTime, nullable=False, index=True)
    open_price = Column(Float)
    high_price = Column(Float) 
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Float)
    raw_data = Column(Text)  # JSON string for debugging
    created_at = Column(DateTime, default=func.now())

class Article(Base):
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False)  # cnbc, nytimes, etc.
    category = Column(String(30), nullable=False, index=True)  # markets, geopolitics
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    link = Column(String(1000))
    published_at = Column(DateTime, index=True)
    tickers = Column(String(200))  # comma-separated: AAPL,NIFTY50
    sentiment_score = Column(Float)  # -1 to +1, null if not analyzed
    created_at = Column(DateTime, default=func.now())

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    target_price = Column(Float)
    stop_loss = Column(Float)
    reasoning = Column(Text)  # GPT explanation
    data_points_used = Column(Integer)  # how many ticks/articles influenced this
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
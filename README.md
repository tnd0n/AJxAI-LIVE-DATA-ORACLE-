# AJxAI – Live-Data Oracle Platform

AJxAI is an AI-driven oracle that ingests live market, crypto, and news data, decodes hidden patterns with LLMs/ML models, and pushes actionable signals. **No mock data is ever allowed.** All modules hit real-time sources or fail loudly.

## System Architecture

```
Data Layer → Decode Layer → Action Layer
```

1. **Data Layer**: Angel One SmartAPI, Binance REST + WebSocket, CoinGecko REST
2. **Decode Layer**: GPT-4/5 pattern analysis, custom ML models
3. **Action Layer**: Trade router, Telegram/Web notifications

## Tech Stack

- **Backend**: Python 3.11 + FastAPI (uvicorn)
- **Database**: PostgreSQL (long-term) + Redis (cache)
- **AI/ML**: OpenAI GPT-4/5
- **Frontend**: HTML/CSS/JavaScript
- **Deployment**: Replit → GitHub CI/CD → Render

## Quick Start

1. Set environment variables in `config/api_keys.env`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python backend/main.py`
4. Access at `http://localhost:5000`
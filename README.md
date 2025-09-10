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

## 🔧 Development Workflow for Agents

### GitHub Integration - Batch Upload

**❌ DON'T**: Use individual curl commands for each file (inefficient)

**✅ DO**: Use the batch upload script for efficient GitHub pushes

```bash
# Install requests if not available
pip install requests

# Batch upload all files to GitHub
python scripts/github_batch_upload.py \
  --token YOUR_GITHUB_TOKEN \
  --owner tnd0n \
  --repo AJxAI-LIVE-DATA-ORACLE-

# Or with custom file configuration
python scripts/github_batch_upload.py \
  --token YOUR_GITHUB_TOKEN \
  --owner tnd0n \
  --repo AJxAI-LIVE-DATA-ORACLE- \
  --config scripts/config_example.json
```

### Agent Guidelines

1. **Always use batch upload** for pushing multiple files
2. **Update TASK_LOG.md** after completing work
3. **Test APIs with real data** before pushing
4. **Never commit API keys** - they're in .gitignore
5. **Use meaningful commit messages** with emojis for clarity

### File Structure Rules

```
AJxAI-LIVE-DATA-ORACLE-/
├── 📄 README.md                    # Keep updated with agent instructions
├── 📄 .gitignore                   # Protects API keys and secrets
├── 📄 requirements.txt             # All Python dependencies
├── 📄 TASK_LOG.md                  # Agent communication log
├── 📁 scripts/                     # Development tools
│   ├── github_batch_upload.py     # Batch GitHub uploads
│   └── config_example.json        # Upload configuration template
├── 📁 backend/                     # Python backend
│   ├── main.py                     # FastAPI application
│   ├── data_layer/                 # API integrations
│   ├── decode_layer/               # AI/ML processing
│   └── action_layer/               # Output actions
├── 📁 config/                      # Configuration (git-ignored)
└── 📁 frontend/                    # Web interface
```

### API Integration Status

- ✅ **Angel One SmartAPI**: Live authentication, NIFTY data ready
- ✅ **CoinGecko API**: Bitcoin $112K+, full market data
- ⚠️ **Binance API**: Valid credentials, region-restricted
- 🚀 **Platform**: FastAPI server operational on port 5000
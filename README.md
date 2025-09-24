# SniprX – AI-Powered XAUUSD Trading Bot & Dashboard

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18-green?logo=node.js)](https://nodejs.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://telegram.org/)

**SniprX** is a **full-stack trading platform** for XAUUSD (Gold), combining a **Python-based automated trading bot** with a **Next.js dashboard** for monitoring, management, and alerts. The system supports **multi-strategy trading**, **risk management**, **Telegram notifications**, and optional **Google OAuth** via Express backend.

---

## 🏆 Features

### Backend – XAUUSD-bot (Python)
- **Multi-strategy execution** on MT5 (Judas Swing, MSB Retest, AMD, MMC, MMXM, Engulfing Candle, Order Block, OTE)
- **FastAPI server** for bot control, MT5 login, trade fetching
- **Telegram alerts** for trades, errors, and notifications
- **SQLite logging** + CSV + JSON logs with a unified schema
- **Configurable risk management** (dynamic lot sizing, ATR-based SL/TP, drawdown control)
- **Optional ML/LLM trade filtering** using Gemini API
- **Production-ready**: modular design, error handling, logging, and scalability

### Frontend – SniprX Dashboard (Next.js)
- Modern **Next.js 14 + Tailwind UI** dashboard
- Real-time connection to FastAPI backend (`NEXT_PUBLIC_API_URL`)
- **Telegram bot integration** (`node-telegram-bot-api`)
- Optional **Express backend**:
  - Google OAuth authentication
  - Session management
  - Telegram bot webhook hosting
- **Visual trade analytics**: open trades, history, PnL, and alerts
- **Responsive design** for desktop and mobile

---
## 📦 Project Structure

SniprX/

├── XAUUSD-bot/ # Backend (Python + MT5)
│ ├── api_server.py # FastAPI endpoints
│ ├── STOCKDATA/main.py # Trading loop, strategy manager
│ ├── STOCKDATA/file.py # Trade placement, risk & persistence
│ ├── STOCKDATA/utils/ # Helpers: trade logger, MT5 utils, ML filter
│ ├── config.json # Config: risk, strategies, integrations
│ ├── schema.sql # SQLite schema
│ ├── trades/ # SQLite DB + CSV logs
│ └── logs/ # JSON logs
│
├── BOT--master/ # Frontend (Next.js Dashboard)
│ ├── app/ # Next.js routes/pages
│ ├── lib/telegram-bot.ts # Telegram integration
│ ├── pages/api/telegram/ # API routes (webhook, notify)
│ ├── server/ # Optional Express backend
│ └── .env.local # Dashboard environment config
│
└── README.md


---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **MetaTrader 5 terminal** (default: `C:\Program Files\MetaTrader 5\terminal64.exe`)
- (Optional) SQLite3 CLI tools

---

### 🐍 Backend Setup (XAUUSD-bot)
```bash
cd XAUUSD-bot
python -m venv venv
venv\Scripts\activate      # Windows PowerShell
pip install -r requirements.txt

Environment Variables

Copy .env.example → .env.local and set:
NEXT_PUBLIC_API_URL=http://localhost:8000
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_BOT_USERNAME=YourBotUserName

Bot Configuration

Update config.json:

MT5 credentials: mt5.login, mt5.password, mt5.server

Trading: symbols, timeframe, risk_settings, strategy_filters

Optional integrations: telegram.bot_token, telegram.chat_id, gemini.api_key

Initialize Database

mkdir -p trades
python - <<'PY'
import sqlite3, os
os.makedirs('trades', exist_ok=True)
conn = sqlite3.connect('trades/trades.db')
conn.executescript(open('schema.sql','r',encoding='utf-8').read())
conn.commit(); conn.close()
print('SQLite trades.db initialized.')
PY


Run Backend
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
python -m STOCKDATA

Frontend Setup (SniprX Dashboard)
cd BOT--master
npm install

Environment Variables

Create .env.local:
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_BOT_USERNAME=SniprXBot
NEXT_PUBLIC_API_URL=http://localhost:8000


Run Frontend
npm run dev


Dashboard available at: http://localhost:3000

Used for OAuth and Telegram webhook hosting:

cd BOT--master/server
npm install

Environment Variables
PORT=8000
SESSION_SECRET=your-super-secret-session-key
TELEGRAM_BOT_TOKEN=...
TELEGRAM_BOT_USERNAME=SniprXBot
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

Run Express Backend
npm run dev


Database Schema

Trades table (unified for Python + Dashboard):

CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    volume REAL,
    price REAL,
    sl REAL,
    tp REAL,
    profit REAL,
    comment TEXT
);


Indexed on: timestamp, symbol, strategy, trade_type for faster queries.

Production Notes

Adjust MT5_TERMINAL_PATH in STOCKDATA/main.py if MT5 is installed elsewhere.

Keep secrets out of version control (.env.local, .env, config.json).

For production:

Replace SQLite with PostgreSQL/MySQL

Secure FastAPI endpoints (JWT/OAuth)

Host Telegram bot on backend (Node or Python)

Roadmap

Dockerize backend + frontend

Multi-asset support (beyond XAUUSD)

Advanced ML/LLM trade filtering

Cloud deployment with CI/CD

Enhanced analytics dashboard

# SniprX – AI-Powered Trading Platform

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![Node.js](https://img.shields.io/badge/Node.js-18+-green?logo=node.js)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![MT5](https://img.shields.io/badge/MetaTrader-5-blue)

**SniprX is a professional-grade, integrated trading platform for XAUUSD (Gold), major forex pairs such as **USD/JPY and EUR/USD**. It combines a Python-based automated trading engine with an interactive Next.js dashboard for real-time trade monitoring, execution, and Telegram alerts. The platform supports multiple advanced trading strategies, dynamic risk management, and machine learning–powered trade filtering to enhance decision-making, accuracy, and efficiency. Designed for both retail and institutional traders, SniprX delivers a sophisticated, data-driven trading experience across traditional and digital markets.**
---

## 🚀 Features

### Backend – XAUUSD Trading Bot (Python + MetaTrader 5)
- **Multi-Strategy Execution**: Implements advanced trading strategies.
- **FastAPI Server**: RESTful API for bot control, MT5 authentication, and trade data retrieval.
- **Telegram Integration**: Real-time trade alerts, error notifications, and system status updates via Telegram.
- **Persistent Logging**: Unified trade logging in SQLite, CSV, and JSON formats with a standardized schema.
- **Advanced Risk Management**: Dynamic lot sizing, ATR-based stop-loss/take-profit, and drawdown protection.
- **Optional AI/ML Filtering**: Leverage Gemini API for intelligent trade validation and filtering.
- **Production-Ready**: Modular architecture, comprehensive error handling, and scalable design.

### Frontend – SniprX Dashboard (Next.js)
- **Modern UI**: Built with Next.js 14, Tailwind CSS, and TypeScript for a responsive, intuitive interface.
- **Real-Time Data**: Connects to the FastAPI backend via `NEXT_PUBLIC_API_URL` for live trade updates.
- **Telegram Bot Integration**: Manage and monitor Telegram notifications directly from the dashboard.
- **Optional Express Backend**:
  - Google OAuth 2.0 for secure user authentication.
  - Session management with secure cookies.
  - Telegram webhook hosting for scalable bot operations.
- **Trade Analytics**: Visualize open trades, historical performance, profit/loss, and alerts with interactive charts.
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices.

---

## 📂 Project Structure

```
SniprX/
├── XAUUSD-bot/                # Python backend for trading bot
│   ├── api_server.py          # FastAPI endpoints for bot control
│   ├── STOCKDATA/
│   │   ├── main.py            # Core trading loop and strategy manager
│   │   ├── file.py            # Trade execution, risk management, and persistence
│   │   ├── utils/             # Helper modules (MT5 utils, trade logger, ML filter)
│   ├── config.json            # Bot configuration (MT5, risk, strategies, integrations)
│   ├── schema.sql             # SQLite database schema
│   ├── trades/                # SQLite database and CSV trade logs
│   └── logs/                  # JSON logs for debugging and auditing
├── BOT--master/               # Next.js frontend dashboard
│   ├── app/                   # Next.js routes and pages
│   ├── lib/telegram-bot.ts    # Telegram bot integration
│   ├── pages/api/telegram/    # API routes for Telegram webhook and notifications
│   ├── server/                # Optional Express backend for OAuth and Telegram
│   └── .env.local             # Frontend environment variables
```

---

## 🛠️ Quickstart Guide

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18 or higher
- **MetaTrader 5**: Installed at default path (`C:\Program Files\MetaTrader 5\terminal64.exe`)
- **SQLite3**: Optional CLI tools for database management
- **Telegram Bot**: Create a bot via [BotFather](https://t.me/BotFather) to obtain a token
- **(Optional)** Google Cloud Console credentials for OAuth integration

---

### 🐍 Backend Setup (XAUUSD-bot)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-repo/SniprX.git
   cd SniprX/XAUUSD-bot
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   - Copy `.env.example` to `.env.local` and update:
     ```env
     NEXT_PUBLIC_API_URL=http://localhost:8000
     TELEGRAM_BOT_TOKEN=your-telegram-bot-token
     TELEGRAM_BOT_USERNAME=@YourBotUsername
     ```

4. **Configure Bot Settings**
   - Update `config.json` with:
     - **MT5 Credentials**: `mt5.login`, `mt5.password`, `mt5.server`
     - **Trading Parameters**: `symbols`, `timeframe`, `risk_settings`, `strategy_filters`
     - **Integrations**: `telegram.bot_token`, `telegram.chat_id`, `gemini.api_key` (optional)

5. **Initialize SQLite Database**
   ```bash
   mkdir -p trades
   python -c "import sqlite3, os; os.makedirs('trades', exist_ok=True); conn = sqlite3.connect('trades/trades.db'); conn.executescript(open('schema.sql', 'r', encoding='utf-8').read()); conn.commit(); conn.close(); print('SQLite trades.db initialized.')"
   ```

6. **Run the Backend**
   ```bash
   uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
   python -m STOCKDATA
   ```

---

### 🌐 Frontend Setup (SniprX Dashboard)

1. **Navigate to Frontend Directory**
   ```bash
   cd ../BOT--master
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Configure Environment Variables**
   - Create `.env.local` and add:
     ```env
     NEXT_PUBLIC_API_URL=http://localhost:8000
     TELEGRAM_BOT_TOKEN=your-telegram-bot-token
     TELEGRAM_BOT_USERNAME=@SniprXBot
     ```

4. **Run the Frontend**
   ```bash
   npm run dev
   ```
   - Dashboard available at: [http://localhost:3000](http://localhost:3000)

---

### Express Backend (OAuth & Telegram Webhook)

1. **Navigate to Express Server**
   ```bash
   cd BOT--master/server
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Configure Environment Variables**
   - Create `.env` and add:
     ```env
     PORT=8000
     SESSION_SECRET=your-super-secret-session-key
     TELEGRAM_BOT_TOKEN=your-telegram-bot-token
     TELEGRAM_BOT_USERNAME=@SniprXBot
     GOOGLE_CLIENT_ID=your-google-client-id
     GOOGLE_CLIENT_SECRET=your-google-client-secret
     ```

4. **Run the Express Backend**
   ```bash
   npm run dev
   ```

---

### 🗄️ Database Schema

The platform uses a unified `trades` table for storing trade data, accessible by both the Python backend and Next.js dashboard.

```sql
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

-- Indexes for faster queries
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_strategy ON trades(strategy);
CREATE INDEX idx_trades_trade_type ON trades(trade_type);
```

---

## 📝 Production Notes

- **MT5 Path**: Update `MT5_TERMINAL_PATH` in `STOCKDATA/main.py` if MetaTrader 5 is installed in a non-default location.
- **Security**: Exclude sensitive files (`.env`, `.env.local`, `config.json`) from version control using `.gitignore`.
- **Scalability**:
  - Replace SQLite with PostgreSQL or MySQL for production environments.
  - Secure FastAPI endpoints with JWT or OAuth2 authentication.
  - Host Telegram bot webhook on the Express backend or Python FastAPI server.
- **Performance**: Optimize MT5 connection pooling and strategy execution for high-frequency trading.
- **Monitoring**: Implement health checks and uptime monitoring for the FastAPI server and Express backend.

---

## 📚 Additional Resources

- [MetaTrader 5 Documentation](https://www.metatrader5.com/en/terminal/help)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

---

**SniprX** – Empowering traders with AI-driven precision and real-time insights.

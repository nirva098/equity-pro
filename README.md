# NSE Alpha Army

Daily pre-market NSE trading system with an RL loop. Modular, testable, and runs free on GitHub Actions.

## Overview
Scans NSE500, applies deterministic finance rules + LLM qual layer, and outputs 3-5 high conviction trades with entry/SL/target. Paper trades at 9:15 AM. EOD 3:45 PM calculates PnL and updates RL memory via KB + LLM journal hybrid.

## Setup

1. Copy `.env.example` to `.env` and fill in API keys:
   - OPENAI_API_KEY
   - TAVILY_API_KEY
   - LANGCHAIN_API_KEY
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize Database:
   ```bash
   python -c "from core.db import init_db; init_db()"
   ```

4. Run locally:
   ```bash
   python premarket_run.py
   python eod_run.py
   ```

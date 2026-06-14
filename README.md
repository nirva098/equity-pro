# NSE Alpha Army

A fully autonomous, deterministic + LLM-based pre-market trading agent for the Indian Stock Market (NSE).

## System Architecture

The system is built on **LangGraph** and runs entirely locally or via GitHub Actions. It strictly separates math/finance logic from reasoning:

1. **Data Layer (Deterministic)**: Uses `yfinance` and `nsepython` to fetch market context, FII/DII data, and technical indicators (ATR, RSI, ADX). Contains a 3-stage Discounted Cash Flow (DCF) model.
2. **Decision Core (Deterministic)**: 
   - **Market Context**: Classifies regime as Risk-on / Risk-off / High VIX.
   - **Quant Screener**: Filters stocks through 3 predefined setups (`value_breakout`, `momentum_pullback`, `quality_compounder`).
   - **Risk Sizer**: ATR-based stop-loss/targets and Kelly criterion position sizing.
3. **LLM Qual Layer (gpt-4o-mini)**: 
   - Builds structured research briefs for the top quant candidates.
   - Extracts news/technical/sector catalysts for the shortlist.
   - Runs a skeptic pass to identify bear cases, red flags, and kill-trade conditions.
   - Produces a final PM-style ranking before risk sizing.
   - Generates trade theses and validates outputs against deterministic data to prevent hallucinations.
4. **Execution & Feedback Loop**: Paper trades are stored in SQLite. EOD reporter calculates PnL, judges setup performance, and updates strategy weights using Thompson Sampling so the next cycle gets explicit nudges.

---

## Local Setup

### 1. Prerequisites
- Python 3.11+
- OpenAI API Key (for LLM reasoning)
- Tavily API Key (for news search)
- (Optional) Telegram Bot Token & Chat ID for notifications

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/equity-pro.git
cd equity-pro

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy the example environment file:
```bash
cp .env.example .env
```
Edit `.env` and add your API keys.

### 4. Running the Pipelines
Run the **Premarket** pipeline (simulates 9:15 AM execution):
```bash
PYTHONPATH=. python3 premarket_run.py
```
Run the **End-of-Day (EOD)** pipeline (simulates 3:30 PM closing):
```bash
PYTHONPATH=. python3 eod_run.py
```

---

## Running on GitHub Actions (Fully Autonomous)

You can set this project to run completely hands-free every day.

### 1. Configure Repository Secrets
Go to your repository **Settings > Secrets and variables > Actions** and add:
- `OPENAI_API_KEY`
- `TAVILY_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 2. Grant Write Permissions (Critical)
The action needs permission to commit the SQLite database and updated strategy memory back to the repository.
1. Go to **Settings > Actions > General**.
2. Scroll down to **Workflow permissions**.
3. Select **Read and write permissions**.
4. Click **Save**.

### 3. Schedule
The GitHub Action `.github/workflows/alpha.yml` is scheduled to run:
- **Premarket**: 8:30 AM IST (Monday-Friday)
- **EOD**: 3:45 PM IST (Monday-Friday)

You can also trigger it manually from the **Actions** tab by selecting "workflow_dispatch" and choosing the run type.

---

## Reading Reports

- **Database**: All trades are tracked in `trades.db` (SQLite).
- **Research Database**: Full run/candidate/recommendation audit trail is stored in `data/research.db`.
- **Daily Reports**: Found in the `reports/` folder (JSON format).
- **Research Dashboard**: Generate the DB-backed dashboard with:
```bash
PYTHONPATH=. python3 generate_research_dashboard.py
```
Then open `reports/research_dashboard.html`.
- **AI Audit Tables**: `research_briefs`, `catalyst_checks`, `skeptic_reviews`, and `final_rankings` show how the AI research pod changed the quant shortlist before sizing.
- **Trading Journal**: The LLM writes its daily learnings and analysis to `memory/trading_journal.md`.
- **Strategy Weights**: The RL loop updates setup probabilities in `memory/strategy_memory.json`.
- **Feedback Loop**: The dashboard now shows the latest EOD feedback summary, setup-level judge/nudge signals, and the current setup weights carried into the next cycle.

### *1. Repo Structure*
nse-alpha-army/
├──.github/
│ └── workflows/
│ └── alpha.yml # GitHub Actions: 8:00 AM + 3:45 PM IST cron
├── agents/
│ ├── __init__.py
│ ├── supervisor.py # LLM: orchestrator, reads KB + journal
│ ├── market_context_agent.py # Deterministic + LLM: regime detection
│ ├── data_scout_fundamental.py # Deterministic: yfinance DCF, ratios
│ ├── data_scout_technical.py # Deterministic: ATR, S/R, momentum
│ ├── data_scout_news.py # LLM + Tavily: sentiment, events
│ ├── quant_screener.py # Deterministic: rule-based filters
│ ├── thesis_agent.py # LLM: writes 3-line thesis per stock
│ ├── risk_sizer.py # Deterministic: Kelly, ATR SL, 2% risk cap
│ ├── validator_node.py # Deterministic: hallucination check
│ ├── paper_executor.py # Deterministic: simulate fills 9:15 AM
│ ├── eod_reporter.py # LLM + Deterministic: PnL, journal entry
│ └── rl_updater.py # Deterministic: Thompson Sampling KB update
├── tools/
│ ├── __init__.py
│ ├── yfinance_tool.py # Wrapper: NSE data fetch.NS tickers
│ ├── nse_tool.py # nsepython: FII/DII, holidays, corp actions
│ ├── dcf_model.py # Pure python: 3-stage DCF
│ ├── technicals.py # ATR, RSI, pivot S/R, ADX functions
│ ├── tavily_search.py # News search wrapper
│ └── telegram_notify.py # Send EOD report
├── core/
│ ├── __init__.py
│ ├── state.py # TypedDict AlphaState
│ ├── graph.py # Builds premarket + eod LangGraphs
│ ├── db.py # SQLite: trades, strategy_memory CRUD
│ └── config.py # Load.env, constants
├── memory/
│ ├── strategy_memory.json # RL KB: setup weights, stats, regime perf
│ └── trading_journal.md # LLM context: lessons, special events
├── reports/ # Generated daily: thesis, EOD reports
│ └──.gitkeep
├── data/
│ └── universe_nse500.csv # List of tickers to scan
├── db/
│ └── schema.sql # SQLite tables: trades, daily_runs
├── premarket_run.py # Entry: called by 8:00 AM cron
├── eod_run.py # Entry: called by 3:45 PM cron
├── requirements.txt
├──.env.example # OPENAI_API_KEY, TAVILY_API_KEY, etc
├──.gitignore
└── README.md
---

### *2. Master Code-Gen Prompt - Paste this to your AI coder*
You are a senior quant developer. Build the complete "NSE Alpha Army" repo per spec below. Use Python 3.11, LangGraph 0.2+, langchain-openai, yfinance, nsepython, tavily-python, SQLite.

GOAL:
Daily pre-market NSE system. Scans NSE500, applies deterministic finance rules + LLM qual layer, outputs 3-5 high conviction trades with entry/SL/target. Paper trades at 9:15 AM. EOD 3:45 PM calculates PnL and updates RL memory via KB + LLM journal hybrid. Runs free on GitHub Actions.

CRITICAL RULES:
1. All math, data fetch, risk sizing, validation = Deterministic Python. No LLM.
2. All synthesis, thesis writing, regime interpretation, lessons = LLM gpt-4o-mini temp=0.3.
3. RL = Hybrid. strategy_memory.json holds Thompson Sampling weights updated by code. trading_journal.md holds lessons read by LLM. Supervisor uses both.
4. Prevent recency bias: Do not downweight setup if trades<30. Use Laplace smoothing: weight=(wins+1)/(trades+2).
5. Special conditions: If market_context['event']=Fed/Budget, LLM must reference journal and can override weights.
6. Validator must check: LLM output numbers exist in deterministic data. If not, retry thesis_agent.
7. Total portfolio risk per day = 2% max. Position size = (0.02 * Capital) / (entry - SL). Cap 5% per stock.

FILE SPECS:

1. core/state.py
   AlphaState TypedDict: date, universe:List[str], market_context:dict, fundamentals:Dict, technicals:Dict, news_sentiment:Dict, thesis:Dict, trades:List[dict], execution_log:List, eod_pnl:dict, strategy_memory:dict, next_agent:str

2. core/db.py
   SQLite with tables:
   trades(id, date, ticker, setup, entry, sl, target, qty, entry_time, exit_time, exit_price, pnl_R, status)
   daily_runs(date, regime, trades_taken, win_rate, total_R, journal_entry)
   Functions: init_db(), log_trade(), update_memory(), load_memory()

3. memory/strategy_memory.json - initial:
   {"setups": {"value_breakout": {"trades":0,"wins":0,"weight":0.5,"notes":""},
              "momentum_pullback":{"trades":0,"wins":0,"weight":0.5,"notes":""},
              "quality_compounder":{"trades":0,"wins":0,"weight":0.5,"notes":""}},
    "regime_multipliers": {"risk_on":1.0,"risk_off":0.5,"high_vix":0.3},
    "special_events": []}

4. agents/market_context_agent.py
   Fetch: NIFTY, INDIAVIX via yfinance. FII/DII via nsepython. US futures via yfinance ^GSPC.
   LLM prompt: "Classify regime: risk_on/risk_off/high_vix. Flag events: Fed_week/Budget_day. JSON."
   Output: state[market_context]

5. agents/data_scout_fundamental.py
   For each ticker: yf.Ticker(ticker).financials,.balance_sheet,.cashflow,.info
   Calc: DCF 3-stage, Piotroski F-Score, Altman Z, ROCE, FCF_yield. All pure pandas/numpy.
   Output: state[fundamentals][ticker]

6. agents/data_scout_technical.py
   Calc: ATR14, RSI14, ADX14, 20/50/200DMA, pivot S/R. Flag: breakout = close>resistance AND vol>1.5*avg_vol.
   Output: state[technicals][ticker]

7. agents/quant_screener.py
   Rules: Load strategy_memory. Apply filters:
   value_breakout: FCF_yield>8 AND DCF_upside>25% AND F_score>7 AND price>200DMA
   momentum_pullback: 3M_ret>15% AND RSI<40 AND price>50DMA AND ADX>25
   quality_compounder: ROCE>18% 3yr_avg AND D/E<0.5 AND 52w_high_distance<5%
   Rank by: strategy_memory[setup][weight] * expected_R. Return top 20.

8. agents/thesis_agent.py
   LLM prompt per ticker: "Data: {fundamentals, technicals, news}. Write JSON: {thesis: 3 lines - Catalyst/Valuation/Risk, confidence:1-10}. Style: Motilal Oswal ER note."
   temp=0.3

9. agents/risk_sizer.py
   For each trade: ATR = technicals[ATR14]. SL = entry - 1.5*ATR. Target = entry + 3*ATR.
   Kelly_f = (winrate*avg_win - lossrate*avg_loss)/avg_win. Use strategy_memory stats.
   qty = (Capital*0.02*Kelly_f) / (entry-SL). Keep top 5 by confidence*expected_R.

10. agents/validator_node.py
    Extract all numbers from thesis_agent output. Check each exists in fundamentals or technicals dict. If any missing, set next_agent=thesis_agent. Else next_agent=paper_executor.

11. agents/eod_reporter.py
    Fetch 3:30 PM price via yfinance. Calc PnL_R for each trade. Update trades table.
    LLM prompt: "Today results: {pnl}. Journal history: {trading_journal.md last 5 entries}. Write new journal entry: What worked, what failed, lesson for tomorrow. If regime=event_day, note it. 5 lines max."
    Append to memory/trading_journal.md. Send Telegram.

12. agents/rl_updater.py
    Load strategy_memory.json. For each closed trade: update wins, trades.
    new_weight = (wins+1)/(trades+2). If trades<30: weight=max(weight,0.5).
    Save strategy_memory.json.

13. agents/supervisor.py
    Load strategy_memory.json + trading_journal.md last 2000 chars.
    LLM prompt: "Memory: {weights}. Journal: {lessons}. Today regime: {market_context}. Decide active_setups and risk_modifier 0.5-1.5. If journal warns about event_days and today is event, reduce risk. JSON."
    Routes to market_context_agent.

14. core/graph.py
    Build premarket_graph: START->supervisor->market_context->scouts->screener->thesis->sizer->validator->{executor or thesis}->END
    Build eod_graph: START->eod_reporter->rl_updater->END

15. premarket_run.py
    Load universe from data/universe_nse500.csv. init_db(). app=premarket_graph.compile(). app.invoke({date:today, universe:...}). Save report to reports/{date}_premarket.json.

16. eod_run.py
    app=eod_graph.compile(). app.invoke({date:today})

17..github/workflows/alpha.yml
    Two jobs: premarket on cron '30 2 * * 1-5', eod on '15 10 * * 1-5'.
    Steps: checkout, setup-python, pip install, run script with secrets, git commit trades.db + memory/ + reports/, upload artifact.

18. requirements.txt
    langgraph>=0.2.0
    langchain-openai>=0.2.0
    langchain-community>=0.3.0
    yfinance>=0.2.40
    nsepython>=2.0
    tavily-python>=0.5.0
    pandas>=2.2.0
    numpy>=1.26.0
    python-dotenv>=1.0.0

OUTPUT:
Generate all files with complete code. No placeholders. Ensure imports work. Add docstrings. Make it runnable via `python premarket_run.py` locally after setting.env.
---

### *3. Setup Steps After Code Gen*

1. `git init && git add. && git commit -m "init"`
2. Create repo on GitHub, push.
3. Repo Settings → Secrets → Actions: Add `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGCHAIN_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
4. Push code. GitHub Actions will run 8:00 AM IST next weekday.
5. Check Actions tab for logs + artifacts.

*Cost*: $0 for infra. ∼$0.02-0.05/day for gpt-4o-mini + Tavily.
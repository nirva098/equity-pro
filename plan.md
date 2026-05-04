### *`plan.md` - NSE Alpha Army Build Plan*

*Goal*: Ship daily pre-market NSE trade generator with RL loop. Modular, testable, free to run.

*Core Principle*: Deterministic for math/data, LLM for reasoning. Hybrid RL via KB + Journal.

#### *Phase 0: Foundations [Day 1]*
Goal: Repo skeleton + infra works. No agent logic yet.
| Task | Files | Done when |
| 0.1 Repo init | `.gitignore`, `README.md`, `requirements.txt` | `pip install -r requirements.txt` works |
| 0.2 Env + Config | `.env.example`, `core/config.py` | Keys load, `Capital=1000000` defined |
| 0.3 DB Schema | `db/schema.sql`, `core/db.py` | `init_db()` creates `trades`, `daily_runs` tables |
| 0.4 State Schema | `core/state.py` | `AlphaState` TypedDict imports clean |
| 0.5 CI Test | `.github/workflows/alpha.yml` | Manual `workflow_dispatch` runs `python -c "print('ok')"` |
| 0.6 Memory seeds | `memory/strategy_memory.json`, `memory/trading_journal.md` | Files exist with initial JSON/md |
*Test*: Run `python -c "from core.db import init_db; init_db()"` → no errors. Push → Actions run.

---

#### *Phase 1: Data Layer [Day 2-3]*
Goal: Reliably fetch NSE data. 100% deterministic.
| Task | Files | Done when |
| 1.1 yfinance wrapper | `tools/yfinance_tool.py` | `get_nse_data("RELIANCE.NS")` returns dict |
| 1.2 NSE wrapper | `tools/nse_tool.py` | `get_fii_dii()`, `is_trading_day()` work |
| 1.3 DCF engine | `tools/dcf_model.py` | `run_dcf(financials)` returns intrinsic_value |
| 1.4 Technicals lib | `tools/technicals.py` | `calc_atr()`, `find_pivots()` unit tested |
| 1.5 Universe | `data/universe_nse500.csv` | 500 tickers list loaded |
| 1.6 Data Scouts | `agents/data_scout_fundamental.py`, `agents/data_scout_technical.py` | Given ticker, outputs to `state[fundamentals]` |
*Test*: Script that loops 5 tickers, dumps `fundamentals` + `technicals` to JSON. No LLM calls.

---

#### *Phase 2: Decision Core [Day 4-5]*
Goal: From data → ranked candidates. Still no LLM.
| Task | Files | Done when |
| 2.1 Market Context | `agents/market_context_agent.py` | Outputs `regime=risk_on`, `vix=13.2` without LLM first |
| 2.2 Quant Screener | `agents/quant_screener.py` | Runs 3 rule sets, returns top 20 tickers + setup tag |
| 2.3 Risk Sizer | `agents/risk_sizer.py` | Given candidates, outputs `trades` with qty, SL, target |
| 2.4 Validator | `agents/validator_node.py` | Rejects trade if `SL>=entry` or `total_risk>2%` |
*Test*: Run screener → sizer → validator on 2026-05-01 data. Prints 3-5 trades with numbers. All deterministic.

---

#### *Phase 3: LLM Qual Layer [Day 6-7]*
Goal: Add reasoning + writing. Keep it sandboxed.
| Task | Files | Done when |
| 3.1 Thesis Agent | `agents/thesis_agent.py` | Input: dicts. Output: JSON `{thesis, confidence}`. temp=0.3 |
| 3.2 News Agent | `tools/tavily_search.py`, `agents/data_scout_news.py` | Returns `{sentiment, events}` per ticker |
| 3.3 Regime LLM | Upgrade `market_context_agent.py` | Adds LLM call for `event_flag`, `regime_narrative` |
| 3.4 Validator v2 | Upgrade `validator_node.py` | Now cross-checks: numbers in thesis exist in data dicts |
| 3.5 Supervisor | `agents/supervisor.py` | Reads `strategy_memory.json` + journal. Outputs `active_setups` |
*Test*: Run full premarket flow with 3 tickers. Check LangSmith trace: LLM only used in 3 nodes. No math in LLM output.

---

#### *Phase 4: Execution + Reporting [Day 8]*
Goal: Close the daily loop.
| Task | Files | Done when |
| 4.1 Paper Executor | `agents/paper_executor.py` | Simulates 9:15 fill, logs to `trades` table |
| 4.2 EOD Reporter | `agents/eod_reporter.py` | Calcs PnL, writes to `trading_journal.md`, Telegram msg |
| 4.3 Telegram tool | `tools/telegram_notify.py` | `send_message(text)` works |
| 4.4 Graph wiring | `core/graph.py` | `premarket_graph` + `eod_graph` compile |
| 4.5 Entry scripts | `premarket_run.py`, `eod_run.py` | Run end-to-end locally |
*Test*: `python premarket_run.py` → `reports/2026-05-03_premarket.json` created. `python eod_run.py` → journal updated.

---

#### *Phase 5: RL Feedback Loop [Day 9-10]*
Goal: System learns without overfitting.
| Task | Files | Done when |
| 5.1 RL Updater | `agents/rl_updater.py` | Thompson Sampling: updates `strategy_memory.json` |
| 5.2 Supervisor v2 | Upgrade `agents/supervisor.py` | Uses weights + journal to set `risk_modifier` |
| 5.3 Special Events | `market_context_agent.py` | Flags `Fed_week`, `Budget_day` to memory |
| 5.4 Backtest harness | `backtest.py` | Run past 60 days to check no recency bias |
*Test*: Manually mark 5 trades as losses for `momentum`. Check `weight` stays >0.4 if `trades<30`. Journal mentions "Fed week anomaly".

---

#### *Phase 6: Productionize [Day 11-12]*
Goal: Runs reliably on GitHub Actions.
| Task | Files | Done when |
| 6.1 Secrets setup | GitHub repo secrets | All keys added |
| 6.2 Cron test | `.github/workflows/alpha.yml` | `workflow_dispatch` completes, commits DB |
| 6.3 Artifact logs | workflow | Reports downloadable from Actions tab |
| 6.4 Error handling | All agents | `try/except` + LangSmith trace on fail |
| 6.5 README | `README.md` | Runbook: local setup, how to read reports |
*Test*: Merge to `main`. Wait for 8:00 AM IST. Check Actions → green. Check repo → `trades.db` updated.

---

### *How to use this plan with your code-gen LLM*

Feed one phase per chat session:
Prompt: "Implement Phase 1 from this plan.md. Generate all files listed for Phase 1 only. 
Use the master prompt specs from previous message for function details.
Do not write Phase 2 yet. Ensure Phase 1 is standalone and testable."
After it generates, you test locally. If green, commit + next phase.

*Branch strategy*: `main` = stable. `phase-1-data`, `phase-2-core`, etc. Merge after tests pass.

*Debugging rule*: If Phase 3 breaks, you only revert Phase 3. Phase 1-2 still good.

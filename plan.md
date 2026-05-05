# NSE Alpha Army — Roadmap

> Living document. Check off items as completed, add new plans at the bottom.

---

## ✅ Completed

### Foundation & Pipeline (Phases 0–6)
- [x] Repo skeleton, DB schema, AlphaState TypedDict
- [x] yfinance + nsepython data layer (fundamental + technical scouts)
- [x] DCF 3-stage model, Piotroski F-Score, ROCE, FCF Yield
- [x] ATR14, RSI14, ADX14, pivot S/R, 200/50/20 DMA
- [x] Quant screener: 3 setups (value_breakout, momentum_pullback, quality_compounder)
- [x] Kelly risk sizer (ATR-based SL, 3×ATR target)
- [x] Validator: SL/entry check + thesis hallucination detection
- [x] Thompson Sampling RL loop with Laplace smoothing
- [x] LangGraph premarket + EOD graphs
- [x] GitHub Actions cron (8:30 AM + 3:45 PM IST Mon–Fri)
- [x] Telegram EOD notifications

### Bug Fixes (2026-05-05)
- [x] **Pipeline order**: risk_sizer now runs before thesis_agent (thesis was always empty)
- [x] **D/E ratio**: quality_compounder now enforces D/E < 0.5 (was missing)
- [x] **Composite scoring**: candidates now ranked by multi-factor conviction score (were all tied at 1.5)
- [x] **Risk caps**: separate 2% per-trade / 6% portfolio-daily limits (single cap was blocking trades 2–5)
- [x] **active_setups**: screener now respects supervisor's setup decisions
- [x] **Kelly cold-start**: lowered from 0.5 → 0.25 (quarter-Kelly)
- [x] **EOD market context**: EOD run now loads regime from premarket report

### Visualization (2026-05-05)
- [x] GitHub Pages dashboard at `nirva098.github.io/equity-pro`
- [x] 3-page UI: Today's signals / Trade history / Performance charts
- [x] Regime banner with NIFTY, VIX, FII, narrative
- [x] Dated archive at `docs/history/{date}.html`

---

## 🔜 Pending — Near Term

### P1: DB Migration to Turso
**Why**: `trades.db` committed to git on every run pollutes history; `market_data.db` is too heavy for git.
**Plan**:
- Sign up at turso.tech, create `equity-pro-trades` and `equity-pro-market` databases
- `pip install libsql-experimental`
- Swap `sqlite3.connect(path)` → `libsql_experimental.connect(url, auth_token)` in `core/db.py` and `core/market_db.py`
- Add `TURSO_TRADES_URL`, `TURSO_TRADES_TOKEN`, `TURSO_MARKET_URL`, `TURSO_MARKET_TOKEN` to GitHub Secrets
- Remove `git add trades.db data/market_data.db` from workflow
**Effort**: ~2 hrs | **Cost**: Free (Turso free tier: 500MB, 8 DBs)

### P2: Altman Z-Score in Fundamental Scout
**Why**: Adds a distress filter — remove stocks at bankruptcy risk from all setups.
**Plan**: Add `calculate_altman_z(fin, bs)` to `data_scout_fundamental.py`. Filter: Z > 2.6 (safe zone). Add to screener pre-filter before setup rules.
**Effort**: ~1 hr

### P3: Volume Profile in Technical Scout
**Why**: Current breakout flag uses only pivot R1 + volume. Adding VWAP and volume profile gives stronger breakout conviction.
**Plan**: Add `calc_vwap(hist)` to `tools/technicals.py`. Add `VWAP_distance_%` to technicals dict. Use in `value_breakout` scoring bonus.
**Effort**: ~1 hr

### P4: Intraday Price Alert via Telegram
**Why**: Currently signals are sent EOD. A mid-day alert when price approaches target/SL is useful.
**Plan**: Add a 12:30 PM IST GitHub Actions job. Fetches current prices for open trades. If within 2% of target or 1% of SL, sends Telegram alert.
**Effort**: ~2 hrs | **Infra**: New cron in alpha.yml

---

## 🗓️ Pending — Medium Term

### P5: Paper to Live Trading Bridge
**Why**: Move from simulated fills to actual NSE order placement.
**Options**: Zerodha Kite API (most popular), Fyers API, Dhan API. All free for retail.
**Plan**: Add `agents/live_executor.py` that wraps Kite Connect. Keep `paper_executor.py` as fallback. Feature-flag via `.env`: `EXECUTION_MODE=paper|live`.
**Effort**: ~1 day | **Blocker**: Zerodha API subscription (₹2000/month)

### P6: Multi-Timeframe Confirmation
**Why**: Current technicals use daily OHLCV only. Confirming on weekly trend reduces false breakouts.
**Plan**: Fetch weekly data in `data_scout_technical.py`. Add `Weekly_Trend` (above/below 10-week MA). Add as confirmation bonus in screener scoring.
**Effort**: ~2 hrs

### P7: Sector Rotation Awareness
**Why**: FII buying into specific sectors creates tailwinds the system currently ignores.
**Plan**: Add `agents/sector_agent.py` that fetches NSE sector indices (NIFTY IT, NIFTY Bank etc.) via yfinance. Top-2 performing sectors get a score bonus in screener.
**Effort**: ~3 hrs

### P8: Strategy Memory Visualization
**Why**: The RL loop runs but weights are invisible. Want to see how setups perform over time.
**Plan**: Read `memory/strategy_memory.json` in `generate_dashboard.py`. Add a 4th dashboard page "Strategy Memory" with setup weights, win rates, trade counts as cards + a weight-over-time chart (from `memory/weight_history.json` which rl_updater will write).
**Effort**: ~2 hrs

---

## 💡 Ideas Backlog (Not Prioritized)

- Options overlay: check if high-conviction stocks have unusual options activity via NSE derivatives data
- Earnings calendar filter: avoid entering trades within 5 days of results (nsepython has corporate actions)
- Portfolio correlation check: reject trade if new stock is >0.7 correlated with existing open trade
- Walk-forward backtest: replace synthetic backtest with real historical signals using market_data.db
- WhatsApp alert via Twilio (as alternative/complement to Telegram)
- LangSmith tracing for LLM call monitoring

---

## 📌 Rules

1. **Deterministic for math, LLM for reasoning** — never reverse this
2. **Test locally before pushing** — `python premarket_run.py` must run clean
3. **One phase per PR** — don't mix bug fixes and new features in one commit
4. **Laplace smoothing floor stays at 0.5 until trades ≥ 30** — don't remove this protection

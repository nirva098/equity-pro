import json
from datetime import datetime
import yfinance as yf
from core.db import get_open_trades, update_trade_exit, log_daily_run
from core.config import OPENAI_API_KEY
from tools.telegram_notify import send_message

def _calc_pnl(trades: list) -> dict:
    """Fetch latest prices and calculate PnL_R for each open trade."""
    results = []
    for trade in trades:
        ticker = trade['ticker']
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1d")
            if not hist.empty:
                exit_price = float(hist['Close'].iloc[-1])
            else:
                exit_price = trade['entry']  # Default to entry if fetch fails
        except Exception:
            exit_price = trade['entry']

        risk_per_share = trade['entry'] - trade['sl']
        if risk_per_share > 0:
            pnl_R = (exit_price - trade['entry']) / risk_per_share
        else:
            pnl_R = 0

        results.append({
            'id': trade['id'],
            'ticker': ticker,
            'setup': trade['setup'],
            'entry': trade['entry'],
            'sl': trade['sl'],
            'target': trade['target'],
            'qty': trade['qty'],
            'exit_price': round(exit_price, 2),
            'pnl_R': round(pnl_R, 2),
            'pnl_abs': round((exit_price - trade['entry']) * trade['qty'], 2)
        })

    return results

def _generate_journal_entry(pnl_results: list, regime: str) -> str:
    """Use LLM to generate a journal entry from today's results."""
    # Load last 5 journal entries
    try:
        with open('memory/trading_journal.md', 'r') as f:
            journal = f.read()
        # Get last ~5 entries (rough: split by date headers)
        entries = journal.split('\n## ')
        last_entries = '\n## '.join(entries[-5:]) if len(entries) > 5 else journal
    except Exception:
        last_entries = ""

    if not OPENAI_API_KEY:
        # Deterministic fallback
        total_R = sum(r['pnl_R'] for r in pnl_results)
        wins = sum(1 for r in pnl_results if r['pnl_R'] > 0)
        return (f"Date: {datetime.now().strftime('%Y-%m-%d')}. "
                f"Trades: {len(pnl_results)}, Wins: {wins}, Total R: {total_R:.2f}. "
                f"Regime: {regime}. No LLM analysis available.")

    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=OPENAI_API_KEY)

        pnl_summary = json.dumps(pnl_results, indent=2, default=str)
        prompt = f"""Today's trading results:
{pnl_summary}

Regime: {regime}

Journal history (last 5 entries):
{last_entries[-1500:]}

Write a new journal entry (5 lines max):
- What worked today
- What failed
- Lesson for tomorrow
- If regime was an event day, note it
- Keep it actionable

Write the entry:"""

        response = llm.invoke(prompt)
        return response.content.strip()

    except Exception as e:
        print(f"Journal LLM error: {e}")
        total_R = sum(r['pnl_R'] for r in pnl_results)
        return f"Date: {datetime.now().strftime('%Y-%m-%d')}. Total R: {total_R:.2f}. Regime: {regime}."

def run_eod_reporter(state: dict) -> dict:
    """
    EOD Reporter Agent:
    - Fetches latest prices for open trades
    - Calculates PnL_R
    - Updates trades in DB
    - Generates LLM journal entry
    - Appends to trading_journal.md
    - Sends Telegram summary
    - Logs daily run stats
    """
    today = state.get('date', datetime.now().strftime('%Y-%m-%d'))
    regime = state.get('market_context', {}).get('regime', 'unknown')

    # 1. Get open trades from DB
    open_trades = get_open_trades(today)
    if not open_trades:
        print("No open trades found for today.")
        state['eod_pnl'] = {'trades': 0, 'total_R': 0, 'win_rate': 0}
        return state

    print(f"Processing {len(open_trades)} open trades...")

    # 2. Calculate PnL
    pnl_results = _calc_pnl(open_trades)

    # 3. Update DB
    for result in pnl_results:
        update_trade_exit(result['id'], result['exit_price'], result['pnl_R'])

    # 4. Stats
    total_R = sum(r['pnl_R'] for r in pnl_results)
    wins = sum(1 for r in pnl_results if r['pnl_R'] > 0)
    win_rate = (wins / len(pnl_results)) * 100 if pnl_results else 0
    total_pnl_abs = sum(r['pnl_abs'] for r in pnl_results)

    # 5. Generate journal entry
    journal_entry = _generate_journal_entry(pnl_results, regime)

    # 6. Append to trading journal
    try:
        with open('memory/trading_journal.md', 'a') as f:
            f.write(f"\n\n## {today}\n{journal_entry}\n")
        print("Journal updated.")
    except Exception as e:
        print(f"Error updating journal: {e}")

    # 7. Send Telegram
    telegram_msg = (
        f"*EOD Report - {today}*\n"
        f"Regime: {regime}\n"
        f"Trades: {len(pnl_results)} | Wins: {wins}\n"
        f"Win Rate: {win_rate:.0f}% | Total R: {total_R:.2f}\n"
        f"P&L: ₹{total_pnl_abs:,.0f}\n\n"
    )
    for r in pnl_results:
        emoji = "🟢" if r['pnl_R'] > 0 else "🔴"
        telegram_msg += f"{emoji} {r['ticker']}: {r['pnl_R']:+.2f}R (₹{r['pnl_abs']:+,.0f})\n"

    send_message(telegram_msg)

    # 8. Log daily run
    log_daily_run(today, regime, len(pnl_results), win_rate, total_R, journal_entry)

    # 9. Update state
    state['eod_pnl'] = {
        'trades': len(pnl_results),
        'total_R': total_R,
        'win_rate': win_rate,
        'total_pnl_abs': total_pnl_abs,
        'results': pnl_results
    }

    return state

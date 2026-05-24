from datetime import datetime
from core.research_db import update_trade_execution

def run_paper_executor(state: dict) -> dict:
    """
    Paper Executor: Simulates a 9:15 AM fill at the entry price.
    Logs each trade execution directly to the research database.
    """
    trades = state.get('trades', [])
    execution_log = []
    run_id = state.get('run_id')

    if not run_id:
        print("Paper Executor: run_id not found in state, skipping executions.")
        state['execution_log'] = execution_log
        return state

    for trade in trades:
        ticker = trade['ticker']
        entry_price = trade['entry']

        try:
            update_trade_execution(run_id, ticker, 'filled', entry_price)
            execution_log.append({
                'ticker': ticker,
                'status': 'filled',
                'entry': entry_price,
                'qty': trade['qty'],
                'time': '09:15:00'
            })
            print(f"  FILLED: {ticker} qty={trade['qty']} @ {entry_price}")
        except Exception as e:
            execution_log.append({
                'ticker': ticker,
                'status': 'error',
                'error': str(e)
            })
            print(f"  ERROR: {ticker} - {e}")

    state['execution_log'] = execution_log
    return state

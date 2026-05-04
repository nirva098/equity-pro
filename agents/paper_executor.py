from datetime import datetime
from core.db import log_trade

def run_paper_executor(state: dict) -> dict:
    """
    Paper Executor: Simulates a 9:15 AM fill at the entry price.
    Logs each trade to the SQLite trades table.
    """
    trades = state.get('trades', [])
    execution_log = []
    today = state.get('date', datetime.now().strftime('%Y-%m-%d'))

    for trade in trades:
        trade_record = {
            'date': today,
            'ticker': trade['ticker'],
            'setup': trade['setup'],
            'entry': trade['entry'],
            'sl': trade['sl'],
            'target': trade['target'],
            'qty': trade['qty'],
            'entry_time': '09:15:00'
        }

        try:
            log_trade(trade_record)
            execution_log.append({
                'ticker': trade['ticker'],
                'status': 'filled',
                'entry': trade['entry'],
                'qty': trade['qty'],
                'time': '09:15:00'
            })
            print(f"  FILLED: {trade['ticker']} qty={trade['qty']} @ {trade['entry']}")
        except Exception as e:
            execution_log.append({
                'ticker': trade['ticker'],
                'status': 'error',
                'error': str(e)
            })
            print(f"  ERROR: {trade['ticker']} - {e}")

    state['execution_log'] = execution_log
    return state

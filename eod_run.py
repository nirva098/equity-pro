import json
from datetime import datetime
from core.db import init_db
from core.graph import build_eod_graph

def main():
    print("=" * 60)
    print("NSE Alpha Army — EOD Report")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Init DB
    init_db()

    # 2. Build initial state
    today = datetime.now().strftime('%Y-%m-%d')
    state = {
        'date': today,
        'market_context': {},
        'eod_pnl': {}
    }

    # 3. Compile and run graph
    print("\nCompiling EOD graph...")
    app = build_eod_graph()

    print("Running EOD pipeline...\n")
    result = app.invoke(state)

    # 4. Print summary
    eod = result.get('eod_pnl', {})
    print(f"\n{'=' * 60}")
    print(f"Trades processed: {eod.get('trades', 0)}")
    print(f"Win rate: {eod.get('win_rate', 0):.0f}%")
    print(f"Total R: {eod.get('total_R', 0):.2f}")
    print(f"Total P&L: ₹{eod.get('total_pnl_abs', 0):,.0f}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()

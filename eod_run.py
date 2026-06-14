import json
import os
from datetime import datetime
from core.research_db import init_research_db
from core.graph import build_eod_graph

def main():
    print("=" * 60)
    print("NSE Alpha Army — EOD Report")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Init DB
    init_research_db()

    # 2. Build initial state
    today = datetime.now().strftime('%Y-%m-%d')

    # Load market_context from today's premarket report (if available)
    market_context = {}
    report_path = f"reports/{today}_premarket.json"
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r') as f:
                premarket_report = json.load(f)
            market_context = premarket_report.get('market_context', {})
            print(f"Loaded market context from {report_path} (regime: {market_context.get('regime', 'unknown')})")
        except Exception as e:
            print(f"Warning: Could not load premarket report: {e}")
    else:
        print(f"No premarket report found at {report_path}, regime will be 'unknown'")

    state = {
        'date': today,
        'market_context': market_context,
        'eod_pnl': {},
        'feedback_loop': {}
    }

    # 3. Compile and run graph
    print("\nCompiling EOD graph...")
    app = build_eod_graph()

    print("Running EOD pipeline...\n")
    result = app.invoke(state)

    # 4. Print summary
    eod = result.get('eod_pnl', {})
    feedback = result.get('feedback_loop', {})
    print(f"\n{'=' * 60}")
    print(f"Trades processed: {eod.get('trades', 0)}")
    print(f"Win rate: {eod.get('win_rate', 0):.0f}%")
    print(f"Total R: {eod.get('total_R', 0):.2f}")
    print(f"Total P&L: ₹{eod.get('total_pnl_abs', 0):,.0f}")
    if feedback.get('headline'):
        print(f"Feedback: {feedback['headline']}")
        for line in feedback.get('next_cycle', [])[:3]:
            print(f"  - {line}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()

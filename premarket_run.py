import json
import pandas as pd
from datetime import datetime
from core.graph import build_premarket_graph
from core.research_db import (
    finish_research_run,
    persist_premarket_state,
    start_research_run,
    init_research_db,
)

def main():
    print("=" * 60)
    print("NSE Alpha Army — Pre-Market Run")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Init DB
    init_research_db()

    # 2. Load universe
    try:
        universe_df = pd.read_csv('data/universe_nse500.csv')
        tickers = universe_df['Ticker'].tolist()
        print(f"\nUniverse loaded: {len(tickers)} tickers")
    except Exception as e:
        print(f"Error loading universe: {e}")
        return

    # 3. Build initial state
    today = datetime.now().strftime('%Y-%m-%d')
    run_id = start_research_run(
        trade_date=today,
        run_type="premarket",
        scanned_count=len(tickers),
        metadata={"entrypoint": "premarket_run.py"},
    )
    state = {
        'run_id': run_id,
        'date': today,
        'universe': tickers,
        'market_context': {},
        'fundamentals': {},
        'technicals': {},
        'news_sentiment': {},
        'research_briefs': {},
        'catalyst_checks': {},
        'skeptic_reviews': {},
        'final_rankings': [],
        'thesis': {},
        'candidates': [],
        'screened_candidates': [],
        'trades': [],
        'execution_log': [],
        'eod_pnl': {},
        'strategy_memory': {},
        'active_setups': [],
        'risk_modifier': 1.0,
        'next_agent': ''
    }

    # 4. Compile and run graph
    print("\nCompiling premarket graph...")
    app = build_premarket_graph()

    print("Running premarket pipeline...\n")
    try:
        result = app.invoke(state)
        persist_premarket_state(run_id, result)
        finish_research_run(run_id, "success", result)
    except Exception as e:
        finish_research_run(run_id, "failed", state, error=str(e))
        raise

    # 5. Save report
    report = {
        'run_id': run_id,
        'date': today,
        'market_context': result.get('market_context', {}),
        'candidates': result.get('candidates', []),
        'screened_candidates': result.get('screened_candidates', []),
        'research_briefs': result.get('research_briefs', {}),
        'catalyst_checks': result.get('catalyst_checks', {}),
        'skeptic_reviews': result.get('skeptic_reviews', {}),
        'final_rankings': result.get('final_rankings', []),
        'trades': result.get('trades', []),
        'thesis': result.get('thesis', {}),
        'execution_log': result.get('execution_log', []),
        'active_setups': result.get('active_setups', []),
        'risk_modifier': result.get('risk_modifier', 1.0)
    }

    report_path = f"reports/{today}_premarket.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=4, default=str)

    print(f"\n{'=' * 60}")
    print(f"Research run_id: {run_id}")
    print(f"Report saved: {report_path}")
    print(f"Trades executed: {len(result.get('execution_log', []))}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()

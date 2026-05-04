"""
Backtest Harness: Simulates past 60 trading days to validate the RL loop
and verify no recency bias.

Usage:
    PYTHONPATH=. python3 backtest.py

What it does:
1. Generates synthetic trade data for the past 60 days across all 3 setups
2. Runs the RL updater after each day
3. Verifies the Laplace smoothing rule: weight stays >= 0.5 when trades < 30
4. Prints a summary of weight evolution
"""

import json
import sqlite3
import os
import shutil
from datetime import datetime, timedelta
from core.config import DB_PATH
from core.db import init_db, log_trade, update_trade_exit, get_closed_trades
from agents.rl_updater import run_rl_updater

# Backtest uses a separate DB and memory file
BACKTEST_DB = "backtest_trades.db"
BACKTEST_MEMORY = "memory/backtest_strategy_memory.json"

def _setup_backtest():
    """Create clean backtest environment."""
    # Use backtest DB
    import core.config
    core.config.DB_PATH = BACKTEST_DB

    # Remove old backtest files
    if os.path.exists(BACKTEST_DB):
        os.remove(BACKTEST_DB)

    # Init fresh DB
    with sqlite3.connect(BACKTEST_DB) as conn:
        with open('db/schema.sql', 'r') as f:
            conn.executescript(f.read())

    # Create fresh memory
    memory = {
        "setups": {
            "value_breakout": {"trades": 0, "wins": 0, "weight": 0.5, "notes": ""},
            "momentum_pullback": {"trades": 0, "wins": 0, "weight": 0.5, "notes": ""},
            "quality_compounder": {"trades": 0, "wins": 0, "weight": 0.5, "notes": ""}
        },
        "regime_multipliers": {"risk_on": 1.0, "risk_off": 0.5, "high_vix": 0.3},
        "special_events": []
    }
    with open(BACKTEST_MEMORY, 'w') as f:
        json.dump(memory, f, indent=4)

def _generate_synthetic_trades(num_days: int = 60):
    """
    Generate synthetic trade data.
    Momentum_pullback will have a deliberately bad streak (5 consecutive losses)
    to test recency bias protection.
    """
    import random
    random.seed(42)

    setups = ['value_breakout', 'momentum_pullback', 'quality_compounder']
    # Win rates: value=60%, momentum=40% (bad streak), quality=55%
    win_rates = {'value_breakout': 0.60, 'momentum_pullback': 0.40, 'quality_compounder': 0.55}

    trades_by_day = {}
    start_date = datetime.now() - timedelta(days=num_days)

    for day_offset in range(num_days):
        date = (start_date + timedelta(days=day_offset)).strftime('%Y-%m-%d')
        day_trades = []

        # 1-2 trades per day, random setup
        num_trades = random.randint(0, 2)
        for _ in range(num_trades):
            setup = random.choice(setups)
            entry = round(random.uniform(500, 3000), 2)
            atr = round(entry * 0.02, 2)
            sl = round(entry - 1.5 * atr, 2)
            target = round(entry + 3.0 * atr, 2)

            # Determine win/loss
            is_win = random.random() < win_rates[setup]

            # Force 5 consecutive losses for momentum between day 20-24
            if setup == 'momentum_pullback' and 20 <= day_offset <= 24:
                is_win = False

            if is_win:
                exit_price = round(entry + random.uniform(0.5, 3.0) * atr, 2)
                pnl_R = round((exit_price - entry) / (entry - sl), 2)
            else:
                exit_price = round(entry - random.uniform(0.5, 1.5) * atr, 2)
                pnl_R = round((exit_price - entry) / (entry - sl), 2)

            day_trades.append({
                'date': date,
                'ticker': f'TEST_{setup[:3].upper()}.NS',
                'setup': setup,
                'entry': entry,
                'sl': sl,
                'target': target,
                'qty': 10,
                'exit_price': exit_price,
                'pnl_R': pnl_R
            })

        if day_trades:
            trades_by_day[date] = day_trades

    return trades_by_day

def run_backtest():
    """Run the backtest."""
    print("=" * 60)
    print("BACKTEST HARNESS — 60 Day Simulation")
    print("=" * 60)

    _setup_backtest()

    # Monkey-patch DB_PATH for core.db module
    import core.db
    core.db.DB_PATH = BACKTEST_DB

    trades_by_day = _generate_synthetic_trades(60)

    weight_history = {
        'value_breakout': [],
        'momentum_pullback': [],
        'quality_compounder': []
    }

    # Track violations
    violations = []

    for date in sorted(trades_by_day.keys()):
        day_trades = trades_by_day[date]

        # Insert trades as open, then close them
        for t in day_trades:
            log_trade(t)

        # Close trades with exit data
        with sqlite3.connect(BACKTEST_DB) as conn:
            conn.row_factory = sqlite3.Row
            open_trades = conn.execute(
                "SELECT * FROM trades WHERE status = 'open' AND date = ?", (date,)
            ).fetchall()

            for i, row in enumerate(open_trades):
                trade_data = day_trades[i] if i < len(day_trades) else {}
                conn.execute(
                    "UPDATE trades SET exit_price = ?, pnl_R = ?, status = 'closed' WHERE id = ?",
                    (trade_data.get('exit_price', row['entry']),
                     trade_data.get('pnl_R', 0),
                     row['id'])
                )
            conn.commit()

        # Run RL updater — it reads from BACKTEST_MEMORY
        # Temporarily point rl_updater to backtest memory
        import agents.rl_updater as rl_mod

        # Save original open function and monkey-patch for memory file
        original_open = __builtins__['open'] if isinstance(__builtins__, dict) else __builtins__.open

        class MemoryRedirect:
            """Redirects strategy_memory.json reads/writes to backtest file."""
            def __init__(self):
                self.active = True

            def __call__(self, path, *args, **kwargs):
                if self.active and 'strategy_memory.json' in str(path):
                    return original_open(BACKTEST_MEMORY, *args, **kwargs)
                return original_open(path, *args, **kwargs)

        redirect = MemoryRedirect()
        if isinstance(__builtins__, dict):
            __builtins__['open'] = redirect
        else:
            import builtins
            builtins.open = redirect

        state = {'date': date, 'market_context': {'event_flag': 'none'}}
        state = run_rl_updater(state)

        # Restore original open
        if isinstance(__builtins__, dict):
            __builtins__['open'] = original_open
        else:
            import builtins
            builtins.open = original_open

        # Record weights
        memory = state.get('strategy_memory', {})
        for setup in weight_history:
            w = memory.get('setups', {}).get(setup, {}).get('weight', 0.5)
            t_count = memory.get('setups', {}).get(setup, {}).get('trades', 0)
            weight_history[setup].append((date, w, t_count))

            # Check violation: weight < 0.5 when trades < 30
            if t_count < 30 and w < 0.5:
                violations.append(f"  VIOLATION: {setup} weight={w} trades={t_count} on {date}")

    # Print results
    print(f"\n{'=' * 60}")
    print("WEIGHT EVOLUTION SUMMARY")
    print(f"{'=' * 60}")

    for setup in weight_history:
        entries = weight_history[setup]
        if entries:
            final_date, final_w, final_t = entries[-1]
            print(f"\n{setup}:")
            print(f"  Final weight: {final_w:.4f}")
            print(f"  Total trades: {final_t}")
            # Show last 5 data points
            for date, w, t in entries[-5:]:
                print(f"    {date}: weight={w:.4f} trades={t}")

    print(f"\n{'=' * 60}")
    print("RECENCY BIAS CHECK")
    print(f"{'=' * 60}")

    if violations:
        print("❌ VIOLATIONS FOUND:")
        for v in violations:
            print(v)
    else:
        print("✅ No violations: weights stayed >= 0.5 when trades < 30")

    # Cleanup
    if os.path.exists(BACKTEST_DB):
        os.remove(BACKTEST_DB)
    if os.path.exists(BACKTEST_MEMORY):
        os.remove(BACKTEST_MEMORY)

    print(f"\n{'=' * 60}")
    print("Backtest complete.")
    print(f"{'=' * 60}")

    return len(violations) == 0

if __name__ == "__main__":
    success = run_backtest()
    exit(0 if success else 1)

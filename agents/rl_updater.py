import json
from core.research_db import get_closed_trades, update_daily_feedback
from core.feedback_loop import build_feedback_loop, load_strategy_memory

def run_rl_updater(state: dict) -> dict:
    """
    RL Updater: Thompson Sampling with Laplace smoothing.
    
    For each closed trade today:
      - Increment trades count for the setup
      - If pnl_R > 0, increment wins
      - new_weight = (wins + 1) / (trades + 2)   # Laplace smoothing
      - If trades < 30: weight = max(weight, 0.5)  # Prevent recency bias
    
    Also logs any special events from market_context to memory.
    """
    today = state.get('date', '')
    market_context = state.get('market_context', {})

    memory_before = load_strategy_memory()
    memory = json.loads(json.dumps(memory_before))

    # Get closed trades for today
    closed_trades = get_closed_trades(today) if today else []

    if closed_trades:
        print(f"RL Updater: Processing {len(closed_trades)} closed trades...")

        for trade in closed_trades:
            setup = trade.get('setup', '')
            pnl_R = trade.get('pnl_R', 0)

            if setup not in memory.get('setups', {}):
                memory['setups'][setup] = {
                    'trades': 0, 'wins': 0, 'weight': 0.5, 'notes': ''
                }

            setup_data = memory['setups'][setup]
            setup_data['trades'] += 1

            if pnl_R > 0:
                setup_data['wins'] += 1

            # Thompson Sampling: Laplace smoothing
            new_weight = (setup_data['wins'] + 1) / (setup_data['trades'] + 2)

            # Prevent recency bias: if trades < 30, floor weight at 0.5
            if setup_data['trades'] < 30:
                new_weight = max(new_weight, 0.5)

            setup_data['weight'] = round(new_weight, 4)

            print(f"  {setup}: trades={setup_data['trades']}, wins={setup_data['wins']}, "
                  f"weight={setup_data['weight']}")

    else:
        print("RL Updater: No closed trades to process.")

    # Log special events from market context
    event_flag = market_context.get('event_flag', 'none')
    if event_flag != 'none' and today:
        event_entry = {
            'date': today,
            'event': event_flag,
            'regime': market_context.get('regime', 'unknown')
        }
        if event_entry not in memory.get('special_events', []):
            memory.setdefault('special_events', []).append(event_entry)
            print(f"  Logged special event: {event_flag} on {today}")

    # Save updated memory
    try:
        with open('memory/strategy_memory.json', 'w') as f:
            json.dump(memory, f, indent=4)
        print("RL Updater: strategy_memory.json updated.")
    except Exception as e:
        print(f"RL Updater: Error saving memory: {e}")

    state['strategy_memory'] = memory
    feedback_loop = build_feedback_loop(
        closed_trades=closed_trades,
        memory_before=memory_before,
        memory_after=memory,
        regime=market_context.get('regime', 'unknown'),
    )
    state['feedback_loop'] = feedback_loop
    if today:
        update_daily_feedback(today, feedback_loop)
    if feedback_loop.get('headline'):
        print(f"Feedback Loop: {feedback_loop['headline']}")
    return state

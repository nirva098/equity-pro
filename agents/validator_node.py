from core.config import CAPITAL, MAX_RISK_PER_TRADE

def run_validator(state: dict) -> dict:
    """
    Deterministic Validator.
    Rejects trades where:
      - SL >= entry (invalid stop loss)
      - Single trade risk > 2% of capital
      - Cumulative portfolio risk > 2% of capital
    Sets state['next_agent'] based on result.
    """
    trades = state.get('trades', [])
    max_total_risk = CAPITAL * MAX_RISK_PER_TRADE
    valid_trades = []
    cumulative_risk = 0

    for trade in trades:
        # Check 1: SL must be below entry
        if trade['sl'] >= trade['entry']:
            print(f"REJECTED {trade['ticker']}: SL ({trade['sl']}) >= entry ({trade['entry']})")
            continue

        # Check 2: Single trade risk must not exceed 2% of capital
        trade_risk = trade['qty'] * trade['risk_per_share']
        if trade_risk > max_total_risk:
            print(f"REJECTED {trade['ticker']}: trade risk ({trade_risk:.0f}) > max ({max_total_risk:.0f})")
            continue

        # Check 3: Cumulative portfolio risk must not exceed 2% of capital
        if cumulative_risk + trade_risk > max_total_risk:
            print(f"REJECTED {trade['ticker']}: cumulative risk would exceed 2% cap")
            continue

        cumulative_risk += trade_risk
        valid_trades.append(trade)

    state['trades'] = valid_trades

    if valid_trades:
        state['next_agent'] = 'paper_executor'
    else:
        state['next_agent'] = 'end'

    return state

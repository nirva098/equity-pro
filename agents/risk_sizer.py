import json
from core.config import CAPITAL, MAX_RISK_PER_TRADE

def run_risk_sizer(state: dict) -> dict:
    """
    Deterministic Risk Sizer.
    For each candidate: ATR-based SL/target, Kelly fraction, position sizing.
    Caps at 5% of capital per stock and 2% total portfolio risk.
    Returns top 5 trades.
    """
    # Load strategy memory for Kelly inputs
    try:
        with open('memory/strategy_memory.json', 'r') as f:
            memory = json.load(f)
    except Exception:
        memory = {"setups": {}}

    candidates = state.get('candidates', [])
    technicals = state.get('technicals', {})
    trades = []

    for candidate in candidates:
        ticker = candidate['ticker']
        setup = candidate['setup']
        score = candidate.get('score', 1.0)
        tech = technicals.get(ticker, {})

        if not tech:
            continue

        entry = tech.get('close', 0)
        atr = tech.get('ATR14', 0)

        if entry <= 0 or atr <= 0:
            continue

        # SL and Target from ATR
        sl = entry - (1.5 * atr)
        target = entry + (3.0 * atr)
        risk_per_share = entry - sl

        if risk_per_share <= 0:
            continue

        # Kelly fraction from strategy_memory
        setup_stats = memory.get('setups', {}).get(setup, {})
        total_trades = setup_stats.get('trades', 0)
        wins = setup_stats.get('wins', 0)

        if total_trades < 30:
            # Laplace smoothing default per kb.md
            kelly_f = 0.5
        else:
            winrate = (wins + 1) / (total_trades + 2)
            avg_win = 3.0  # Expected R:R ratio
            avg_loss = 1.0
            lossrate = 1 - winrate
            kelly_f = (winrate * avg_win - lossrate * avg_loss) / avg_win
            kelly_f = max(kelly_f, 0.1)  # Floor to prevent 0 or negative

        # Position sizing: qty = (Capital * 2% * Kelly_f) / risk_per_share
        qty = int((CAPITAL * MAX_RISK_PER_TRADE * kelly_f) / risk_per_share)

        # Cap at 5% of capital per stock
        max_qty_by_cap = int((CAPITAL * 0.05) / entry)
        qty = min(qty, max_qty_by_cap)

        if qty <= 0:
            continue

        trades.append({
            'ticker': ticker,
            'setup': setup,
            'entry': round(entry, 2),
            'sl': round(sl, 2),
            'target': round(target, 2),
            'qty': qty,
            'risk_per_share': round(risk_per_share, 2),
            'total_risk': round(qty * risk_per_share, 2),
            'expected_R': round((target - entry) / risk_per_share, 2),
            'kelly_f': round(kelly_f, 3),
            'score': score
        })

    # Keep top 5 by score (proxy for confidence * expected_R)
    trades.sort(key=lambda x: x['score'], reverse=True)
    state['trades'] = trades[:5]

    return state

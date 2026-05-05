import json
from core.config import CAPITAL, MAX_RISK_PER_TRADE


def run_risk_sizer(state: dict) -> dict:
    """
    Deterministic Risk Sizer.
    - ATR-based SL (1.5×ATR below entry, or Pivot S1 if closer)
    - Target = 3×ATR above entry (2:1 R:R minimum)
    - Kelly fraction from strategy_memory (quarter-Kelly cold-start)
    - News sentiment gate: bearish sentiment disqualifies; bullish gets full Kelly, neutral gets 80%
    - Setup diversity cap: max 2 trades per setup in final list
    - Returns top 5 diversified trades by score
    """
    try:
        with open('memory/strategy_memory.json', 'r') as f:
            memory = json.load(f)
    except Exception:
        memory = {"setups": {}}

    candidates     = state.get('candidates', [])
    technicals     = state.get('technicals', {})
    news_sentiment = state.get('news_sentiment', {})
    trades = []

    for candidate in candidates:
        ticker = candidate['ticker']
        setup  = candidate['setup']
        score  = candidate.get('score', 1.0)
        tech   = technicals.get(ticker, {})

        if not tech:
            continue

        entry = tech.get('close', 0)
        atr   = tech.get('ATR14', 0)

        if entry <= 0 or atr <= 0:
            continue

        # --- News sentiment gate ---
        sentiment = news_sentiment.get(ticker, {}).get('sentiment', 'neutral')
        if sentiment == 'bearish':
            print(f"  SKIPPED {ticker}: bearish news sentiment")
            continue
        news_kelly_mod = 1.0 if sentiment == 'bullish' else 0.8  # neutral = 80% Kelly

        # --- SL: 1.5×ATR or Pivot S1, whichever is closer to entry (tighter stop) ---
        atr_sl    = entry - (1.5 * atr)
        pivot_sl  = tech.get('Pivot_S1', 0)
        # Use pivot S1 if it's within 3×ATR of entry and above the ATR-based SL
        if pivot_sl > atr_sl and pivot_sl < entry and (entry - pivot_sl) < 3 * atr:
            sl = pivot_sl
        else:
            sl = atr_sl

        target        = entry + (3.0 * atr)
        risk_per_share = entry - sl

        if risk_per_share <= 0:
            continue

        # --- Kelly fraction ---
        setup_stats  = memory.get('setups', {}).get(setup, {})
        total_trades = setup_stats.get('trades', 0)
        wins         = setup_stats.get('wins', 0)

        if total_trades < 30:
            kelly_f = 0.25  # Quarter-Kelly cold-start
        else:
            winrate = (wins + 1) / (total_trades + 2)
            kelly_f = (winrate * 3.0 - (1 - winrate) * 1.0) / 3.0
            kelly_f = max(kelly_f, 0.1)

        kelly_f = kelly_f * news_kelly_mod

        # --- Position sizing ---
        qty = int((CAPITAL * MAX_RISK_PER_TRADE * kelly_f) / risk_per_share)
        max_by_cap = int((CAPITAL * 0.05) / entry)
        qty = min(qty, max_by_cap)

        if qty <= 0:
            continue

        trades.append({
            'ticker':         ticker,
            'setup':          setup,
            'entry':          round(entry, 2),
            'sl':             round(sl, 2),
            'target':         round(target, 2),
            'qty':            qty,
            'risk_per_share': round(risk_per_share, 2),
            'total_risk':     round(qty * risk_per_share, 2),
            'expected_R':     round((target - entry) / risk_per_share, 2),
            'kelly_f':        round(kelly_f, 3),
            'score':          score,
            'news_sentiment': sentiment,
        })

    # Sort by score descending
    trades.sort(key=lambda x: x['score'], reverse=True)

    # --- Setup diversity cap: max 2 per setup ---
    setup_counts: dict = {}
    diversified  = []
    for trade in trades:
        s = trade['setup']
        if setup_counts.get(s, 0) >= 2:
            print(f"  DIVERSITY CAP: {trade['ticker']} skipped ({s} already has 2 trades)")
            continue
        setup_counts[s] = setup_counts.get(s, 0) + 1
        diversified.append(trade)
        if len(diversified) >= 5:
            break

    state['trades'] = diversified
    print(f"Risk sizer: {len(diversified)} trades selected "
          f"({', '.join(f'{k}×{v}' for k,v in setup_counts.items())})")
    return state

import json


def _composite_score(weight: float, fund: dict, tech: dict, setup: str) -> float:
    """
    Composite conviction score for a candidate.
    Base: strategy_memory weight * fixed expected_R (3.0).
    Bonus factors differentiate candidates within the same setup.

    Score range: approximately 0.0 – 5.0
    """
    base = weight * 3.0

    # --- Bonus: fundamental quality ---
    # FCF yield bonus: +0.1 per 1% above threshold (up to +0.5)
    fcf_bonus = min((fund.get('FCF_Yield_%', 0) - 8) * 0.1, 0.5) if fund.get('FCF_Yield_%', 0) > 8 else 0

    # DCF upside bonus: +0.1 per 10% upside above threshold (up to +0.5)
    dcf_bonus = min((fund.get('DCF_Upside_%', 0) - 25) / 100, 0.5) if fund.get('DCF_Upside_%', 0) > 25 else 0

    # Piotroski F-Score bonus: +0.05 per point above 7 (max +0.1)
    f_bonus = min((fund.get('F_Score', 0) - 7) * 0.05, 0.1) if fund.get('F_Score', 0) > 7 else 0

    # ROCE bonus: +0.02 per 1% above 18% (up to +0.2)
    roce_bonus = min((fund.get('ROCE_%', 0) - 18) * 0.02, 0.2) if fund.get('ROCE_%', 0) > 18 else 0

    # --- Bonus: technical confirmation ---
    # Breakout confirmation: strong signal
    breakout_bonus = 0.3 if tech.get('Breakout', False) else 0

    # Proximity to 52w high: tighter = higher conviction for quality_compounder
    dist_bonus = 0
    if setup == 'quality_compounder':
        dist_52w = tech.get('Distance_to_52w_High_%', 100)
        dist_bonus = max(0, (5 - dist_52w) * 0.04)  # +0.04 per 1% closer (max +0.2 at 0%)

    # RSI pullback depth for momentum_pullback: deeper = better entry
    rsi_bonus = 0
    if setup == 'momentum_pullback':
        rsi = tech.get('RSI14', 50)
        rsi_bonus = max(0, (40 - rsi) * 0.02)  # +0.02 per RSI point below 40 (max +0.4 at RSI=20)

    # --- Penalty: low D/E quality check (only for value/quality setups) ---
    de_ratio = fund.get('DE_Ratio', 0)
    de_penalty = 0
    if setup in ('value_breakout', 'quality_compounder') and de_ratio > 1.0:
        de_penalty = min((de_ratio - 1.0) * 0.1, 0.3)  # Penalty grows with leverage

    total = base + fcf_bonus + dcf_bonus + f_bonus + roce_bonus + breakout_bonus + dist_bonus + rsi_bonus - de_penalty
    return round(total, 4)


def run_quant_screener(state: dict) -> dict:
    """
    Deterministic Quant Screener.
    Applies 3 rule-based setups against fundamentals + technicals.
    Respects active_setups from supervisor.
    Ranks candidates by composite conviction score.
    Returns top 20.

    Setups:
      value_breakout:     FCF_yield > 8% AND DCF_upside > 25% AND F_score > 7 AND price > 200DMA
      momentum_pullback:  3M_ret > 15% AND RSI < 40 AND price > 50DMA AND ADX > 25
      quality_compounder: ROCE > 18% AND D/E < 0.5 AND 52w_high_distance < 5%
    """
    # Load strategy memory for weights
    try:
        with open('memory/strategy_memory.json', 'r') as f:
            memory = json.load(f)
    except Exception:
        memory = {"setups": {
            "value_breakout": {"weight": 0.5},
            "momentum_pullback": {"weight": 0.5},
            "quality_compounder": {"weight": 0.5}
        }}

    # Respect supervisor's active_setups decision
    active_setups = state.get('active_setups', list(memory.get('setups', {}).keys()))
    if not active_setups:
        active_setups = list(memory.get('setups', {}).keys())

    fundamentals = state.get('fundamentals', {})
    technicals = state.get('technicals', {})
    candidates = []

    for ticker in fundamentals:
        fund = fundamentals[ticker]
        tech = technicals.get(ticker, {})

        if not tech:
            continue

        close = tech.get('close', 0)

        # --- Setup 1: value_breakout ---
        # FCF_yield > 8% AND DCF_upside > 25% AND F_score > 7 AND price > 200DMA
        if 'value_breakout' in active_setups:
            if (fund.get('FCF_Yield_%', 0) > 8 and
                    fund.get('DCF_Upside_%', 0) > 25 and
                    fund.get('F_Score', 0) > 7 and
                    close > tech.get('DMA200', 0) and tech.get('DMA200', 0) > 0):

                weight = memory['setups'].get('value_breakout', {}).get('weight', 0.5)
                score = _composite_score(weight, fund, tech, 'value_breakout')
                candidates.append({
                    'ticker': ticker,
                    'setup': 'value_breakout',
                    'score': score,
                    'expected_R': 3.0
                })

        # --- Setup 2: momentum_pullback ---
        # 3M_ret > 15% AND RSI < 40 AND price > 50DMA AND ADX > 25
        if 'momentum_pullback' in active_setups:
            if (tech.get('3M_Return_%', 0) > 15 and
                    tech.get('RSI14', 50) < 40 and
                    close > tech.get('DMA50', 0) and tech.get('DMA50', 0) > 0 and
                    tech.get('ADX14', 0) > 25):

                weight = memory['setups'].get('momentum_pullback', {}).get('weight', 0.5)
                score = _composite_score(weight, fund, tech, 'momentum_pullback')
                candidates.append({
                    'ticker': ticker,
                    'setup': 'momentum_pullback',
                    'score': score,
                    'expected_R': 3.0
                })

        # --- Setup 3: quality_compounder ---
        # ROCE > 18% AND D/E < 0.5 AND 52w_high_distance < 5%
        if 'quality_compounder' in active_setups:
            if (fund.get('ROCE_%', 0) > 18 and
                    fund.get('DE_Ratio', 999) < 0.5 and
                    tech.get('Distance_to_52w_High_%', 100) < 5):

                weight = memory['setups'].get('quality_compounder', {}).get('weight', 0.5)
                score = _composite_score(weight, fund, tech, 'quality_compounder')
                candidates.append({
                    'ticker': ticker,
                    'setup': 'quality_compounder',
                    'score': score,
                    'expected_R': 3.0
                })

    # Rank by composite score, take top 20
    candidates.sort(key=lambda x: x['score'], reverse=True)
    state['candidates'] = candidates[:20]

    print(f"Screener: {len(candidates)} total candidates, top {min(len(candidates), 20)} forwarded.")
    if candidates:
        print(f"  Top 3: {[(c['ticker'], c['setup'], c['score']) for c in candidates[:3]]}")

    return state

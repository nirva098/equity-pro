import json

def run_quant_screener(state: dict) -> dict:
    """
    Deterministic Quant Screener.
    Applies 3 rule-based setups against fundamentals + technicals.
    Ranks candidates by strategy_memory weight * expected_R.
    Returns top 20.
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

    fundamentals = state.get('fundamentals', {})
    technicals = state.get('technicals', {})
    candidates = []

    for ticker in fundamentals:
        fund = fundamentals[ticker]
        tech = technicals.get(ticker, {})

        if not tech:
            continue

        close = tech.get('close', 0)
        expected_R = 3.0  # Fixed R:R from ATR sizing (target = 3*ATR, SL = 1.5*ATR)

        # --- value_breakout ---
        # FCF_yield > 8 AND DCF_upside > 25% AND F_score > 7 AND price > 200DMA
        if (fund.get('FCF_Yield_%', 0) > 8 and
            fund.get('DCF_Upside_%', 0) > 25 and
            fund.get('F_Score', 0) > 7 and
            close > tech.get('DMA200', 0) and tech.get('DMA200', 0) > 0):

            weight = memory['setups'].get('value_breakout', {}).get('weight', 0.5)
            candidates.append({
                'ticker': ticker,
                'setup': 'value_breakout',
                'score': weight * expected_R,
                'expected_R': expected_R
            })

        # --- momentum_pullback ---
        # 3M_ret > 15% AND RSI < 40 AND price > 50DMA AND ADX > 25
        if (tech.get('3M_Return_%', 0) > 15 and
            tech.get('RSI14', 50) < 40 and
            close > tech.get('DMA50', 0) and tech.get('DMA50', 0) > 0 and
            tech.get('ADX14', 0) > 25):

            weight = memory['setups'].get('momentum_pullback', {}).get('weight', 0.5)
            candidates.append({
                'ticker': ticker,
                'setup': 'momentum_pullback',
                'score': weight * expected_R,
                'expected_R': expected_R
            })

        # --- quality_compounder ---
        # ROCE > 18% AND 52w_high_distance < 5%
        if (fund.get('ROCE_%', 0) > 18 and
            tech.get('Distance_to_52w_High_%', 100) < 5):

            weight = memory['setups'].get('quality_compounder', {}).get('weight', 0.5)
            candidates.append({
                'ticker': ticker,
                'setup': 'quality_compounder',
                'score': weight * expected_R,
                'expected_R': expected_R
            })

    # Rank by score, take top 20
    candidates.sort(key=lambda x: x['score'], reverse=True)
    state['candidates'] = candidates[:20]

    return state

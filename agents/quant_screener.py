import json
from statistics import mean, pstdev


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _score_higher(value: float, poor: float, good: float) -> float:
    if good == poor:
        return 0.0
    return _clip((value - poor) / (good - poor))


def _score_lower(value: float, poor: float, good: float) -> float:
    if good == poor:
        return 0.0
    return _clip((poor - value) / (poor - good))


def _cross_sectional_ranks(rows: list[dict], key: str) -> dict:
    values = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    if not values:
        return {}
    mu = mean(values)
    sigma = pstdev(values) or 1.0
    return {r['ticker']: _clip(0.5 + ((r.get(key, mu) - mu) / sigma) / 6) for r in rows}


def _candidate_score(weight: float, fund: dict, tech: dict, setup: str, ranks: dict) -> tuple[float, list[str]]:
    """
    Multi-factor score instead of a brittle all-or-nothing filter.
    The output is designed for ranking research candidates; risk controls still happen later.
    """
    ticker = fund.get('_ticker')
    f_score = _score_higher(fund.get('F_Score', 0), 3, 8)
    roce = _score_higher(fund.get('ROCE_%', 0), 0, 30)
    debt = _score_lower(fund.get('DE_Ratio', 3), 3, 0.2)
    fcf = _score_higher(fund.get('FCF_Yield_%', 0), -5, 8)
    dcf = _score_higher(fund.get('DCF_Upside_%', 0), -40, 60)
    momentum = _score_higher(tech.get('3M_Return_%', 0), -15, 25)
    trend_50 = 1.0 if tech.get('close', 0) > tech.get('DMA50', 0) > 0 else 0.0
    trend_200 = 1.0 if tech.get('close', 0) > tech.get('DMA200', 0) > 0 else 0.0
    rsi = tech.get('RSI14', 50)
    pullback = _clip(1 - abs(rsi - 45) / 25)
    adx = _score_higher(tech.get('ADX14', 0), 12, 35)
    near_high = _score_lower(tech.get('Distance_to_52w_High_%', 100), 35, 3)
    volume = _score_higher(tech.get('Volume_Ratio', 1), 0.4, 1.6)
    breakout = 1.0 if tech.get('Breakout') else 0.0
    relative_momentum = ranks.get('3M_Return_%', {}).get(ticker, 0.5)
    relative_quality = ranks.get('ROCE_%', {}).get(ticker, 0.5)

    if setup == 'value_breakout':
        raw = (
            0.22 * fcf + 0.20 * dcf + 0.14 * f_score + 0.10 * roce +
            0.12 * trend_200 + 0.10 * breakout + 0.07 * volume + 0.05 * debt
        )
        reasons = [
            f"FCF yield {fund.get('FCF_Yield_%', 0)}%",
            f"DCF upside {fund.get('DCF_Upside_%', 0)}%",
            "above 200DMA" if trend_200 else "below 200DMA",
        ]
    elif setup == 'momentum_pullback':
        raw = (
            0.22 * momentum + 0.16 * relative_momentum + 0.16 * pullback +
            0.14 * trend_50 + 0.12 * adx + 0.10 * volume +
            0.06 * f_score + 0.04 * debt
        )
        reasons = [
            f"3M return {tech.get('3M_Return_%', 0)}%",
            f"RSI {tech.get('RSI14', 0)}",
            f"ADX {tech.get('ADX14', 0)}",
        ]
    else:
        raw = (
            0.24 * roce + 0.18 * f_score + 0.16 * debt +
            0.14 * near_high + 0.10 * relative_quality +
            0.08 * trend_200 + 0.06 * momentum + 0.04 * volume
        )
        reasons = [
            f"ROCE {fund.get('ROCE_%', 0)}%",
            f"D/E {fund.get('DE_Ratio', 0)}",
            f"{tech.get('Distance_to_52w_High_%', 0)}% from 52w high",
        ]

    score = (raw * 4.0) + (weight * 1.5)
    return round(score, 4), reasons


def run_quant_screener(state: dict) -> dict:
    """
    Quant research funnel.
    Produces ranked ideas even when no stock satisfies every legacy rule exactly.
    Hard rule passes are tagged, but partial high-quality setups are still forwarded.
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
    rows = []

    for ticker in fundamentals:
        fund = fundamentals[ticker]
        tech = technicals.get(ticker, {})

        if not tech:
            continue

        close = tech.get('close', 0)
        if close <= 0 or tech.get('ATR14', 0) <= 0:
            continue

        row = {'ticker': ticker}
        row.update(fund)
        row.update(tech)
        rows.append(row)

    ranks = {
        '3M_Return_%': _cross_sectional_ranks(rows, '3M_Return_%'),
        'ROCE_%': _cross_sectional_ranks(rows, 'ROCE_%'),
    }

    for row in rows:
        ticker = row['ticker']
        fund = fundamentals[ticker].copy()
        fund['_ticker'] = ticker
        tech = technicals[ticker]
        close = tech.get('close', 0)

        # --- Setup 1: value_breakout ---
        if 'value_breakout' in active_setups:
            hard_pass = (
                fund.get('FCF_Yield_%', 0) > 4 and
                fund.get('DCF_Upside_%', 0) > 10 and
                fund.get('F_Score', 0) >= 6 and
                close > tech.get('DMA200', 0) > 0
            )
            weight = memory['setups'].get('value_breakout', {}).get('weight', 0.5)
            score, reasons = _candidate_score(weight, fund, tech, 'value_breakout', ranks)
            if hard_pass or score >= 2.25:
                candidates.append({
                    'ticker': ticker,
                    'setup': 'value_breakout',
                    'score': score,
                    'expected_R': 2.5,
                    'hard_pass': hard_pass,
                    'quant_reasons': reasons,
                })

        # --- Setup 2: momentum_pullback ---
        if 'momentum_pullback' in active_setups:
            hard_pass = (
                tech.get('3M_Return_%', 0) > 10 and
                tech.get('RSI14', 50) < 50 and
                close > tech.get('DMA50', 0) > 0 and
                tech.get('ADX14', 0) > 20
            )
            weight = memory['setups'].get('momentum_pullback', {}).get('weight', 0.5)
            score, reasons = _candidate_score(weight, fund, tech, 'momentum_pullback', ranks)
            if hard_pass or score >= 2.35:
                candidates.append({
                    'ticker': ticker,
                    'setup': 'momentum_pullback',
                    'score': score,
                    'expected_R': 2.5,
                    'hard_pass': hard_pass,
                    'quant_reasons': reasons,
                })

        # --- Setup 3: quality_compounder ---
        if 'quality_compounder' in active_setups:
            hard_pass = (
                fund.get('ROCE_%', 0) > 15 and
                fund.get('DE_Ratio', 999) < 1.0 and
                tech.get('Distance_to_52w_High_%', 100) < 10
            )
            weight = memory['setups'].get('quality_compounder', {}).get('weight', 0.5)
            score, reasons = _candidate_score(weight, fund, tech, 'quality_compounder', ranks)
            if hard_pass or score >= 2.30:
                candidates.append({
                    'ticker': ticker,
                    'setup': 'quality_compounder',
                    'score': score,
                    'expected_R': 2.5,
                    'hard_pass': hard_pass,
                    'quant_reasons': reasons,
                })

    # Rank by composite score, take top 20
    candidates.sort(key=lambda x: x['score'], reverse=True)
    state['candidates'] = candidates[:20]
    state['screened_candidates'] = candidates[:20]

    print(f"Screener: {len(candidates)} total candidates, top {min(len(candidates), 20)} forwarded.")
    if candidates:
        print(f"  Top 3: {[(c['ticker'], c['setup'], c['score']) for c in candidates[:3]]}")
    else:
        print("  No candidates had enough data/score to forward.")

    return state

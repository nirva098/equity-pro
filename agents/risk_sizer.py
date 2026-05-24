import json
from core.config import CAPITAL, MAX_RISK_PER_TRADE


# ── Target selection ────────────────────────────────────────────────────────

def _pick_target(setup: str, entry: float, atr: float, tech: dict, fund: dict) -> float:
    """
    Picks the most realistic exit target anchored to real market structure.

    Priority per setup:
      value_breakout     → Swing_High_1 → Pivot_R1 → Swing_High_2 → 2.5×ATR fallback
      momentum_pullback  → Swing_High_1 → 52w-high mean-reversion → 2.5×ATR fallback
      quality_compounder → 0.65×DCF upside → Swing_High_2 → Swing_High_1 → 2.5×ATR fallback

    A resistance level is only used as a target if it delivers at least 1.8R
    (verified again later by the validator after SL is finalised).
    """
    sh1  = tech.get('Swing_High_1', 0.0)
    sh2  = tech.get('Swing_High_2', 0.0)
    r1   = tech.get('Pivot_R1', 0.0)
    dist = tech.get('Distance_to_52w_High_%', 0.0)
    dcf  = fund.get('DCF_Upside_%', 0.0) if fund else 0.0

    risk = atr * 1.5  # approximate risk before SL is finalised

    def valid_target(t: float, min_r: float = 1.5) -> bool:
        """Returns True if the level is above entry and delivers at least min_r × risk."""
        return t > entry * 1.002 and (t - entry) >= min_r * risk

    if setup == 'value_breakout':
        # Prefer the first real swing high above price
        for candidate in [sh1, r1, sh2]:
            if valid_target(candidate):
                return round(candidate, 2)
        return round(entry + 2.5 * atr, 2)

    elif setup == 'momentum_pullback':
        # Strong preference for the nearest swing high — this is where prior sellers live
        if valid_target(sh1):
            return round(sh1, 2)
        # If dist_to_52w is known and meaningful, aim for partial mean-reversion to 52w high
        if dist > 2.0:
            # Travel 60% of the remaining distance to the 52-week high
            target_52w = entry * (1 + (dist / 100) * 0.60)
            if valid_target(target_52w):
                return round(target_52w, 2)
        if valid_target(sh2):
            return round(sh2, 2)
        return round(entry + 2.5 * atr, 2)

    else:  # quality_compounder
        # Use a conservative fraction of DCF upside as the swing target
        if dcf > 10:
            dcf_target = entry * (1 + (dcf / 100) * 0.65)
            if valid_target(dcf_target):
                return round(dcf_target, 2)
        # Fall back to second swing high (quality stocks tend to retest prior multi-month highs)
        for candidate in [sh2, sh1, r1]:
            if valid_target(candidate):
                return round(candidate, 2)
        return round(entry + 2.5 * atr, 2)


def _pick_sl(entry: float, atr: float, tech: dict) -> float:
    """
    Stop loss anchored to market structure (swing low) where available,
    falling back to ATR-based stop.
    """
    sl1   = tech.get('Swing_Low_1', 0.0)
    pivot = tech.get('Pivot_S1', 0.0)
    atr_sl = entry - 1.5 * atr

    # Swing low: use if it's between 1×ATR and 3×ATR from entry (not too tight, not too wide)
    if sl1 > 0 and (1.0 * atr) <= (entry - sl1) <= (3.0 * atr):
        return round(sl1, 2)

    # Pivot S1: use if tighter than ATR stop but still within 2.5×ATR
    if pivot > 0 and pivot < entry and (entry - pivot) <= (2.5 * atr):
        return round(max(pivot, atr_sl), 2)

    return round(atr_sl, 2)


def _pick_entry(setup: str, close: float, tech: dict) -> float:
    """
    Setup-specific entry price, avoiding market gap-up fills.

    - value_breakout:     close × 0.999  (tiny buffer; stock already breaking out, don't miss)
    - momentum_pullback:  min(close, DMA20 × 1.003)  (anchor to the natural bounce zone)
    - quality_compounder: close × 0.997  (patient entry; 0.3% discount vs chasing)
    """
    if setup == 'momentum_pullback':
        dma20 = tech.get('DMA20', 0.0)
        # Anchor to DMA20 if price is within 1.5% of it — the pullback magnet
        if dma20 > 0 and abs(close - dma20) / close <= 0.015:
            return round(min(close, dma20 * 1.003), 2)
        return round(close * 0.999, 2)
    elif setup == 'quality_compounder':
        return round(close * 0.997, 2)
    else:  # value_breakout
        return round(close * 0.999, 2)


# ── Main sizer ──────────────────────────────────────────────────────────────

def run_risk_sizer(state: dict) -> dict:
    """
    Smart Risk Sizer.

    Per trade:
      - Setup-specific entry (limit buffer, not market price)
      - SL anchored to swing low / Pivot S1 with ATR floor
      - Target anchored to swing highs / DCF / 52w mean-reversion
      - Rejects any trade with final R < 1.8
      - Kelly fraction from strategy_memory (quarter-Kelly cold-start)
      - News sentiment gate: bearish skips; bullish = full Kelly, neutral = 80%
      - Position_bias from ranking agent (half / full)
      - Setup diversity cap: max 2 trades per setup, top 5 output
    """
    try:
        with open('memory/strategy_memory.json', 'r') as f:
            memory = json.load(f)
    except Exception:
        memory = {"setups": {}}

    candidates     = state.get('candidates', [])
    technicals     = state.get('technicals', {})
    fundamentals   = state.get('fundamentals', {})
    news_sentiment = state.get('news_sentiment', {})
    risk_modifier  = max(0.25, min(1.5, float(state.get('risk_modifier', 1.0))))
    trades = []

    for candidate in candidates:
        ticker = candidate['ticker']
        setup  = candidate['setup']
        score  = candidate.get('score', 1.0)
        tech   = technicals.get(ticker, {})
        fund   = fundamentals.get(ticker, {})
        position_bias = candidate.get('position_bias', 'full')

        if not tech:
            continue

        close = tech.get('close', 0.0)
        atr   = tech.get('ATR14', 0.0)

        if close <= 0 or atr <= 0:
            continue

        # --- News sentiment gate ---
        sentiment = news_sentiment.get(ticker, {}).get('sentiment', 'neutral')
        if sentiment == 'bearish':
            print(f"  SKIPPED {ticker}: bearish news sentiment")
            continue
        news_kelly_mod = 1.0 if sentiment == 'bullish' else 0.8

        # --- Smart entry, SL, target ---
        entry  = _pick_entry(setup, close, tech)
        sl     = _pick_sl(entry, atr, tech)
        target = _pick_target(setup, entry, atr, tech, fund)

        risk_per_share = entry - sl
        if risk_per_share <= 0:
            continue

        expected_R = (target - entry) / risk_per_share

        # ── Conviction gate: minimum R ──────────────────────────────────────
        if expected_R < 1.8:
            print(f"  SKIPPED {ticker}: expected_R={expected_R:.2f} < 1.8 minimum "
                  f"(entry={entry}, target={target}, sl={sl})")
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

        bias_mod = 0.5 if position_bias == 'half' else 1.0
        kelly_f  = kelly_f * news_kelly_mod * risk_modifier * bias_mod

        # --- Position sizing ---
        qty = int((CAPITAL * MAX_RISK_PER_TRADE * kelly_f) / risk_per_share)
        max_by_cap = int((CAPITAL * 0.05) / entry)
        qty = min(qty, max_by_cap)

        if qty <= 0:
            continue

        target_source = "swing_high" if (tech.get('Swing_High_1', 0) == target or
                                          tech.get('Swing_High_2', 0) == target) else (
                         "dcf" if fund.get('DCF_Upside_%', 0) > 10 and
                                  abs(entry * (1 + fund.get('DCF_Upside_%', 0) / 100 * 0.65) - target) < 1
                         else "pivot_r1" if tech.get('Pivot_R1', 0) == target else "atr")

        trades.append({
            'ticker':         ticker,
            'setup':          setup,
            'entry':          entry,
            'sl':             sl,
            'target':         target,
            'target_source':  target_source,
            'qty':            qty,
            'risk_per_share': round(risk_per_share, 2),
            'total_risk':     round(qty * risk_per_share, 2),
            'expected_R':     round(expected_R, 2),
            'kelly_f':        round(kelly_f, 3),
            'score':          score,
            'news_sentiment': sentiment,
            'quant_reasons':  candidate.get('quant_reasons', []),
            'hard_pass':      candidate.get('hard_pass', False),
            'ai_rank':        candidate.get('ai_rank'),
            'ai_conviction':  candidate.get('ai_conviction'),
            'why_now':        candidate.get('why_now'),
            'why_this_over_others': candidate.get('why_this_over_others'),
            'position_bias':  position_bias,
        })

    # Sort by composite of score and conviction
    trades.sort(key=lambda x: (x.get('score', 0) + (x.get('ai_conviction') or 0) / 10.0), reverse=True)

    # --- Setup diversity cap: max 2 per setup ---
    setup_counts: dict = {}
    ticker_seen = set()
    diversified  = []
    for trade in trades:
        s = trade['setup']
        if trade['ticker'] in ticker_seen:
            print(f"  DUPLICATE: {trade['ticker']} skipped (already selected)")
            continue
        if setup_counts.get(s, 0) >= 2:
            print(f"  DIVERSITY CAP: {trade['ticker']} skipped ({s} already has 2 trades)")
            continue
        setup_counts[s] = setup_counts.get(s, 0) + 1
        ticker_seen.add(trade['ticker'])
        diversified.append(trade)
        if len(diversified) >= 5:
            break

    state['trades'] = diversified
    print(f"Risk sizer: {len(diversified)} trades selected "
          f"({', '.join(f'{k}×{v}' for k, v in setup_counts.items())}); "
          f"risk_modifier={risk_modifier}")
    for t in diversified:
        print(f"  {t['ticker']:20s} entry={t['entry']:8.2f}  sl={t['sl']:8.2f}  "
              f"target={t['target']:8.2f} [{t['target_source']:12s}]  "
              f"R={t['expected_R']:.2f}  qty={t['qty']}")
    return state



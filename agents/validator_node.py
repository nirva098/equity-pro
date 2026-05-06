import re
from core.config import CAPITAL, MAX_RISK_PER_TRADE, MAX_PORTFOLIO_RISK_PER_DAY

def _extract_numbers(text: str) -> list:
    """Extract all numeric values from a text string."""
    # Match integers and decimals, including negative and percentage
    matches = re.findall(r'-?\d+\.?\d*', str(text))
    return [float(m) for m in matches]

def _number_exists_in_data(number: float, data_dict: dict, tolerance: float = 0.05) -> bool:
    """Check if a number exists in a data dict within ±tolerance (5% by default)."""
    for key, value in data_dict.items():
        if isinstance(value, (int, float)):
            if value == 0:
                if abs(number) < 0.01:
                    return True
            elif abs(number - value) / abs(value) <= tolerance:
                return True
    return False

def _check_thesis_hallucination(thesis_text: str, fund: dict, tech: dict) -> list:
    """
    Extract numbers from thesis and verify each exists in fundamentals or technicals.
    Returns list of unverified numbers.
    """
    numbers = _extract_numbers(thesis_text)
    unverified = []

    for num in numbers:
        # Skip trivially common numbers (1-10 for confidence, small integers)
        if num in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            continue
        if _number_exists_in_data(num, fund) or _number_exists_in_data(num, tech):
            continue
        unverified.append(num)

    return unverified

def run_validator(state: dict) -> dict:
    """
    Validator v2: Deterministic checks + hallucination detection.
    Phase 2 checks:
      - SL >= entry (invalid stop loss)
      - Single trade risk > 2% of capital
      - Cumulative portfolio risk > 2% of capital
    Phase 3 checks:
      - Numbers in thesis must exist in fundamentals/technicals (±5% tolerance)
      - If hallucination detected, flag for thesis retry
    """
    trades = state.get('trades', [])
    thesis = state.get('thesis', {})
    fundamentals = state.get('fundamentals', {})
    technicals = state.get('technicals', {})

    max_single_risk = CAPITAL * MAX_RISK_PER_TRADE           # ₹20,000 per trade
    max_portfolio_risk = CAPITAL * MAX_PORTFOLIO_RISK_PER_DAY  # ₹60,000 total daily
    valid_trades = []
    cumulative_risk = 0
    needs_thesis_retry = False

    for trade in trades:
        ticker = trade['ticker']

        # --- Phase 2 checks ---
        # Check 1: SL must be below entry
        if trade['sl'] >= trade['entry']:
            print(f"REJECTED {ticker}: SL ({trade['sl']}) >= entry ({trade['entry']})")
            continue

        # Check 2: Single trade risk must not exceed 2% of capital
        trade_risk = trade['qty'] * trade['risk_per_share']
        if trade_risk > max_single_risk:
            print(f"REJECTED {ticker}: trade risk (₹{trade_risk:.0f}) > per-trade cap (₹{max_single_risk:.0f})")
            continue

        # Check 3: Cumulative portfolio risk must not exceed 6% of capital per day
        if cumulative_risk + trade_risk > max_portfolio_risk:
            print(f"REJECTED {ticker}: cumulative risk (₹{cumulative_risk + trade_risk:.0f}) would exceed daily cap (₹{max_portfolio_risk:.0f})")
            continue

        # --- Phase 3: Hallucination check ---
        ticker_thesis = thesis.get(ticker, {})
        thesis_text   = ticker_thesis.get('thesis', '')
        catalyst      = trade.get('catalyst', ticker_thesis.get('catalyst', 'none'))
        confidence    = trade.get('confidence', ticker_thesis.get('confidence', 5))
        fund = fundamentals.get(ticker, {})
        tech = technicals.get(ticker, {})

        # Gate: no catalyst + low confidence = speculative, reject (unless LLM failed)
        if catalyst == 'none' and confidence <= 5 and thesis_text != 'Error generating thesis':
            print(f"REJECTED {ticker}: no catalyst identified and confidence={confidence}")
            continue

        if thesis_text and thesis_text != 'Error generating thesis':
            unverified = _check_thesis_hallucination(thesis_text, fund, tech)
            if unverified:
                print(f"WARNING {ticker}: Thesis has unverified numbers: {unverified}")
                needs_thesis_retry = True

        cumulative_risk += trade_risk
        valid_trades.append(trade)
        print(f"APPROVED {ticker}: catalyst='{catalyst}' confidence={confidence} risk=₹{trade_risk:.0f}")

    state['trades'] = valid_trades

    if needs_thesis_retry and not valid_trades:
        state['next_agent'] = 'thesis_agent'
    elif valid_trades:
        state['next_agent'] = 'paper_executor'
    else:
        state['next_agent'] = 'end'

    return state

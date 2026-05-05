import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tools.dcf_model import run_dcf
from tools.yfinance_tool import get_nse_data


def calculate_piotroski_f_score(fin: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame) -> int:
    """
    Full 9-signal Piotroski F-Score.
      Profitability: F1=ROA>0, F2=CFO>0, F3=ΔROA>0, F4=Accruals(CFO/TA>ROA)
      Leverage:      F5=ΔLeverage<0, F6=ΔCurrentRatio>0, F7=NoDilution
      Efficiency:    F8=ΔGrossMargin>0, F9=ΔAssetTurnover>0
    Returns 0-9. Unknown data = 0 for that signal (conservative).
    """
    score = 0
    if fin.empty or bs.empty or cf.empty:
        return 4  # below neutral — unknown is not a pass

    has_prior = fin.shape[1] >= 2 and bs.shape[1] >= 2

    def _get(df, label, col=0):
        try:
            return float(df.loc[label].iloc[col]) if label in df.index else None
        except Exception:
            return None

    # --- Profitability ---
    ni = _get(fin, 'Net Income')
    ta = _get(bs, 'Total Assets')
    cfo = _get(cf, 'Operating Cash Flow')
    roa = (ni / ta) if (ni is not None and ta and ta > 0) else None

    if roa is not None and roa > 0:          score += 1  # F1
    if cfo is not None and cfo > 0:          score += 1  # F2

    # F3: ΔROA positive
    if has_prior and roa is not None:
        ni_p, ta_p = _get(fin, 'Net Income', 1), _get(bs, 'Total Assets', 1)
        if ni_p is not None and ta_p and ta_p > 0:
            if roa > (ni_p / ta_p):              score += 1  # F3

    # F4: Accruals — CFO/TA > ROA (cash quality)
    if cfo is not None and ta and ta > 0 and roa is not None:
        if (cfo / ta) > roa:                 score += 1  # F4

    # --- Leverage / Liquidity ---
    # F5: Debt ratio decreasing
    if has_prior:
        debt, ta2 = _get(bs, 'Total Debt'), _get(bs, 'Total Assets')
        debt_p, ta2_p = _get(bs, 'Total Debt', 1), _get(bs, 'Total Assets', 1)
        if all(v is not None and v > 0 for v in [ta2, ta2_p]) and debt is not None and debt_p is not None:
            if (debt / ta2) < (debt_p / ta2_p):  score += 1  # F5

    # F6: Current ratio improving
    if has_prior:
        ca, cl = _get(bs, 'Current Assets'), _get(bs, 'Current Liabilities')
        ca_p, cl_p = _get(bs, 'Current Assets', 1), _get(bs, 'Current Liabilities', 1)
        if all(v is not None and v > 0 for v in [cl, cl_p]) and ca is not None and ca_p is not None:
            if (ca / cl) > (ca_p / cl_p):       score += 1  # F6

    # F7: No dilution (shares not increasing > 2%)
    for lbl in ('Ordinary Shares Number', 'Share Issued', 'Common Stock'):
        if lbl in bs.index and bs.shape[1] >= 2:
            s, s_p = _get(bs, lbl), _get(bs, lbl, 1)
            if s is not None and s_p and s_p > 0:
                if s <= s_p * 1.02:              score += 1  # F7
            break

    # --- Operating Efficiency ---
    # F8: Gross margin improving
    if has_prior:
        gp, rev = _get(fin, 'Gross Profit'), _get(fin, 'Total Revenue')
        gp_p, rev_p = _get(fin, 'Gross Profit', 1), _get(fin, 'Total Revenue', 1)
        if all(v is not None and v > 0 for v in [rev, rev_p]) and gp is not None and gp_p is not None:
            if (gp / rev) > (gp_p / rev_p):     score += 1  # F8

    # F9: Asset turnover improving
    if has_prior:
        rev2, ta3 = _get(fin, 'Total Revenue'), _get(bs, 'Total Assets')
        rev2_p, ta3_p = _get(fin, 'Total Revenue', 1), _get(bs, 'Total Assets', 1)
        if all(v is not None and v > 0 for v in [ta3, ta3_p]) and rev2 is not None and rev2_p is not None:
            if (rev2 / ta3) > (rev2_p / ta3_p): score += 1  # F9

    return score


def _fetch_ticker_fundamentals(ticker: str) -> tuple:
    """Fetch and compute fundamentals for a single ticker. Returns (ticker, dict|None)."""
    try:
        data = get_nse_data(ticker)
        if not data:
            return ticker, None

        info = data.get('info', {})
        fin  = data.get('financials', pd.DataFrame())
        bs   = data.get('balance_sheet', pd.DataFrame())
        cf   = data.get('cashflow', pd.DataFrame())

        def _g(df, lbl, col=0):
            try:
                return float(df.loc[lbl].iloc[col]) if lbl in df.index else None
            except Exception:
                return None

        # DCF
        dcf_value    = run_dcf(fin, cf, info)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0)) or 0
        dcf_upside   = ((dcf_value - current_price) / current_price * 100) if current_price > 0 else 0

        # F-Score (full 9-signal)
        f_score = calculate_piotroski_f_score(fin, bs, cf)

        # FCF Yield
        fcf = _g(cf, 'Free Cash Flow') or 0
        if not fcf:
            cfo = _g(cf, 'Operating Cash Flow') or 0
            capex = _g(cf, 'Capital Expenditure') or 0
            fcf = cfo + capex
        mktcap = info.get('marketCap', 1) or 1
        fcf_yield = (fcf / mktcap) * 100

        # ROCE
        roce = 0
        ebit = _g(fin, 'EBIT')
        ta   = _g(bs, 'Total Assets')
        cl   = _g(bs, 'Current Liabilities')
        if ebit is not None and ta and cl is not None and (ta - cl) > 0:
            roce = (ebit / (ta - cl)) * 100

        # D/E
        de_ratio = 999.0
        debt = _g(bs, 'Total Debt') or _g(bs, 'Long Term Debt') or 0
        equity = 0
        for lbl in ('Total Stockholder Equity', 'Stockholders Equity', 'Total Equity Gross Minority Interest'):
            v = _g(bs, lbl)
            if v is not None:
                equity = v
                break
        if equity > 0:
            de_ratio = debt / equity

        # Revenue Growth YoY
        rev_growth = 0
        if 'Total Revenue' in fin.index and fin.shape[1] >= 2:
            r0 = _g(fin, 'Total Revenue', 0)
            r1 = _g(fin, 'Total Revenue', 1)
            if r0 and r1 and r1 > 0:
                rev_growth = ((r0 - r1) / r1) * 100

        return ticker, {
            'DCF_Upside_%':    round(dcf_upside, 1),
            'F_Score':         f_score,
            'FCF_Yield_%':     round(fcf_yield, 2),
            'ROCE_%':          round(roce, 1),
            'DE_Ratio':        round(de_ratio, 3),
            'Revenue_Growth_%': round(rev_growth, 1),
            'current_price':   current_price,
        }

    except Exception as e:
        print(f"  [fund] {ticker}: {e}")
        return ticker, None


def run_fundamental_scout(state: dict) -> dict:
    """Fetches fundamentals for all universe tickers in parallel (10 workers)."""
    universe = state.get('universe', [])
    fundamentals = {}
    print(f"Fundamental scout: {len(universe)} tickers, 10 parallel workers...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_ticker_fundamentals, t): t for t in universe}
        done = 0
        for future in as_completed(futures):
            ticker, result = future.result()
            if result:
                fundamentals[ticker] = result
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(universe)} done")

    print(f"Fundamental scout complete: {len(fundamentals)} tickers with data.")
    state['fundamentals'] = fundamentals
    return state

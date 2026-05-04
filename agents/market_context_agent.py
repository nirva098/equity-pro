import yfinance as yf
import pandas as pd
from tools.nse_tool import get_fii_dii

def _parse_fii_net(fii_dii_data) -> float:
    """Parse FII net from nsepython output (handles both DataFrame and list)."""
    try:
        if isinstance(fii_dii_data, pd.DataFrame) and not fii_dii_data.empty:
            for _, row in fii_dii_data.iterrows():
                cat = str(row.get('category', '')).upper()
                if 'FII' in cat or 'FPI' in cat:
                    buy_val = float(str(row.get('buyValue', '0')).replace(',', ''))
                    sell_val = float(str(row.get('sellValue', '0')).replace(',', ''))
                    return buy_val - sell_val
        elif isinstance(fii_dii_data, list):
            for entry in fii_dii_data:
                if isinstance(entry, dict) and 'category' in entry:
                    cat = str(entry['category']).upper()
                    if 'FII' in cat or 'FPI' in cat:
                        buy_val = float(str(entry.get('buyValue', '0')).replace(',', ''))
                        sell_val = float(str(entry.get('sellValue', '0')).replace(',', ''))
                        return buy_val - sell_val
    except Exception:
        pass
    return 0

def run_market_context(state: dict) -> dict:
    """
    Deterministic Market Context Agent (Phase 2 - no LLM).
    Fetches NIFTY, India VIX, S&P 500, and FII/DII data.
    Classifies regime as risk_on / risk_off / high_vix using thresholds.
    """
    try:
        # Fetch NIFTY 50
        nifty = yf.Ticker("^NSEI")
        nifty_hist = nifty.history(period="1mo")
        nifty_close = float(nifty_hist['Close'].iloc[-1]) if not nifty_hist.empty else 0
        nifty_5d_return = 0
        if len(nifty_hist) >= 6:
            nifty_5d_return = ((nifty_hist['Close'].iloc[-1] - nifty_hist['Close'].iloc[-6]) / nifty_hist['Close'].iloc[-6]) * 100

        # Fetch India VIX
        vix_ticker = yf.Ticker("^INDIAVIX")
        vix_hist = vix_ticker.history(period="5d")
        vix = float(vix_hist['Close'].iloc[-1]) if not vix_hist.empty else 15.0

        # Fetch US S&P 500 futures proxy
        sp500 = yf.Ticker("^GSPC")
        sp500_hist = sp500.history(period="5d")
        us_change = 0
        if len(sp500_hist) >= 2:
            us_change = ((sp500_hist['Close'].iloc[-1] - sp500_hist['Close'].iloc[-2]) / sp500_hist['Close'].iloc[-2]) * 100

        # Fetch FII/DII
        fii_dii_data = get_fii_dii()
        fii_net = _parse_fii_net(fii_dii_data)

        # Deterministic regime classification
        if vix > 20:
            regime = "high_vix"
        elif nifty_5d_return < -2 or fii_net < -2000:
            regime = "risk_off"
        else:
            regime = "risk_on"

        state['market_context'] = {
            'regime': regime,
            'nifty_close': nifty_close,
            'vix': vix,
            'fii_net': fii_net,
            'us_futures_change': us_change,
            'nifty_5d_return': nifty_5d_return
        }

    except Exception as e:
        print(f"Error in market_context_agent: {e}")
        state['market_context'] = {
            'regime': 'risk_on',
            'nifty_close': 0,
            'vix': 15.0,
            'fii_net': 0,
            'us_futures_change': 0,
            'nifty_5d_return': 0
        }

    return state

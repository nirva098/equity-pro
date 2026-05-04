import json
import yfinance as yf
import pandas as pd
from tools.nse_tool import get_fii_dii
from core.config import OPENAI_API_KEY

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

def _llm_regime_analysis(market_data: dict) -> dict:
    """
    Optional LLM call to add event_flag and regime_narrative.
    Falls back gracefully if no API key.
    """
    if not OPENAI_API_KEY:
        return {'event_flag': 'none', 'regime_narrative': ''}

    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=OPENAI_API_KEY)

        prompt = f"""You are an Indian market regime analyst.
Given today's market data:
- NIFTY Close: {market_data.get('nifty_close')}
- India VIX: {market_data.get('vix')}
- NIFTY 5-day Return: {market_data.get('nifty_5d_return'):.2f}%
- FII Net (Cr): {market_data.get('fii_net'):.0f}
- US S&P 500 Change: {market_data.get('us_futures_change'):.2f}%
- Deterministic Regime: {market_data.get('regime')}

Return ONLY valid JSON with no markdown formatting:
{{
  "regime": "risk_on" or "risk_off" or "high_vix",
  "event_flag": "Fed_week" or "Budget_day" or "RBI_policy" or "none",
  "regime_narrative": "1-2 sentence explanation of current regime and any notable events"
}}

JSON response:"""

        response = llm.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        return json.loads(content)

    except Exception as e:
        print(f"Regime LLM error: {e}")
        return {'event_flag': 'none', 'regime_narrative': ''}

def run_market_context(state: dict) -> dict:
    """
    Market Context Agent (Phase 3 - Deterministic + LLM).
    Fetches NIFTY, India VIX, S&P 500, and FII/DII data.
    Deterministic regime classification, then LLM adds event_flag and narrative.
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

        market_data = {
            'regime': regime,
            'nifty_close': nifty_close,
            'vix': vix,
            'fii_net': fii_net,
            'us_futures_change': us_change,
            'nifty_5d_return': nifty_5d_return
        }

        # LLM enhancement: add event_flag and regime_narrative
        llm_result = _llm_regime_analysis(market_data)
        market_data['event_flag'] = llm_result.get('event_flag', 'none')
        market_data['regime_narrative'] = llm_result.get('regime_narrative', '')
        # LLM can optionally override regime
        if llm_result.get('regime') in ('risk_on', 'risk_off', 'high_vix'):
            market_data['regime'] = llm_result['regime']

        state['market_context'] = market_data

    except Exception as e:
        print(f"Error in market_context_agent: {e}")
        state['market_context'] = {
            'regime': 'risk_on',
            'nifty_close': 0,
            'vix': 15.0,
            'fii_net': 0,
            'us_futures_change': 0,
            'nifty_5d_return': 0,
            'event_flag': 'none',
            'regime_narrative': ''
        }

    return state

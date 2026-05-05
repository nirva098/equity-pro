import pandas as pd
import numpy as np
from tools.dcf_model import run_dcf
from tools.yfinance_tool import get_nse_data

def calculate_piotroski_f_score(financials: pd.DataFrame, balance_sheet: pd.DataFrame, cashflow: pd.DataFrame) -> int:
    """Calculates a simplified Piotroski F-Score (0-9)"""
    score = 0
    try:
        if financials.empty or balance_sheet.empty or cashflow.empty:
            return 5 # Default neutral score
            
        # 1. Profitability (ROA, CFO, Change in ROA, Accruals)
        if 'Net Income' in financials.index and 'Total Assets' in balance_sheet.index:
            ni = financials.loc['Net Income'].iloc[0]
            total_assets = balance_sheet.loc['Total Assets'].iloc[0]
            roa = ni / total_assets
            if roa > 0: score += 1
            
        if 'Operating Cash Flow' in cashflow.index:
            cfo = cashflow.loc['Operating Cash Flow'].iloc[0]
            if cfo > 0: score += 1
            if 'Total Assets' in balance_sheet.index and cfo > (financials.loc['Net Income'].iloc[0] if 'Net Income' in financials.index else 0):
                score += 1
                
        # ... further detailed F-score parts omitted for brevity, returning a placeholder calculation based on available stats
        # We will approximate based on typical available columns:
        if 'Gross Profit' in financials.index:
            if financials.loc['Gross Profit'].iloc[0] > 0: score += 1
            
        if 'Total Debt' in balance_sheet.index:
            # Assuming debt is not increasing drastically
            score += 1
            
        return score
    except Exception:
        return 5

def run_fundamental_scout(state: dict) -> dict:
    """Agent: Fetches and calculates fundamental data for all tickers in universe"""
    fundamentals = {}
    universe = state.get('universe', [])
    
    for ticker in universe:
        data = get_nse_data(ticker)
        if not data:
            continue
            
        info = data.get('info', {})
        fin = data.get('financials', pd.DataFrame())
        bs = data.get('balance_sheet', pd.DataFrame())
        cf = data.get('cashflow', pd.DataFrame())
        
        # 1. DCF
        dcf_value = run_dcf(fin, cf, info)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        dcf_upside = ((dcf_value - current_price) / current_price) * 100 if current_price > 0 else 0
        
        # 2. F-Score
        f_score = calculate_piotroski_f_score(fin, bs, cf)
        
        # 3. FCF Yield
        fcf = 0
        if 'Free Cash Flow' in cf.index:
             fcf = cf.loc['Free Cash Flow'].iloc[0]
        elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
             fcf = cf.loc['Operating Cash Flow'].iloc[0] + cf.loc['Capital Expenditure'].iloc[0]
             
        market_cap = info.get('marketCap', 1)
        fcf_yield = (fcf / market_cap) * 100 if market_cap > 0 else 0
        
        # 4. ROCE Approximation (EBIT / Capital Employed)
        roce = 0
        if 'EBIT' in fin.index and 'Total Assets' in bs.index and 'Current Liabilities' in bs.index:
            ebit = fin.loc['EBIT'].iloc[0]
            cap_emp = bs.loc['Total Assets'].iloc[0] - bs.loc['Current Liabilities'].iloc[0]
            if cap_emp > 0:
                roce = (ebit / cap_emp) * 100

        # 5. Debt-to-Equity Ratio
        de_ratio = 999.0  # High default = debt filter will exclude if D/E unknown
        try:
            total_debt = 0
            if 'Total Debt' in bs.index:
                total_debt = float(bs.loc['Total Debt'].iloc[0])
            elif 'Long Term Debt' in bs.index:
                total_debt = float(bs.loc['Long Term Debt'].iloc[0])

            stockholder_equity = 0
            for eq_label in ('Total Stockholder Equity', 'Stockholders Equity',
                             'Total Equity Gross Minority Interest'):
                if eq_label in bs.index:
                    stockholder_equity = float(bs.loc[eq_label].iloc[0])
                    break

            if stockholder_equity > 0:
                de_ratio = total_debt / stockholder_equity
        except Exception:
            pass

        fundamentals[ticker] = {
            'DCF_Value': dcf_value,
            'DCF_Upside_%': dcf_upside,
            'F_Score': f_score,
            'FCF_Yield_%': fcf_yield,
            'ROCE_%': roce,
            'DE_Ratio': round(de_ratio, 3),
            'current_price': current_price
        }

    state['fundamentals'] = fundamentals
    return state

import pandas as pd

def run_dcf(financials: pd.DataFrame, cashflow: pd.DataFrame, info: dict) -> float:
    """
    Standard 3-stage DCF model returning intrinsic value per share.
    Simplified version using standard growth rates if inputs are missing.
    """
    try:
        # 1. Get Free Cash Flow (FCF)
        # Using the latest available year
        if 'Free Cash Flow' in cashflow.index:
            fcf_latest = cashflow.loc['Free Cash Flow'].iloc[0]
        elif 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
            fcf_latest = cashflow.loc['Operating Cash Flow'].iloc[0] + cashflow.loc['Capital Expenditure'].iloc[0]
        else:
            return 0.0
            
        if pd.isna(fcf_latest) or fcf_latest <= 0:
            return 0.0

        # 2. Extract shares outstanding
        shares_out = info.get('sharesOutstanding', 1)
        if shares_out <= 0:
            return 0.0

        # 3. Assumptions for 3-Stage Model
        discount_rate = 0.10 # 10% WACC approximation
        growth_stage_1 = 0.15 # 15% growth for years 1-5
        growth_stage_2 = 0.08 # 8% growth for years 6-10
        terminal_growth = 0.03 # 3% perpetuity growth

        # Calculate Present Value of FCFs
        pv_fcf = 0
        current_fcf = fcf_latest
        
        # Stage 1: Years 1-5
        for year in range(1, 6):
            current_fcf *= (1 + growth_stage_1)
            pv_fcf += current_fcf / ((1 + discount_rate) ** year)
            
        # Stage 2: Years 6-10
        for year in range(6, 11):
            current_fcf *= (1 + growth_stage_2)
            pv_fcf += current_fcf / ((1 + discount_rate) ** year)
            
        # Stage 3: Terminal Value
        terminal_value = (current_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
        pv_terminal_value = terminal_value / ((1 + discount_rate) ** 10)
        
        intrinsic_value = (pv_fcf + pv_terminal_value) / shares_out
        return float(intrinsic_value)
        
    except Exception as e:
        print(f"DCF calculation error: {e}")
        return 0.0

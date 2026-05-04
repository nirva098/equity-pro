import pandas as pd
from typing import Dict, Any
from core.market_db import get_prices, get_fundamentals

def get_nse_data(ticker: str) -> Dict[str, Any]:
    """Fetches comprehensive NSE data exclusively from the local SQLite cache."""
    try:
        # Fetch prices from DB
        hist = get_prices(ticker)
        
        if hist.empty:
            return {}
            
        # Fetch fundamentals from DB
        fund = get_fundamentals(ticker)
        if not fund:
            return {}
            
        data = {
            'ticker': ticker,
            'info': fund['info'],
            'historical': hist,
            'financials': fund['financials'],
            'balance_sheet': fund['balance_sheet'],
            'cashflow': fund['cashflow']
        }
        return data
    except Exception as e:
        print(f"Error fetching cached data for {ticker}: {e}")
        return {}

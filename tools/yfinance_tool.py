import yfinance as yf
import pandas as pd
from typing import Dict, Any

def get_nse_data(ticker: str) -> Dict[str, Any]:
    """Fetches comprehensive NSE data using yfinance"""
    try:
        t = yf.Ticker(ticker)
        
        # Get historical data (1 year for 200DMA calculations)
        hist = t.history(period="1y")
        
        if hist.empty:
            return {}
            
        data = {
            'ticker': ticker,
            'info': t.info,
            'historical': hist,
            'financials': t.financials,
            'balance_sheet': t.balance_sheet,
            'cashflow': t.cashflow
        }
        return data
    except Exception as e:
        print(f"Error fetching yfinance data for {ticker}: {e}")
        return {}

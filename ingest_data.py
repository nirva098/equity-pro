import os
import csv
import yfinance as yf
from datetime import datetime
from core.market_db import init_market_db, get_max_date, upsert_prices, upsert_fundamentals, get_fundamentals

def run_ingestion():
    print("Initializing market database...")
    init_market_db()
    
    csv_path = "data/universe_nse500.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    tickers = []
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        next(reader) # skip header
        for row in reader:
            if row:
                tickers.append(row[0])
                
    print(f"Starting daily ingestion for {len(tickers)} tickers...")
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Fetching data for {ticker}...")
        try:
            t = yf.Ticker(ticker)
            
            # 1. Handle Daily Prices (Delta Fetch)
            max_date = get_max_date(ticker)
            if not max_date:
                # New ticker, fetch 1 year
                hist = t.history(period="1y")
            else:
                # Existing ticker, fetch last 5 days to ensure we get any recent gaps
                hist = t.history(period="5d")
                
            if not hist.empty:
                upsert_prices(ticker, hist)
                
            # 2. Handle Fundamentals (Cached for 14 days)
            fund = get_fundamentals(ticker)
            needs_update = True
            
            if fund and fund.get('last_updated'):
                last_upd = datetime.strptime(fund['last_updated'], '%Y-%m-%d')
                days_old = (datetime.now() - last_upd).days
                if days_old < 14:
                    needs_update = False
                    
            if needs_update:
                upsert_fundamentals(ticker, t.info, t.financials, t.balance_sheet, t.cashflow)
                
        except Exception as e:
            print(f"  -> Error fetching {ticker}: {e}")
            
    print("Ingestion complete!")

if __name__ == "__main__":
    run_ingestion()

import os
import csv
try:
    from nsepython import nse_get_index_list
except ImportError:
    print("nsepython not installed or fnolist not available")

def get_nifty500_tickers():
    try:
        # Some nsepython versions might have different functions. 
        # But 'fnolist' returns all F&O stocks which is ~200 highly liquid stocks.
        from nsepython import fnolist
        symbols = fnolist()
        # Ensure it's a list of strings
        symbols = [str(s).strip() for s in symbols if s]
        return symbols
    except Exception as e:
        print(f"Error fetching from nsepython: {e}")
        # Fallback to a hardcoded list of highly liquid Nifty 50 stocks
        return [
            "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "INFY", "ITC", 
            "SBI", "L&T", "BAJFINANCE", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "LT",
            "M&M", "SUNPHARMA", "MARUTI", "TATASTEEL", "NTPC", "TATAMOTORS", "ULTRACEMCO",
            "POWERGRID", "TITAN", "COALINDIA", "BAJAJFINSV", "ASIANPAINT", "ONGC", "ADANIPORTS"
        ]

if __name__ == "__main__":
    symbols = get_nifty500_tickers()
    if not symbols:
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
    
    # Filter out common index symbols if they were fetched by mistake
    indices = {"NIFTY", "BANKNIFTY", "NIFTYIT"}
    symbols = [s for s in symbols if s not in indices]
    
    # Take top 250
    symbols = symbols[:250]
    
    csv_path = "data/universe_nse500.csv"
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Ticker"])
        for sym in symbols:
            # Handle standard Yahoo symbols
            clean_sym = sym.replace("L&T", "LT").replace("M&M", "M&M")
            writer.writerow([f"{clean_sym}.NS"])
            
    print(f"Successfully wrote {len(symbols)} tickers to {csv_path}")

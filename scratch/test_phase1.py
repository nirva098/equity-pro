import json
import pandas as pd
from agents.data_scout_fundamental import run_fundamental_scout
from agents.data_scout_technical import run_technical_scout
from tools.nse_tool import get_fii_dii, is_trading_day

def main():
    print("Testing NSE Tool...")
    fii = get_fii_dii()
    print(f"FII/DII Data fetched: {len(fii) > 0}")
    print(f"Is trading day: {is_trading_day()}")
    
    print("\nReading Universe CSV...")
    try:
        universe_df = pd.read_csv('data/universe_nse500.csv')
        tickers = universe_df['Ticker'].tolist()
        print(f"Loaded {len(tickers)} tickers: {tickers}")
    except Exception as e:
        print(f"Failed to read universe: {e}")
        return

    state = {
        'universe': tickers,
        'fundamentals': {},
        'technicals': {}
    }
    
    print("\nRunning Fundamental Scout...")
    state = run_fundamental_scout(state)
    
    print("\nRunning Technical Scout...")
    state = run_technical_scout(state)
    
    print("\nWriting output to scratch/phase1_output.json...")
    output = {
        'fundamentals': state.get('fundamentals', {}),
        'technicals': state.get('technicals', {})
    }
    
    with open('scratch/phase1_output.json', 'w') as f:
        json.dump(output, f, indent=4)
        
    print("Test Complete. Check scratch/phase1_output.json")

if __name__ == "__main__":
    main()

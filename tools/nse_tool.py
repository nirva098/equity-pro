import nsepython
from datetime import datetime

def get_fii_dii() -> dict:
    """Fetches FII DII data from NSE"""
    try:
        data = nsepython.nse_fiidii()
        return data
    except Exception as e:
        print(f"Error fetching FII/DII data: {e}")
        return {}

def is_trading_day() -> bool:
    """Checks if today is a trading holiday"""
    try:
        holidays = nsepython.nse_holidays()
        today_str = datetime.now().strftime("%d-%b-%Y")
        
        if 'CBM' in holidays:
            for holiday in holidays['CBM']:
                if holiday.get('tradingDate') == today_str:
                    return False
        
        # Also check weekends
        if datetime.now().weekday() >= 5: # 5 is Saturday, 6 is Sunday
            return False
            
        return True
    except Exception as e:
        print(f"Error checking trading day: {e}")
        # Default to checking if it's a weekday if API fails
        return datetime.now().weekday() < 5

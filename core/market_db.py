import sqlite3
import pandas as pd
import json
from datetime import datetime
from io import StringIO

MARKET_DB_PATH = "data/market_data.db"

def init_market_db():
    import os
    os.makedirs(os.path.dirname(MARKET_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(MARKET_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT PRIMARY KEY,
            last_updated TEXT,
            info_json TEXT,
            financials_json TEXT,
            balance_sheet_json TEXT,
            cashflow_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_max_date(ticker: str) -> str:
    """Returns the most recent date we have price data for a ticker."""
    conn = sqlite3.connect(MARKET_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM daily_prices WHERE ticker=?", (ticker,))
    res = c.fetchone()
    conn.close()
    return res[0] if res and res[0] else None

def upsert_prices(ticker: str, df: pd.DataFrame):
    """Inserts or updates daily price data from a yfinance dataframe."""
    if df.empty:
        return
    conn = sqlite3.connect(MARKET_DB_PATH)
    c = conn.cursor()
    for index, row in df.iterrows():
        date_str = str(index).split(" ")[0]
        c.execute('''
            INSERT INTO daily_prices (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
            open=excluded.open, high=excluded.high, low=excluded.low, 
            close=excluded.close, volume=excluded.volume
        ''', (ticker, date_str, row['Open'], row['High'], row['Low'], row['Close'], row['Volume']))
    conn.commit()
    conn.close()

def upsert_fundamentals(ticker: str, info: dict, fin: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame):
    """Inserts or updates fundamental data JSONs."""
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(MARKET_DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO fundamentals (ticker, last_updated, info_json, financials_json, balance_sheet_json, cashflow_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
        last_updated=excluded.last_updated,
        info_json=excluded.info_json,
        financials_json=excluded.financials_json,
        balance_sheet_json=excluded.balance_sheet_json,
        cashflow_json=excluded.cashflow_json
    ''', (
        ticker, today, 
        json.dumps(info), 
        fin.to_json(orient='split'), 
        bs.to_json(orient='split'), 
        cf.to_json(orient='split')
    ))
    conn.commit()
    conn.close()

def get_fundamentals(ticker: str) -> dict:
    """Retrieves fundamentals, returns tuple of (info, financials_df, balance_sheet_df, cashflow_df). Returns None if empty."""
    conn = sqlite3.connect(MARKET_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT last_updated, info_json, financials_json, balance_sheet_json, cashflow_json FROM fundamentals WHERE ticker=?", (ticker,))
    res = c.fetchone()
    conn.close()
    
    if not res:
        return None
        
    last_updated, info_str, fin_str, bs_str, cf_str = res
    info = json.loads(info_str) if info_str else {}
    try:
        fin_df = pd.read_json(StringIO(fin_str), orient='split') if fin_str else pd.DataFrame()
        bs_df = pd.read_json(StringIO(bs_str), orient='split') if bs_str else pd.DataFrame()
        cf_df = pd.read_json(StringIO(cf_str), orient='split') if cf_str else pd.DataFrame()
    except Exception:
        return None
        
    return {
        'last_updated': last_updated,
        'info': info,
        'financials': fin_df,
        'balance_sheet': bs_df,
        'cashflow': cf_df
    }

def get_prices(ticker: str) -> pd.DataFrame:
    """Retrieves price history as a DataFrame matching yfinance format."""
    conn = sqlite3.connect(MARKET_DB_PATH)
    df = pd.read_sql_query("SELECT date as Date, open as Open, high as High, low as Low, close as Close, volume as Volume FROM daily_prices WHERE ticker=? ORDER BY date ASC", conn, params=(ticker,))
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
        
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df

import pandas as pd
import numpy as np

def calc_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Calculates the Average True Range (ATR)"""
    if len(df) < period + 1:
        return 0.0
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    atr = true_range.rolling(period).mean()
    return float(atr.iloc[-1])

def calc_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """Calculates the Relative Strength Index (RSI)"""
    if len(df) < period + 1:
        return 0.0
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])

def calc_adx(df: pd.DataFrame, period: int = 14) -> float:
    """Calculates the Average Directional Index (ADX)"""
    if len(df) < period + 1:
        return 0.0
        
    plus_dm = df['High'].diff()
    minus_dm = df['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    atr = pd.Series(tr).rolling(period).mean()
    
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).rolling(period).mean() / atr)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.rolling(period).mean()
    return float(adx.iloc[-1])

def calc_dma(df: pd.DataFrame, periods: list = [20, 50, 200]) -> dict:
    """Calculates multiple Daily Moving Averages (DMA)"""
    dmas = {}
    for p in periods:
        if len(df) >= p:
            dmas[f'DMA{p}'] = float(df['Close'].rolling(window=p).mean().iloc[-1])
        else:
            dmas[f'DMA{p}'] = 0.0
    return dmas

def find_pivots(df: pd.DataFrame) -> dict:
    """Calculates standard floor pivots for Support and Resistance using previous day's data"""
    if len(df) < 2:
        return {'PP': 0, 'R1': 0, 'S1': 0}
        
    prev_high = df['High'].iloc[-2]
    prev_low = df['Low'].iloc[-2]
    prev_close = df['Close'].iloc[-2]
    
    pp = (prev_high + prev_low + prev_close) / 3
    r1 = (2 * pp) - prev_low
    s1 = (2 * pp) - prev_high
    
    return {'PP': float(pp), 'R1': float(r1), 'S1': float(s1)}

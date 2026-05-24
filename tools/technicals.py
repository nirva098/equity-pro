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

def calc_vwap(df: pd.DataFrame) -> float:
    """
    Calculates VWAP using the full history as a long-term anchor.
    Uses typical price (H+L+C)/3 weighted by volume.
    """
    if df.empty or 'Volume' not in df.columns:
        return 0.0
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical * df['Volume']).sum() / df['Volume'].sum()
    return round(float(vwap), 2) if not pd.isna(vwap) else 0.0


def find_swing_levels(df: pd.DataFrame, n: int = 5, lookback: int = 90) -> dict:
    """
    Identifies swing highs (resistance) and swing lows (support) from recent price history.

    A swing high = a candle whose High is the local maximum among the N candles on each side.
    A swing low  = a candle whose Low is the local minimum among the N candles on each side.

    Returns the two nearest swing highs above current price and the nearest swing low
    below current price — anchored to real market structure, not ATR multiples.

    Args:
        df:       OHLCV DataFrame, most-recent candle last.
        n:        Wing length for pivot detection (5 = robust for daily swing trading).
        lookback: How many recent candles to scan (90 ≈ 4.5 months of daily data).

    Returns:
        dict: Swing_High_1, Swing_High_2, Swing_Low_1 (floats; 0.0 if not found)
    """
    if len(df) < 2 * n + 1:
        return {'Swing_High_1': 0.0, 'Swing_High_2': 0.0, 'Swing_Low_1': 0.0}

    recent = df.tail(lookback).reset_index(drop=True)
    close = float(recent['Close'].iloc[-1])

    swing_highs: list[float] = []
    swing_lows: list[float] = []

    for i in range(n, len(recent) - n):
        hi = float(recent['High'].iloc[i])
        lo = float(recent['Low'].iloc[i])

        # Swing high: this bar's high is the maximum in the [i-n, i+n] window
        if hi == recent['High'].iloc[i - n: i + n + 1].max():
            swing_highs.append(round(hi, 2))

        # Swing low: this bar's low is the minimum in the [i-n, i+n] window
        if lo == recent['Low'].iloc[i - n: i + n + 1].min():
            swing_lows.append(round(lo, 2))

    # Resistance levels: swing highs strictly above current close (>0.2% gap), ascending
    resistances = sorted(set(h for h in swing_highs if h > close * 1.002))
    # Support levels: swing lows strictly below current close (<0.2% gap), descending
    supports = sorted(set(l for l in swing_lows if l < close * 0.998), reverse=True)

    return {
        'Swing_High_1': resistances[0] if len(resistances) > 0 else 0.0,
        'Swing_High_2': resistances[1] if len(resistances) > 1 else 0.0,
        'Swing_Low_1':  supports[0]    if len(supports) > 0    else 0.0,
    }

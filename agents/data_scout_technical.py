import pandas as pd
from tools.yfinance_tool import get_nse_data
from tools.technicals import calc_atr, calc_rsi, calc_adx, calc_dma, find_pivots

def run_technical_scout(state: dict) -> dict:
    """Agent: Calculates technical indicators for the universe"""
    technicals = {}
    universe = state.get('universe', [])
    
    for ticker in universe:
        data = get_nse_data(ticker)
        if not data or data.get('historical').empty:
            continue
            
        hist = data['historical']
        
        atr = calc_atr(hist)
        rsi = calc_rsi(hist)
        adx = calc_adx(hist)
        dmas = calc_dma(hist)
        pivots = find_pivots(hist)
        
        current_close = hist['Close'].iloc[-1]
        current_vol = hist['Volume'].iloc[-1]
        avg_vol = hist['Volume'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else 1
        
        # Breakout Flag: close > resistance AND vol > 1.5 * avg_vol
        breakout = bool(current_close > pivots['R1'] and current_vol > (1.5 * avg_vol))
        
        # 3M return approximation (63 trading days)
        ret_3m = 0
        if len(hist) > 63:
            ret_3m = ((current_close - hist['Close'].iloc[-63]) / hist['Close'].iloc[-63]) * 100
        
        # 52w high distance
        high_52w = hist['High'].max()
        dist_52w_high = ((high_52w - current_close) / high_52w) * 100 if high_52w > 0 else 0
        
        technicals[ticker] = {
            'ATR14': atr,
            'RSI14': rsi,
            'ADX14': adx,
            'DMA20': dmas.get('DMA20', 0),
            'DMA50': dmas.get('DMA50', 0),
            'DMA200': dmas.get('DMA200', 0),
            'Pivot_R1': pivots['R1'],
            'Pivot_S1': pivots['S1'],
            'Breakout': breakout,
            '3M_Return_%': ret_3m,
            'Distance_to_52w_High_%': dist_52w_high,
            'close': current_close
        }
        
    state['technicals'] = technicals
    return state

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tools.yfinance_tool import get_nse_data
from tools.technicals import calc_atr, calc_rsi, calc_adx, calc_dma, find_pivots


def _fetch_ticker_technicals(ticker: str) -> tuple:
    """Fetch and compute technicals for a single ticker. Returns (ticker, dict|None)."""
    try:
        data = get_nse_data(ticker)
        if not data or data.get('historical') is None:
            return ticker, None
        hist = data['historical']
        if hist.empty or len(hist) < 20:
            return ticker, None

        atr   = calc_atr(hist)
        rsi   = calc_rsi(hist)
        adx   = calc_adx(hist)
        dmas  = calc_dma(hist)
        pivots = find_pivots(hist)

        close   = float(hist['Close'].iloc[-1])
        vol     = float(hist['Volume'].iloc[-1])
        avg_vol = float(hist['Volume'].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else 1

        # Breakout: close > R1 AND vol > 1.5× avg
        breakout = bool(close > pivots['R1'] and vol > 1.5 * avg_vol)

        # 3M return (≈63 trading days)
        ret_3m = 0.0
        if len(hist) > 63:
            ret_3m = ((close - float(hist['Close'].iloc[-63])) / float(hist['Close'].iloc[-63])) * 100

        # 52w high distance
        high_52w = float(hist['High'].max())
        dist_52w = ((high_52w - close) / high_52w) * 100 if high_52w > 0 else 0

        # MACD (12/26/9) — for momentum confirmation
        ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
        ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_bullish = bool(macd_line.iloc[-1] > signal_line.iloc[-1] and
                            macd_line.iloc[-2] <= signal_line.iloc[-2])  # fresh crossover

        # Volume ratio (today vs 20-day avg)
        vol_ratio = round(vol / avg_vol, 2) if avg_vol > 0 else 1.0

        return ticker, {
            'ATR14':                  round(atr, 2),
            'RSI14':                  round(rsi, 1),
            'ADX14':                  round(adx, 1),
            'DMA20':                  round(dmas.get('DMA20', 0), 2),
            'DMA50':                  round(dmas.get('DMA50', 0), 2),
            'DMA200':                 round(dmas.get('DMA200', 0), 2),
            'Pivot_R1':               round(pivots['R1'], 2),
            'Pivot_S1':               round(pivots['S1'], 2),
            'Breakout':               breakout,
            'MACD_Bullish_Cross':     macd_bullish,
            '3M_Return_%':            round(ret_3m, 1),
            'Distance_to_52w_High_%': round(dist_52w, 1),
            'Volume_Ratio':           vol_ratio,
            'close':                  round(close, 2),
        }

    except Exception as e:
        print(f"  [tech] {ticker}: {e}")
        return ticker, None


def run_technical_scout(state: dict) -> dict:
    """Fetches technicals for all universe tickers in parallel (10 workers)."""
    universe = state.get('universe', [])
    technicals = {}
    print(f"Technical scout: {len(universe)} tickers, 10 parallel workers...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_ticker_technicals, t): t for t in universe}
        done = 0
        for future in as_completed(futures):
            ticker, result = future.result()
            if result:
                technicals[ticker] = result
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(universe)} done")

    print(f"Technical scout complete: {len(technicals)} tickers with data.")
    state['technicals'] = technicals
    return state

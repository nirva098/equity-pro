import json

def run_thesis_agent(state: dict) -> dict:
    """
    Deterministic Agent: Generates a concise research note for each sized trade.
    Assembles fields from earlier agents without invoking an LLM.
    """
    trades         = state.get('trades', [])
    news_sentiment = state.get('news_sentiment', {})
    catalyst_checks = state.get('catalyst_checks', {})
    skeptic_reviews = state.get('skeptic_reviews', {})
    thesis_output  = {}

    for i, trade in enumerate(trades):
        ticker = trade['ticker']
        news   = news_sentiment.get(ticker, {})
        catalyst_check = catalyst_checks.get(ticker, {})
        skeptic = skeptic_reviews.get(ticker, {})
        
        catalyst_type = catalyst_check.get('catalyst_type', 'none')
        catalyst = catalyst_check.get('catalyst', 'none')
        
        # If no real catalyst from checks, try to infer from ranking's why_now or fallback
        if catalyst == 'none' and trade.get('why_now'):
            catalyst = trade.get('why_now')
            catalyst_type = 'quant'

        confidence = trade.get('ai_conviction', 5)
        # Cap confidence if no catalyst
        if catalyst == 'none' and confidence > 4:
            confidence = 4
            print(f"  {ticker}: confidence capped at 4 (no catalyst identified)")
            
        bear_case = skeptic.get('bear_case', '')
        
        thesis_text = f"Catalyst: {catalyst}. Risk: {bear_case}"

        thesis_output[ticker] = {
            'thesis':     thesis_text,
            'catalyst':   catalyst,
            'catalyst_type': catalyst_type,
            'bear_case':  bear_case,
            'confidence': confidence,
        }
        trades[i]['confidence'] = confidence
        trades[i]['catalyst']   = catalyst
        trades[i]['catalyst_type'] = catalyst_type
        trades[i]['bear_case'] = bear_case

        print(f"  {ticker}: catalyst_type='{catalyst_type}' catalyst='{catalyst}' confidence={confidence}")

    state['thesis']  = thesis_output
    state['trades']  = trades
    state['llm_available'] = True
    return state



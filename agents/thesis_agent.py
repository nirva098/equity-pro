import json
from tools.llm_tool import get_llm


def run_thesis_agent(state: dict) -> dict:
    """
    LLM Agent: Generates a 3-line thesis + catalyst + confidence score per trade.
    Catalyst is required. If no clear catalyst exists, confidence is capped at 5.
    Style: Motilal Oswal equity research note. temp=0.3.
    """
    llm = get_llm(temperature=0.3)
    if not llm:
        print("Warning: LLM not configured. Skipping thesis generation.")
        state['thesis'] = {}
        return state

    trades         = state.get('trades', [])
    fundamentals   = state.get('fundamentals', {})
    technicals     = state.get('technicals', {})
    news_sentiment = state.get('news_sentiment', {})
    thesis_output  = {}

    for i, trade in enumerate(trades):
        ticker = trade['ticker']
        fund   = fundamentals.get(ticker, {})
        tech   = technicals.get(ticker, {})
        news   = news_sentiment.get(ticker, {})

        prompt = f"""You are a senior equity research analyst at Motilal Oswal.
Analyze this NSE stock and write a trade thesis with a specific catalyst.

Ticker: {ticker}
Setup: {trade.get('setup', 'unknown')}
News Sentiment: {news.get('sentiment', 'neutral')} | Events: {news.get('events', [])}

Fundamental Data:
{json.dumps(fund, indent=2, default=str)}

Technical Data:
{json.dumps(tech, indent=2, default=str)}

Entry: {trade.get('entry')}, SL: {trade.get('sl')}, Target: {trade.get('target')}

RULES:
1. You MUST identify a specific catalyst for why this trade makes sense TODAY.
   Valid catalysts: earnings beat, contract win, index inclusion, FII/DII block buy,
   technical breakout above resistance, sector tailwind, management guidance upgrade.
2. If NO clear catalyst is identifiable from the data provided, set catalyst to "none".
3. If catalyst is "none", confidence MUST be <= 5.
4. Use ONLY numbers that appear in the data above. Do not invent metrics.

Return ONLY valid JSON, no markdown:
{{
  "thesis": "Line 1: Catalyst - specific event driving move today. Line 2: Valuation - why price is attractive relative to fundamentals. Line 3: Risk - primary downside scenario.",
  "catalyst": "specific catalyst or 'none'",
  "confidence": <integer 1-10, max 5 if catalyst is none>
}}

JSON response:"""

        try:
            response = llm.invoke(prompt)
            content  = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            parsed     = json.loads(content)
            catalyst   = parsed.get('catalyst', 'none')
            confidence = int(parsed.get('confidence', 5))

            # Enforce: no catalyst → cap confidence at 5
            if catalyst == 'none' and confidence > 5:
                confidence = 5
                print(f"  {ticker}: confidence capped at 5 (no catalyst identified)")

            thesis_output[ticker] = {
                'thesis':     parsed.get('thesis', ''),
                'catalyst':   catalyst,
                'confidence': confidence,
            }
            trades[i]['confidence'] = confidence
            trades[i]['catalyst']   = catalyst

            print(f"  {ticker}: catalyst='{catalyst}' confidence={confidence}")

        except Exception as e:
            print(f"  Thesis error for {ticker}: {e}")
            thesis_output[ticker] = {'thesis': 'Error generating thesis', 'catalyst': 'none', 'confidence': 5}
            trades[i]['confidence'] = 5
            trades[i]['catalyst']   = 'none'

    state['thesis']  = thesis_output
    state['trades']  = trades
    return state

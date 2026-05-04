import json
from core.config import OPENAI_API_KEY

def run_thesis_agent(state: dict) -> dict:
    """
    LLM Agent: Generates a 3-line thesis + confidence score per trade.
    Uses gpt-4o-mini at temp=0.3.
    Style: Motilal Oswal equity research note.
    """
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not set. Skipping thesis generation.")
        state['thesis'] = {}
        return state

    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        state['thesis'] = {}
        return state

    trades = state.get('trades', [])
    fundamentals = state.get('fundamentals', {})
    technicals = state.get('technicals', {})
    news_sentiment = state.get('news_sentiment', {})
    thesis_output = {}

    for i, trade in enumerate(trades):
        ticker = trade['ticker']
        fund = fundamentals.get(ticker, {})
        tech = technicals.get(ticker, {})
        news = news_sentiment.get(ticker, {})

        prompt = f"""You are a senior equity research analyst at Motilal Oswal.
Analyze this NSE stock and write a trade thesis.

Ticker: {ticker}
Setup: {trade.get('setup', 'unknown')}

Fundamental Data:
{json.dumps(fund, indent=2, default=str)}

Technical Data:
{json.dumps(tech, indent=2, default=str)}

News Sentiment:
{json.dumps(news, indent=2, default=str)}

Entry: {trade.get('entry')}, SL: {trade.get('sl')}, Target: {trade.get('target')}

Return ONLY valid JSON with no markdown formatting:
{{
  "thesis": "Line 1: Catalyst - why now. Line 2: Valuation - why cheap/fair. Line 3: Risk - what could go wrong.",
  "confidence": <1-10 integer>
}}

Use ONLY numbers that appear in the data above. Do not invent metrics.
JSON response:"""

        try:
            response = llm.invoke(prompt)
            content = response.content.strip()

            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            parsed = json.loads(content)
            thesis_output[ticker] = {
                'thesis': parsed.get('thesis', ''),
                'confidence': int(parsed.get('confidence', 5))
            }

            # Attach confidence to the trade dict
            trades[i]['confidence'] = thesis_output[ticker]['confidence']

        except Exception as e:
            print(f"Thesis error for {ticker}: {e}")
            thesis_output[ticker] = {'thesis': 'Error generating thesis', 'confidence': 5}
            trades[i]['confidence'] = 5

    state['thesis'] = thesis_output
    state['trades'] = trades
    return state

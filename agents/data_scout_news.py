import json
import time
from tools.tavily_search import search_news
from tools.llm_tool import get_llm

def _summarize_news_with_llm(ticker: str, news_results: list) -> dict:
    """Uses LLM to summarize news into sentiment + events."""
    if not news_results:
        return {'sentiment': 'neutral', 'events': []}

    try:
        llm = get_llm(temperature=0.3)
        if not llm:
            return {'sentiment': 'neutral', 'events': []}

        news_text = "\n".join([
            f"- {n['title']}: {n['content'][:200]}" for n in news_results[:5]
        ])

        prompt = f"""Analyze these recent news items for {ticker} (NSE stock).
Return ONLY valid JSON with no markdown formatting:
{{"sentiment": "bullish" or "bearish" or "neutral", "events": ["event1", "event2"]}}

News:
{news_text}

JSON response:"""

        response = llm.invoke(prompt)
        content = response.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        # Respect free tier rate limits (e.g. 15-20 requests per minute)
        time.sleep(3) 

        return json.loads(content)

    except Exception as e:
        print(f"News LLM error for {ticker}: {e}")
        return {'sentiment': 'neutral', 'events': []}

def run_news_scout(state: dict) -> dict:
    """
    Agent: Fetches news for top candidates and summarizes sentiment via LLM.
    Limit to top 10 candidates to prevent API rate limiting.
    """
    candidates = state.get('candidates', [])
    trades = state.get('trades', [])

    # Get tickers from top 10 candidates or trades
    tickers_to_search = set()
    for c in candidates[:10]: # CAP at top 10
        tickers_to_search.add(c['ticker'])
    for t in trades:
        tickers_to_search.add(t['ticker'])

    news_sentiment = {}

    for ticker in tickers_to_search:
        # Clean ticker name for search (remove .NS suffix)
        clean_name = ticker.replace('.NS', '').replace('.BO', '')
        query = f"{clean_name} NSE stock news India"

        news_results = search_news(query, max_results=5)
        sentiment = _summarize_news_with_llm(ticker, news_results)

        news_sentiment[ticker] = {
            'sentiment': sentiment.get('sentiment', 'neutral'),
            'events': sentiment.get('events', []),
            'articles_found': len(news_results)
        }

    state['news_sentiment'] = news_sentiment
    return state

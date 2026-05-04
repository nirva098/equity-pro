from tavily import TavilyClient
from core.config import TAVILY_API_KEY

def search_news(query: str, max_results: int = 5) -> list:
    """
    Searches for recent news using Tavily API.
    Returns list of {title, url, content} dicts.
    Gracefully returns empty list if API key is missing or call fails.
    """
    if not TAVILY_API_KEY:
        print("Warning: TAVILY_API_KEY not set. Skipping news search.")
        return []

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False
        )
        results = []
        for r in response.get('results', []):
            results.append({
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'content': r.get('content', '')
            })
        return results
    except Exception as e:
        print(f"Tavily search error for '{query}': {e}")
        return []

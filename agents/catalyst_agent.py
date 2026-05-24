import json

from agents.ai_utils import by_ticker, compact_candidate, parse_llm_json, unique_by_ticker
from tools.llm_tool import get_llm
from tools.tavily_search import search_news


MAX_CATALYST_CANDIDATES = 12


def _technical_catalyst(item: dict, news: list[dict]) -> dict:
    tech = item.get("technicals", {})
    reasons = item.get("quant_reasons", [])
    catalyst_type = "technical" if reasons else "none"
    strength = 6 if item.get("hard_pass") else 5
    if tech.get("Breakout"):
        strength += 1
    if tech.get("Volume_Ratio", 0) and tech.get("Volume_Ratio", 0) >= 1.5:
        strength += 1
    return {
        "ticker": item.get("ticker"),
        "catalyst_type": catalyst_type,
        "catalyst": "; ".join(reasons[:2]) if reasons else "none",
        "catalyst_strength": min(strength, 8),
        "freshness": "technical",
        "evidence": reasons,
        "source_urls": [n.get("url") for n in news if n.get("url")][:3],
    }


def run_catalyst_agent(state: dict) -> dict:
    """
    Searches recent context for top candidates and extracts why-now evidence.
    Falls back to technical/quant catalysts when news or LLM access is unavailable.
    """
    candidates = unique_by_ticker(state.get("candidates") or [], MAX_CATALYST_CANDIDATES)
    fundamentals = state.get("fundamentals", {})
    technicals = state.get("technicals", {})
    compact = [compact_candidate(c, fundamentals, technicals) for c in candidates]

    if not compact:
        state["catalyst_checks"] = {}
        return state

    news_by_ticker = {}
    for item in compact:
        ticker = item["ticker"]
        clean_name = ticker.replace(".NS", "").replace(".BO", "")
        results = search_news(f"{clean_name} NSE stock latest results order win sector news India", max_results=4)
        news_by_ticker[ticker] = results

    llm = get_llm(temperature=0.2)
    if not llm:
        checks = [_technical_catalyst(item, news_by_ticker.get(item["ticker"], [])) for item in compact]
        state["catalyst_checks"] = by_ticker(checks)
        print(f"Catalyst agent: fallback catalyst checks for {len(checks)} candidates.")
        return state

    news_payload = {
        item["ticker"]: [
            {"title": n.get("title"), "url": n.get("url"), "content": (n.get("content") or "")[:350]}
            for n in news_by_ticker.get(item["ticker"], [])
        ]
        for item in compact
    }

    prompt = f"""You are a catalyst analyst for Indian equities.
For each candidate, identify the strongest why-now driver. Prefer recent news if present, otherwise use the supplied technical/quant evidence.
Do not invent news or dates. If evidence is weak, say catalyst_type "none".

Candidates:
{json.dumps(compact, indent=2, default=str)}

Recent news snippets:
{json.dumps(news_payload, indent=2, default=str)}

Return ONLY valid JSON:
{{
  "catalysts": [
    {{
      "ticker": "TICKER.NS",
      "catalyst_type": "news|earnings|sector|technical|quant|none",
      "catalyst": "specific why-now driver or none",
      "catalyst_strength": <integer 1-10>,
      "freshness": "today|this_week|stale|technical|unknown",
      "evidence": ["specific evidence"],
      "source_urls": ["urls used"]
    }}
  ]
}}
"""
    try:
        response = llm.invoke(prompt)
        parsed = parse_llm_json(response.content, {"catalysts": []})
        checks = parsed.get("catalysts", []) if isinstance(parsed, dict) else []
        if not checks:
            checks = [_technical_catalyst(item, news_by_ticker.get(item["ticker"], [])) for item in compact]
        state["catalyst_checks"] = by_ticker(checks)
        print(f"Catalyst agent: {len(state['catalyst_checks'])} catalyst checks generated.")
    except Exception as e:
        checks = [_technical_catalyst(item, news_by_ticker.get(item["ticker"], [])) for item in compact]
        state["catalyst_checks"] = by_ticker(checks)
        print(f"Catalyst agent error: {e}; using deterministic fallback.")

    return state

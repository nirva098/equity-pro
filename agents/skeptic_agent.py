import json

from agents.ai_utils import by_ticker, compact_candidate, parse_llm_json, unique_by_ticker
from tools.llm_tool import get_llm


MAX_SKEPTIC_CANDIDATES = 12


def _fallback_review(item: dict, catalyst: dict) -> dict:
    tech = item.get("technicals", {})
    red_flags = []
    if tech.get("RSI14", 50) >= 70:
        red_flags.append("RSI is overheated")
    if tech.get("Volume_Ratio", 1) < 0.5:
        red_flags.append("weak latest volume")
    if tech.get("Distance_to_52w_High_%", 0) > 30:
        red_flags.append("far from 52-week high")
    if catalyst.get("catalyst_type") == "none":
        red_flags.append("no clear catalyst")
    return {
        "ticker": item.get("ticker"),
        "bear_case": "; ".join(red_flags) if red_flags else "Main risk is failed follow-through after entry.",
        "red_flags": red_flags,
        "kill_trade": len(red_flags) >= 3,
        "risk_penalty": min(0.15 * len(red_flags), 0.6),
        "invalidation": "Reject if price closes below stop or setup-specific momentum fails.",
    }


def run_skeptic_agent(state: dict) -> dict:
    """
    Challenges top candidates before final ranking. This agent can kill weak ideas.
    """
    candidates = unique_by_ticker(state.get("candidates") or [], MAX_SKEPTIC_CANDIDATES)
    fundamentals = state.get("fundamentals", {})
    technicals = state.get("technicals", {})
    catalysts = state.get("catalyst_checks", {})
    briefs = state.get("research_briefs", {})
    compact = [compact_candidate(c, fundamentals, technicals) for c in candidates]

    if not compact:
        state["skeptic_reviews"] = {}
        return state

    llm = get_llm(temperature=0.1)
    if not llm:
        reviews = [_fallback_review(item, catalysts.get(item["ticker"], {})) for item in compact]
        state["skeptic_reviews"] = by_ticker(reviews)
        print(f"Skeptic agent: fallback reviews for {len(reviews)} candidates.")
        return state

    payload = []
    for item in compact:
        ticker = item["ticker"]
        payload.append({
            "candidate": item,
            "brief": briefs.get(ticker, {}),
            "catalyst": catalysts.get(ticker, {}),
        })

    prompt = f"""You are a skeptical portfolio risk analyst.
Challenge each trade candidate. Be specific and conservative, but do not reject good setups just because no news headline exists.
Only set kill_trade true for serious issues: weak evidence, overextension, bad liquidity/volume, poor setup fit, or unattractive risk.

Inputs:
{json.dumps(payload, indent=2, default=str)}

Return ONLY valid JSON:
{{
  "reviews": [
    {{
      "ticker": "TICKER.NS",
      "bear_case": "specific bear case",
      "red_flags": ["specific red flags"],
      "kill_trade": true_or_false,
      "risk_penalty": <number 0.0 to 1.0>,
      "invalidation": "specific condition that invalidates the trade"
    }}
  ]
}}
"""
    try:
        response = llm.invoke(prompt)
        parsed = parse_llm_json(response.content, {"reviews": []})
        reviews = parsed.get("reviews", []) if isinstance(parsed, dict) else []
        if not reviews:
            reviews = [_fallback_review(item, catalysts.get(item["ticker"], {})) for item in compact]
        state["skeptic_reviews"] = by_ticker(reviews)
        print(f"Skeptic agent: {len(state['skeptic_reviews'])} reviews generated.")
    except Exception as e:
        reviews = [_fallback_review(item, catalysts.get(item["ticker"], {})) for item in compact]
        state["skeptic_reviews"] = by_ticker(reviews)
        print(f"Skeptic agent error: {e}; using deterministic fallback.")

    return state

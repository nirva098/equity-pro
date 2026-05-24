import json

from agents.ai_utils import compact_candidate, parse_llm_json, unique_by_ticker
from tools.llm_tool import get_llm


MAX_RANKING_CANDIDATES = 12
MAX_FINAL_CANDIDATES = 8


def _numeric(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _deterministic_rank(payload: list[dict]) -> list[dict]:
    ranked = []
    for item in payload:
        c = item["candidate"]
        catalyst = item.get("catalyst", {})
        skeptic = item.get("skeptic", {})
        catalyst_strength = _numeric(catalyst.get("catalyst_strength"), 4)
        penalty = _numeric(skeptic.get("risk_penalty"), 0)
        conviction = _numeric(c.get("quant_score"), 0) + (catalyst_strength / 3.0) - (penalty * 2.0)
        decision = "reject" if skeptic.get("kill_trade") else "trade"
        if conviction < 4.0:
            decision = "watchlist"
        ranked.append({
            "ticker": c.get("ticker"),
            "setup": c.get("setup"),
            "decision": decision,
            "conviction": max(1, min(10, round(conviction, 1))),
            "why_now": catalyst.get("catalyst") or "; ".join(c.get("quant_reasons", [])),
            "why_this_over_others": "Ranked by quant score, catalyst strength, and skeptic penalty.",
            "position_bias": "half" if penalty >= 0.3 or catalyst_strength <= 5 else "full",
        })
    ranked.sort(key=lambda r: (r["decision"] == "trade", r["conviction"]), reverse=True)
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def run_ranking_agent(state: dict) -> dict:
    """
    Final PM-style ranking before sizing.
    Updates state['candidates'] to the final AI-approved trade/watchlist shortlist.
    """
    candidates = unique_by_ticker(state.get("candidates") or [], MAX_RANKING_CANDIDATES)
    fundamentals = state.get("fundamentals", {})
    technicals = state.get("technicals", {})
    briefs = state.get("research_briefs", {})
    catalysts = state.get("catalyst_checks", {})
    skeptic_reviews = state.get("skeptic_reviews", {})
    market_context = state.get("market_context", {})

    payload = []
    for c in candidates:
        ticker = c.get("ticker")
        payload.append({
            "candidate": compact_candidate(c, fundamentals, technicals),
            "brief": briefs.get(ticker, {}),
            "catalyst": catalysts.get(ticker, {}),
            "skeptic": skeptic_reviews.get(ticker, {}),
        })

    if not payload:
        state["final_rankings"] = []
        return state

    llm = get_llm(temperature=0.15)
    if not llm:
        rankings = _deterministic_rank(payload)
    else:
        prompt = f"""You are the portfolio manager making the final pre-market shortlist.
Rank the trade candidates using quant evidence, catalyst strength, skeptic review, market regime, diversification, and risk/reward.
Reject weak ideas. Prefer a small number of high-quality recommendations over filling slots.

Market context:
{json.dumps(market_context, indent=2, default=str)}

Candidates with research:
{json.dumps(payload, indent=2, default=str)}

Return ONLY valid JSON:
{{
  "recommendations": [
    {{
      "ticker": "TICKER.NS",
      "setup": "setup_name",
      "rank": 1,
      "decision": "trade|watchlist|reject",
      "conviction": <integer 1-10>,
      "why_now": "specific reason",
      "why_this_over_others": "relative ranking reason",
      "position_bias": "full|half|watchlist"
    }}
  ]
}}
"""
        try:
            response = llm.invoke(prompt)
            parsed = parse_llm_json(response.content, {"recommendations": []})
            rankings = parsed.get("recommendations", []) if isinstance(parsed, dict) else []
            if not rankings:
                rankings = _deterministic_rank(payload)
        except Exception as e:
            print(f"Ranking agent error: {e}; using deterministic fallback.")
            rankings = _deterministic_rank(payload)

    rankings_by_ticker = {r.get("ticker"): r for r in rankings if r.get("ticker")}
    final_candidates = []
    for c in candidates:
        ticker = c.get("ticker")
        ranking = rankings_by_ticker.get(ticker)
        if not ranking or ranking.get("decision") != "trade":
            continue
        enriched = c.copy()
        enriched["ai_rank"] = ranking.get("rank")
        enriched["ai_decision"] = ranking.get("decision")
        enriched["ai_conviction"] = ranking.get("conviction")
        enriched["why_now"] = ranking.get("why_now")
        enriched["why_this_over_others"] = ranking.get("why_this_over_others")
        enriched["position_bias"] = ranking.get("position_bias")
        final_candidates.append(enriched)

    final_candidates.sort(key=lambda c: (c.get("ai_rank") or 999, -(c.get("ai_conviction") or 0)))
    state["final_rankings"] = rankings
    state["candidates"] = final_candidates[:MAX_FINAL_CANDIDATES]
    print(f"Ranking agent: {len(state['candidates'])} candidates forwarded to risk sizing.")
    return state

import json

from agents.ai_utils import by_ticker, compact_candidate, parse_llm_json, unique_by_ticker
from tools.llm_tool import get_llm


MAX_BRIEF_CANDIDATES = 20


def _fallback_brief(item: dict) -> dict:
    reasons = item.get("quant_reasons", [])
    return {
        "ticker": item.get("ticker"),
        "setup": item.get("setup"),
        "bull_case": "; ".join(reasons) if reasons else "Quant score is strong versus the screened universe.",
        "quant_evidence": reasons,
        "setup_fit_score": 7 if item.get("hard_pass") else 6,
        "missing_data": [],
        "must_verify": ["fresh catalyst", "liquidity and gap risk"],
    }


def run_research_brief_agent(state: dict) -> dict:
    """
    Converts top quant candidates into structured analyst briefs.
    This is intentionally batched to keep free-tier LLM usage under control.
    """
    candidates = unique_by_ticker(state.get("candidates") or [], MAX_BRIEF_CANDIDATES)
    fundamentals = state.get("fundamentals", {})
    technicals = state.get("technicals", {})
    compact = [compact_candidate(c, fundamentals, technicals) for c in candidates]

    if not compact:
        state["research_briefs"] = {}
        return state

    llm = get_llm(temperature=0.2)
    if not llm:
        briefs = [_fallback_brief(c) for c in compact]
        state["research_briefs"] = by_ticker(briefs)
        state["llm_available"] = False
        print(f"Research brief agent: fallback briefs for {len(briefs)} candidates.")
        return state

    prompt = f"""You are an Indian equity research analyst.
Create concise structured research briefs for these NSE trade candidates.
Use only the supplied numbers. Do not invent facts, management comments, or news.

Candidates:
{json.dumps(compact, indent=2, default=str)}

Return ONLY valid JSON:
{{
  "briefs": [
    {{
      "ticker": "TICKER.NS",
      "setup": "setup_name",
      "bull_case": "one specific paragraph based on data",
      "quant_evidence": ["specific supplied evidence"],
      "setup_fit_score": <integer 1-10>,
      "missing_data": ["data that would improve confidence"],
      "must_verify": ["specific pre-trade checks"]
    }}
  ]
}}
"""
    try:
        response = llm.invoke(prompt)
        parsed = parse_llm_json(response.content, {"briefs": []})
        briefs = parsed.get("briefs", []) if isinstance(parsed, dict) else []
        if not briefs:
            briefs = [_fallback_brief(c) for c in compact]
        state["research_briefs"] = by_ticker(briefs)
        state["llm_available"] = True
        print(f"Research brief agent: {len(state['research_briefs'])} briefs generated.")
    except Exception as e:
        briefs = [_fallback_brief(c) for c in compact]
        state["research_briefs"] = by_ticker(briefs)
        state["llm_available"] = False
        print(f"Research brief agent error: {e}; using deterministic fallback.")

    return state

import json
import re
from typing import Any


def parse_llm_json(content: str, fallback: Any) -> Any:
    """Parse JSON from an LLM response, tolerating markdown fences and leading text."""
    if not content:
        return fallback

    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        return fallback

    try:
        return json.loads(match.group(1))
    except Exception:
        return fallback


def compact_candidate(candidate: dict, fundamentals: dict, technicals: dict) -> dict:
    ticker = candidate.get("ticker")
    fund = fundamentals.get(ticker, {}) or {}
    tech = technicals.get(ticker, {}) or {}
    return {
        "ticker": ticker,
        "setup": candidate.get("setup"),
        "quant_score": candidate.get("score"),
        "hard_pass": candidate.get("hard_pass", False),
        "quant_reasons": candidate.get("quant_reasons", []),
        "fundamentals": {
            "DCF_Upside_%": fund.get("DCF_Upside_%"),
            "F_Score": fund.get("F_Score"),
            "FCF_Yield_%": fund.get("FCF_Yield_%"),
            "ROCE_%": fund.get("ROCE_%"),
            "DE_Ratio": fund.get("DE_Ratio"),
            "Revenue_Growth_%": fund.get("Revenue_Growth_%"),
        },
        "technicals": {
            "close": tech.get("close"),
            "ATR14": tech.get("ATR14"),
            "RSI14": tech.get("RSI14"),
            "ADX14": tech.get("ADX14"),
            "DMA50": tech.get("DMA50"),
            "DMA200": tech.get("DMA200"),
            "3M_Return_%": tech.get("3M_Return_%"),
            "Distance_to_52w_High_%": tech.get("Distance_to_52w_High_%"),
            "Volume_Ratio": tech.get("Volume_Ratio"),
            "Breakout": tech.get("Breakout"),
        },
    }


def by_ticker(items: list[dict]) -> dict:
    return {item.get("ticker"): item for item in items if item.get("ticker")}


def unique_by_ticker(candidates: list[dict], limit: int) -> list[dict]:
    selected = []
    seen = set()
    for candidate in candidates:
        ticker = candidate.get("ticker")
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected

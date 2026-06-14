from __future__ import annotations

import json
from collections import defaultdict


DEFAULT_MEMORY = {
    "setups": {},
    "regime_multipliers": {"risk_on": 1.0, "risk_off": 0.5, "high_vix": 0.3},
    "special_events": [],
}


def load_strategy_memory(path: str = "memory/strategy_memory.json") -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(DEFAULT_MEMORY))


def _weight_snapshot(memory: dict, setup: str) -> dict:
    setup_data = (memory or {}).get("setups", {}).get(setup, {})
    return {
        "trades": int(setup_data.get("trades", 0) or 0),
        "wins": int(setup_data.get("wins", 0) or 0),
        "weight": float(setup_data.get("weight", 0.5) or 0.5),
    }


def _nudge_label(total_r: float, win_rate: float, weight_delta: float) -> str:
    if total_r >= 1.5 or (win_rate >= 60 and weight_delta > 0):
        return "lean_in"
    if total_r <= -1.0 or win_rate <= 33:
        return "trim_risk"
    return "stay_patient"


def _nudge_text(label: str, setup: str) -> str:
    pretty = setup.replace("_", " ")
    if label == "lean_in":
        return f"Lean in on {pretty} if the same conditions reappear."
    if label == "trim_risk":
        return f"Trim risk on {pretty} next cycle unless the tape is materially cleaner."
    return f"Keep {pretty} active, but wait for cleaner confirmation."


def build_feedback_loop(
    closed_trades: list[dict],
    memory_before: dict,
    memory_after: dict,
    regime: str = "unknown",
) -> dict:
    by_setup: dict[str, list[dict]] = defaultdict(list)
    for trade in closed_trades or []:
        by_setup[trade.get("setup", "unknown")].append(trade)

    setup_feedback = []
    for setup, trades in sorted(by_setup.items()):
        total_r = round(sum(float(t.get("pnl_R", 0) or 0) for t in trades), 2)
        wins = sum(1 for t in trades if float(t.get("pnl_R", 0) or 0) > 0)
        trade_count = len(trades)
        win_rate = round((wins / trade_count) * 100, 1) if trade_count else 0.0
        avg_r = round(total_r / trade_count, 2) if trade_count else 0.0
        before = _weight_snapshot(memory_before, setup)
        after = _weight_snapshot(memory_after, setup)
        weight_delta = round(after["weight"] - before["weight"], 4)
        nudge = _nudge_label(total_r, win_rate, weight_delta)
        setup_feedback.append(
            {
                "setup": setup,
                "trades": trade_count,
                "wins": wins,
                "win_rate": win_rate,
                "total_R": total_r,
                "avg_R": avg_r,
                "weight_before": before["weight"],
                "weight_after": after["weight"],
                "weight_delta": weight_delta,
                "nudge": nudge,
                "nudge_text": _nudge_text(nudge, setup),
            }
        )

    setup_feedback.sort(key=lambda item: (item["total_R"], item["weight_delta"]), reverse=True)

    if not setup_feedback:
        headline = "No closed trades today, so there is nothing to judge yet."
        next_cycle = ["Hold current setup mix and wait for fresh data."]
    else:
        best = setup_feedback[0]
        worst = min(setup_feedback, key=lambda item: item["total_R"])
        headline = (
            f"Best setup: {best['setup']} at {best['total_R']:+.2f}R. "
            f"Weakest setup: {worst['setup']} at {worst['total_R']:+.2f}R."
        )
        next_cycle = [item["nudge_text"] for item in setup_feedback[:3]]

    total_r = round(sum(float(t.get("pnl_R", 0) or 0) for t in closed_trades or []), 2)
    wins = sum(1 for t in closed_trades or [] if float(t.get("pnl_R", 0) or 0) > 0)
    trade_count = len(closed_trades or [])

    return {
        "regime": regime,
        "trades": trade_count,
        "wins": wins,
        "win_rate": round((wins / trade_count) * 100, 1) if trade_count else 0.0,
        "total_R": total_r,
        "headline": headline,
        "setups": setup_feedback,
        "next_cycle": next_cycle,
    }

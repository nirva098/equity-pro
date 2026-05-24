import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any


RESEARCH_DB_PATH = os.getenv("RESEARCH_DB_PATH", "data/research.db")
SCHEMA_PATH = "db/research_schema.sql"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def init_research_db(db_path: str = RESEARCH_DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        with open(SCHEMA_PATH, "r") as f:
            conn.executescript(f.read())
        conn.commit()


def start_research_run(
    trade_date: str,
    run_type: str,
    scanned_count: int = 0,
    metadata: dict | None = None,
    db_path: str = RESEARCH_DB_PATH,
) -> str:
    init_research_db(db_path)
    run_id = f"{trade_date}-{run_type}-{uuid.uuid4().hex[:8]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO research_runs (
                run_id, run_type, trade_date, started_at, status, scanned_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, run_type, trade_date, _now(), "running", scanned_count, _json(metadata or {})),
        )
        conn.commit()
    return run_id


def finish_research_run(
    run_id: str,
    status: str,
    state: dict,
    error: str | None = None,
    db_path: str = RESEARCH_DB_PATH,
) -> None:
    market_context = state.get("market_context", {}) or {}
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE research_runs
               SET finished_at = ?,
                   status = ?,
                   regime = ?,
                   risk_modifier = ?,
                   active_setups_json = ?,
                   candidates_count = ?,
                   trades_count = ?,
                   error = ?
             WHERE run_id = ?
            """,
            (
                _now(),
                status,
                market_context.get("regime"),
                state.get("risk_modifier"),
                _json(state.get("active_setups", [])),
                len(state.get("screened_candidates", state.get("candidates", [])) or []),
                len(state.get("trades", []) or []),
                error,
                run_id,
            ),
        )
        conn.commit()


def log_run_event(
    run_id: str,
    stage: str,
    message: str,
    level: str = "info",
    payload: dict | None = None,
    db_path: str = RESEARCH_DB_PATH,
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO run_events (run_id, stage, level, message, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, stage, level, message, _json(payload or {}), _now()),
        )
        conn.commit()


def persist_premarket_state(run_id: str, state: dict, db_path: str = RESEARCH_DB_PATH) -> None:
    trade_date = state.get("date") or datetime.now().strftime("%Y-%m-%d")
    candidates = state.get("screened_candidates", state.get("candidates", [])) or []
    trades = state.get("trades", []) or []
    fundamentals = state.get("fundamentals", {}) or {}
    technicals = state.get("technicals", {}) or {}
    thesis = state.get("thesis", {}) or {}
    research_briefs = state.get("research_briefs", {}) or {}
    catalyst_checks = state.get("catalyst_checks", {}) or {}
    skeptic_reviews = state.get("skeptic_reviews", {}) or {}
    final_rankings = state.get("final_rankings", []) or []

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM screen_candidates WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM trade_recommendations WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM research_briefs WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM catalyst_checks WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM skeptic_reviews WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM final_rankings WHERE run_id = ?", (run_id,))

        for rank, candidate in enumerate(candidates, start=1):
            ticker = candidate.get("ticker")
            conn.execute(
                """
                INSERT INTO screen_candidates (
                    run_id, trade_date, ticker, setup, rank, score, expected_R, hard_pass,
                    quant_reasons_json, fundamentals_json, technicals_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    trade_date,
                    ticker,
                    candidate.get("setup"),
                    rank,
                    candidate.get("score", 0),
                    candidate.get("expected_R"),
                    1 if candidate.get("hard_pass") else 0,
                    _json(candidate.get("quant_reasons", [])),
                    _json(fundamentals.get(ticker, {})),
                    _json(technicals.get(ticker, {})),
                    _now(),
                ),
            )

        for ticker, brief in research_briefs.items():
            conn.execute(
                """
                INSERT INTO research_briefs (
                    run_id, trade_date, ticker, setup, bull_case, setup_fit_score,
                    quant_evidence_json, missing_data_json, must_verify_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    trade_date,
                    ticker,
                    brief.get("setup"),
                    brief.get("bull_case"),
                    brief.get("setup_fit_score"),
                    _json(brief.get("quant_evidence", [])),
                    _json(brief.get("missing_data", [])),
                    _json(brief.get("must_verify", [])),
                    _now(),
                ),
            )

        for ticker, catalyst in catalyst_checks.items():
            conn.execute(
                """
                INSERT INTO catalyst_checks (
                    run_id, trade_date, ticker, catalyst_type, catalyst, catalyst_strength,
                    freshness, evidence_json, source_urls_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    trade_date,
                    ticker,
                    catalyst.get("catalyst_type"),
                    catalyst.get("catalyst"),
                    catalyst.get("catalyst_strength"),
                    catalyst.get("freshness"),
                    _json(catalyst.get("evidence", [])),
                    _json(catalyst.get("source_urls", [])),
                    _now(),
                ),
            )

        for ticker, review in skeptic_reviews.items():
            conn.execute(
                """
                INSERT INTO skeptic_reviews (
                    run_id, trade_date, ticker, bear_case, red_flags_json, kill_trade,
                    risk_penalty, invalidation, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    trade_date,
                    ticker,
                    review.get("bear_case"),
                    _json(review.get("red_flags", [])),
                    1 if review.get("kill_trade") else 0,
                    review.get("risk_penalty"),
                    review.get("invalidation"),
                    _now(),
                ),
            )

        for ranking in final_rankings:
            conn.execute(
                """
                INSERT INTO final_rankings (
                    run_id, trade_date, ticker, setup, rank, decision, conviction,
                    why_now, why_this_over_others, position_bias, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    trade_date,
                    ranking.get("ticker"),
                    ranking.get("setup"),
                    ranking.get("rank"),
                    ranking.get("decision"),
                    ranking.get("conviction"),
                    ranking.get("why_now"),
                    ranking.get("why_this_over_others"),
                    ranking.get("position_bias"),
                    _now(),
                ),
            )

        for rank, trade in enumerate(trades, start=1):
            ticker = trade.get("ticker")
            ticker_thesis = thesis.get(ticker, {}) if isinstance(thesis, dict) else {}
            ticker_catalyst = catalyst_checks.get(ticker, {}) if isinstance(catalyst_checks, dict) else {}
            ticker_review = skeptic_reviews.get(ticker, {}) if isinstance(skeptic_reviews, dict) else {}
            conn.execute(
                """
                INSERT INTO trade_recommendations (
                    run_id, trade_date, ticker, setup, rank, entry, sl, target, qty,
                    risk_per_share, total_risk, expected_R, kelly_f, score, confidence,
                    catalyst, catalyst_type, news_sentiment, thesis, bear_case,
                    quant_reasons_json, hard_pass, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    trade_date,
                    ticker,
                    trade.get("setup"),
                    rank,
                    trade.get("entry"),
                    trade.get("sl"),
                    trade.get("target"),
                    trade.get("qty"),
                    trade.get("risk_per_share"),
                    trade.get("total_risk"),
                    trade.get("expected_R"),
                    trade.get("kelly_f"),
                    trade.get("score"),
                    trade.get("confidence", ticker_thesis.get("confidence", trade.get("ai_conviction"))),
                    trade.get("catalyst", ticker_thesis.get("catalyst", ticker_catalyst.get("catalyst"))),
                    trade.get("catalyst_type", ticker_thesis.get("catalyst_type", ticker_catalyst.get("catalyst_type"))),
                    trade.get("news_sentiment"),
                    ticker_thesis.get("thesis", ""),
                    trade.get("bear_case", ticker_thesis.get("bear_case", ticker_review.get("bear_case", ""))),
                    _json(trade.get("quant_reasons", [])),
                    1 if trade.get("hard_pass") else 0,
                    "recommended",
                    _now(),
                ),
            )
        conn.commit()


def latest_run(db_path: str = RESEARCH_DB_PATH) -> dict | None:
    if not os.path.exists(db_path):
        return None
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM research_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

def update_trade_execution(run_id: str, ticker: str, status: str, execution_price: float, db_path: str = RESEARCH_DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE trade_recommendations
               SET status = ?,
                   execution_price = ?
             WHERE run_id = ? AND ticker = ?
            """,
            (status, execution_price, run_id, ticker)
        )
        conn.commit()

def get_open_trades(date: str = None, db_path: str = RESEARCH_DB_PATH) -> list:
    """Get all filled trades (open positions), optionally filtered by date."""
    if not os.path.exists(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        if date:
            rows = conn.execute(
                "SELECT * FROM trade_recommendations WHERE status = 'filled' AND trade_date = ?", (date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trade_recommendations WHERE status = 'filled'"
            ).fetchall()
        return [dict(row) for row in rows]

def update_trade_exit(trade_id: int, exit_price: float, pnl_R: float, pnl_abs: float, db_path: str = RESEARCH_DB_PATH) -> None:
    """Update a trade with exit data and mark as closed."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """UPDATE trade_recommendations 
               SET exit_price = ?, exit_time = ?, pnl_R = ?, pnl_abs = ?, status = 'closed'
               WHERE id = ?""",
            (exit_price, datetime.now().strftime('%H:%M:%S'), pnl_R, pnl_abs, trade_id)
        )
        conn.commit()

def get_closed_trades(date: str = None, db_path: str = RESEARCH_DB_PATH) -> list:
    """Get all closed trades, optionally filtered by date."""
    if not os.path.exists(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        if date:
            rows = conn.execute(
                "SELECT * FROM trade_recommendations WHERE status = 'closed' AND trade_date = ?", (date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trade_recommendations WHERE status = 'closed'"
            ).fetchall()
        return [dict(row) for row in rows]

def log_daily_run(date: str, regime: str, trades_taken: int,
                  win_rate: float, total_R: float, journal_entry: str, db_path: str = RESEARCH_DB_PATH) -> None:
    """Insert or replace a daily run summary."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO daily_runs (date, regime, trades_taken, win_rate, total_R, journal_entry)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date, regime, trades_taken, win_rate, total_R, journal_entry)
        )
        conn.commit()

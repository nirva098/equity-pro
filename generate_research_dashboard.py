import json
import os
import sqlite3
from datetime import datetime

from core.research_db import RESEARCH_DB_PATH, init_research_db


def _rows(conn, query, params=()):
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def _load_json(value, fallback):
    try:
        return json.loads(value) if value else fallback
    except Exception:
        return fallback


def generate_research_dashboard(db_path: str = RESEARCH_DB_PATH, out_path: str = "reports/research_dashboard.html"):
    init_research_db(db_path)
    with sqlite3.connect(db_path) as conn:
        runs = _rows(
            conn,
            """
            SELECT * FROM research_runs
            ORDER BY started_at DESC
            LIMIT 30
            """,
        )
        latest = runs[0] if runs else None
        candidates = []
        trades = []
        rankings = []
        events = []
        if latest:
            candidates = _rows(
                conn,
                """
                SELECT * FROM screen_candidates
                WHERE run_id = ?
                ORDER BY rank ASC
                LIMIT 50
                """,
                (latest["run_id"],),
            )
            trades = _rows(
                conn,
                """
                SELECT * FROM trade_recommendations
                WHERE run_id = ?
                ORDER BY rank ASC
                """,
                (latest["run_id"],),
            )
            rankings = _rows(
                conn,
                """
                SELECT * FROM final_rankings
                WHERE run_id = ?
                ORDER BY rank ASC
                """,
                (latest["run_id"],),
            )
            events = _rows(
                conn,
                """
                SELECT * FROM run_events
                WHERE run_id = ?
                ORDER BY created_at ASC
                LIMIT 100
                """,
                (latest["run_id"],),
            )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not latest:
        body = "<main><h1>Research DB</h1><p>No research runs stored yet.</p></main>"
    else:
        active_setups = _load_json(latest.get("active_setups_json"), [])
        run_cards = "".join(
            f"""
            <tr>
              <td>{r.get('trade_date', '')}</td>
              <td>{r.get('run_type', '')}</td>
              <td><span class="status {r.get('status', '')}">{r.get('status', '')}</span></td>
              <td>{r.get('regime') or '-'}</td>
              <td>{r.get('scanned_count') or 0}</td>
              <td>{r.get('candidates_count') or 0}</td>
              <td>{r.get('trades_count') or 0}</td>
              <td>{r.get('started_at', '')}</td>
            </tr>
            """
            for r in runs
        )
        candidate_rows = "".join(
            f"""
            <tr>
              <td>{c.get('rank')}</td>
              <td><b>{c.get('ticker', '').replace('.NS', '')}</b></td>
              <td>{c.get('setup', '').replace('_', ' ')}</td>
              <td>{float(c.get('score') or 0):.2f}</td>
              <td>{'yes' if c.get('hard_pass') else 'no'}</td>
              <td>{', '.join(_load_json(c.get('quant_reasons_json'), []))}</td>
            </tr>
            """
            for c in candidates
        )
        trade_rows = "".join(
            f"""
            <tr>
              <td>{t.get('rank')}</td>
              <td><b>{t.get('ticker', '').replace('.NS', '')}</b></td>
              <td>{t.get('setup', '').replace('_', ' ')}</td>
              <td>{float(t.get('entry') or 0):.2f}</td>
              <td>{float(t.get('sl') or 0):.2f}</td>
              <td>{float(t.get('target') or 0):.2f}</td>
              <td>{t.get('qty')}</td>
              <td>{float(t.get('total_risk') or 0):.0f}</td>
              <td>{float(t.get('expected_R') or 0):.2f}</td>
              <td>{t.get('catalyst_type') or '-'}</td>
            </tr>
            """
            for t in trades
        )
        ranking_rows = "".join(
            f"""
            <tr>
              <td>{r.get('rank') or '-'}</td>
              <td><b>{r.get('ticker', '').replace('.NS', '')}</b></td>
              <td>{r.get('setup', '').replace('_', ' ')}</td>
              <td><span class="status {r.get('decision', '')}">{r.get('decision', '')}</span></td>
              <td>{r.get('conviction') or '-'}</td>
              <td>{r.get('position_bias') or '-'}</td>
              <td>{r.get('why_now') or '-'}</td>
              <td>{r.get('why_this_over_others') or '-'}</td>
            </tr>
            """
            for r in rankings
        )
        event_rows = "".join(
            f"""
            <tr>
              <td>{e.get('created_at')}</td>
              <td>{e.get('stage')}</td>
              <td>{e.get('level')}</td>
              <td>{e.get('message')}</td>
            </tr>
            """
            for e in events
        )
        body = f"""
        <main>
          <section class="hero">
            <div>
              <p class="eyebrow">Latest research run</p>
              <h1>{latest.get('trade_date')} {latest.get('run_type')}</h1>
              <p class="muted">{latest.get('run_id')}</p>
            </div>
            <div class="metrics">
              <div><span>Scanned</span><strong>{latest.get('scanned_count') or 0}</strong></div>
              <div><span>Candidates</span><strong>{latest.get('candidates_count') or 0}</strong></div>
              <div><span>Trades</span><strong>{latest.get('trades_count') or 0}</strong></div>
              <div><span>Risk Mod</span><strong>{latest.get('risk_modifier') or '-'}</strong></div>
            </div>
          </section>

          <section class="panel">
            <h2>Run Context</h2>
            <div class="chips">
              <span>{latest.get('status')}</span>
              <span>{latest.get('regime') or 'regime unknown'}</span>
              {''.join(f'<span>{s.replace("_", " ")}</span>' for s in active_setups)}
            </div>
            {f'<p class="error">{latest.get("error")}</p>' if latest.get("error") else ''}
          </section>

          <section class="panel">
            <h2>Recommended Trades</h2>
            <table>
              <thead><tr><th>#</th><th>Ticker</th><th>Setup</th><th>Entry</th><th>SL</th><th>Target</th><th>Qty</th><th>Risk</th><th>R</th><th>Driver</th></tr></thead>
              <tbody>{trade_rows or '<tr><td colspan="10">No trades recommended.</td></tr>'}</tbody>
            </table>
          </section>

          <section class="panel">
            <h2>AI Final Ranking</h2>
            <table>
              <thead><tr><th>#</th><th>Ticker</th><th>Setup</th><th>Decision</th><th>Conviction</th><th>Bias</th><th>Why Now</th><th>Relative Reason</th></tr></thead>
              <tbody>{ranking_rows or '<tr><td colspan="8">No AI rankings stored.</td></tr>'}</tbody>
            </table>
          </section>

          <section class="panel">
            <h2>Candidate Funnel</h2>
            <table>
              <thead><tr><th>#</th><th>Ticker</th><th>Setup</th><th>Score</th><th>Hard Pass</th><th>Reasons</th></tr></thead>
              <tbody>{candidate_rows or '<tr><td colspan="6">No candidates stored.</td></tr>'}</tbody>
            </table>
          </section>

          <section class="panel">
            <h2>Run History</h2>
            <table>
              <thead><tr><th>Date</th><th>Type</th><th>Status</th><th>Regime</th><th>Scanned</th><th>Candidates</th><th>Trades</th><th>Started</th></tr></thead>
              <tbody>{run_cards}</tbody>
            </table>
          </section>

          <section class="panel">
            <h2>Events</h2>
            <table>
              <thead><tr><th>Time</th><th>Stage</th><th>Level</th><th>Message</th></tr></thead>
              <tbody>{event_rows or '<tr><td colspan="4">No events stored.</td></tr>'}</tbody>
            </table>
          </section>
        </main>
        """

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Equity Pro Research DB</title>
  <style>
    :root {{
      --bg: #0f1115;
      --panel: #171a21;
      --line: #2b303b;
      --text: #e6e8ee;
      --muted: #9aa3b2;
      --accent: #4fb3a3;
      --warn: #e2b86b;
      --bad: #ef7373;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h1, h2, p {{ margin: 0; }}
    h1 {{ font-size: 28px; margin-top: 4px; }}
    h2 {{ font-size: 15px; margin-bottom: 14px; }}
    .hero {{ display: flex; justify-content: space-between; gap: 20px; align-items: stretch; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--accent); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; font-weight: 700; }}
    .muted {{ color: var(--muted); margin-top: 8px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(100px, 1fr)); gap: 10px; min-width: 460px; }}
    .metrics div, .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
    .metrics div {{ padding: 14px; }}
    .metrics span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }}
    .metrics strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    .panel {{ padding: 18px; margin-bottom: 18px; overflow: auto; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .chips span {{ border: 1px solid var(--line); border-radius: 999px; padding: 5px 10px; color: var(--muted); font-size: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ color: var(--muted); text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid var(--line); padding: 10px 8px; }}
    td {{ border-bottom: 1px solid var(--line); padding: 10px 8px; vertical-align: top; }}
    tr:last-child td {{ border-bottom: 0; }}
    .status {{ border-radius: 999px; padding: 3px 8px; background: #22332f; color: var(--accent); }}
    .status.failed {{ background: #3a2428; color: var(--bad); }}
    .status.running {{ background: #3b3323; color: var(--warn); }}
    .error {{ color: var(--bad); margin-top: 10px; }}
    footer {{ color: var(--muted); font-size: 12px; padding: 0 28px 28px; max-width: 1180px; margin: 0 auto; }}
    @media (max-width: 780px) {{
      .hero {{ flex-direction: column; }}
      .metrics {{ min-width: 0; grid-template-columns: repeat(2, 1fr); }}
      main {{ padding: 18px; }}
    }}
  </style>
</head>
<body>
  {body}
  <footer>Generated from {db_path} at {generated_at}</footer>
</body>
</html>
"""
    with open(out_path, "w") as f:
        f.write(html)
    print(f"Research dashboard generated: {out_path}")


if __name__ == "__main__":
    generate_research_dashboard()

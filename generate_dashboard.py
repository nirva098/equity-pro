import json
import os
import sqlite3
from datetime import datetime, timedelta
from core.feedback_loop import load_strategy_memory

RESEARCH_DB = "data/research.db"

def _load_recent_trades(db_path=RESEARCH_DB, days=30):
    """Load recent trade recommendations from research.db."""
    if not os.path.exists(db_path):
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            rows = conn.execute(
                """SELECT * FROM trade_recommendations
                   WHERE trade_date >= ?
                   ORDER BY trade_date DESC, id DESC LIMIT 100""",
                (cutoff,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def _load_daily_runs(db_path=RESEARCH_DB, days=30):
    """Load recent daily run summaries from research.db."""
    if not os.path.exists(db_path):
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            rows = conn.execute(
                "SELECT * FROM daily_runs WHERE date >= ? ORDER BY date DESC LIMIT 30",
                (cutoff,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def _parse_feedback(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}

def generate_dashboard():
    # Find the latest premarket report
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        print("No reports found.")
        return

    files = [f for f in os.listdir(reports_dir) if f.endswith("_premarket.json")]
    if not files:
        print("No premarket reports found.")
        return

    latest_report_path = os.path.join(reports_dir, sorted(files)[-1])
    with open(latest_report_path, 'r') as f:
        data = json.load(f)

    date = data.get('date', 'Unknown')
    market_context = data.get('market_context', {})
    trades = data.get('trades', [])
    thesis = data.get('thesis', {})
    active_setups = data.get('active_setups', [])
    risk_modifier = data.get('risk_modifier', 1.0)

    recent_trades = _load_recent_trades()
    daily_runs = _load_daily_runs()
    strategy_memory = load_strategy_memory()
    latest_feedback = _parse_feedback(daily_runs[0].get('feedback_json')) if daily_runs else {}

    # Build regime color
    regime = market_context.get('regime', 'risk_on')
    regime_color = {'risk_on': '#9ece6a', 'risk_off': '#f7768e', 'high_vix': '#e0af68'}.get(regime, '#7aa2f7')

    # Trade cards
    cards_html = ""
    for trade in trades:
        ticker = trade.get('ticker', 'N/A')
        t_info = thesis.get(ticker, {})
        t_thesis = t_info.get('thesis', '')
        confidence = trade.get('confidence', t_info.get('confidence', 0))
        rr = trade.get('expected_R', 0)
        score = trade.get('score', 0)

        cards_html += f"""
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="ticker">{ticker.replace('.NS','')}</div>
                    <span class="badge">{trade.get('setup','').replace('_',' ').upper()}</span>
                </div>
                <div class="confidence-ring" title="Conviction score">{score:.2f}</div>
            </div>
            <div class="stats">
                <div class="stat"><span class="stat-label">Entry</span><span class="stat-value">₹{trade.get('entry','—')}</span></div>
                <div class="stat"><span class="stat-label">Stop Loss</span><span class="stat-value red">₹{trade.get('sl','—')}</span></div>
                <div class="stat"><span class="stat-label">Target</span><span class="stat-value green">₹{trade.get('target','—')} <span class="target-src" title="Target source">[{trade.get('target_source','atr')}]</span></span></div>
                <div class="stat"><span class="stat-label">Qty</span><span class="stat-value">{trade.get('qty','—')}</span></div>
                <div class="stat"><span class="stat-label">Risk</span><span class="stat-value red">₹{trade.get('total_risk','—')}</span></div>
                <div class="stat"><span class="stat-label">R:R</span><span class="stat-value">{rr:.1f}x</span></div>
                <div class="stat"><span class="stat-label">Kelly f</span><span class="stat-value">{trade.get('kelly_f','—')}</span></div>
                <div class="stat"><span class="stat-label">Confidence</span><span class="stat-value">{confidence}/10</span></div>
            </div>
            {('<div class="thesis">' + t_thesis + '</div>') if t_thesis else ''}
        </div>"""

    # History rows
    history_rows = ""
    for t in recent_trades:
        pnl_r = t.get('pnl_R') or 0
        status = t.get('status', '')
        date_col = t.get('trade_date') or t.get('date', '')
        pnl_class = 'green' if pnl_r > 0 else ('red' if pnl_r < 0 else '')
        pnl_display = f"{pnl_r:+.2f}R" if status == 'closed' else '—'
        history_rows += f"""
        <tr>
            <td>{date_col}</td>
            <td><b>{t.get('ticker','').replace('.NS','')}</b></td>
            <td><span class="badge-sm">{t.get('setup','').replace('_',' ')}</span></td>
            <td>₹{t.get('entry','')}</td>
            <td class="red">₹{t.get('sl','')}</td>
            <td class="green">₹{t.get('target','')}</td>
            <td>{t.get('qty','')}</td>
            <td><span class="{pnl_class}">{pnl_display}</span></td>
            <td><span class="status-{status}">{status}</span></td>
        </tr>"""

    # Daily runs chart data
    chart_labels = json.dumps([r['date'] for r in reversed(daily_runs)])
    chart_r = json.dumps([round(r.get('total_R', 0), 2) for r in reversed(daily_runs)])
    chart_wr = json.dumps([round(r.get('win_rate', 0), 1) for r in reversed(daily_runs)])

    # Metrics
    total_closed = [t for t in recent_trades if t.get('status') == 'closed']
    total_wins = sum(1 for t in total_closed if (t.get('pnl_R') or 0) > 0)
    win_rate_30d = round((total_wins / len(total_closed)) * 100) if total_closed else 0
    total_r_30d = round(sum(t.get('pnl_R') or 0 for t in total_closed), 2)
    avg_r = round(total_r_30d / len(total_closed), 2) if total_closed else 0
    setup_rows = []
    for setup, info in (strategy_memory.get('setups', {}) or {}).items():
        setup_rows.append({
            "setup": setup,
            "weight": float(info.get("weight", 0.5) or 0.5),
            "trades": int(info.get("trades", 0) or 0),
            "wins": int(info.get("wins", 0) or 0),
        })
    setup_rows.sort(key=lambda row: row["weight"], reverse=True)
    feedback_rows = latest_feedback.get("setups", [])
    feedback_headline = latest_feedback.get("headline", "No EOD feedback captured yet.")
    feedback_actions = latest_feedback.get("next_cycle", ["Run an EOD cycle to generate nudges for tomorrow."])

    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M IST')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NSE Alpha Army — {date}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg: #0d0d12;
            --surface: #13131a;
            --card: #1a1a24;
            --border: #252535;
            --accent: #7aa2f7;
            --accent2: #bb9af7;
            --green: #9ece6a;
            --red: #f7768e;
            --yellow: #e0af68;
            --text: #c0caf5;
            --muted: #565f89;
            --mono: 'JetBrains Mono', monospace;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; }}

        /* NAV */
        nav {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 2rem; display: flex; align-items: center; justify-content: space-between; height: 56px; position: sticky; top: 0; z-index: 100; backdrop-filter: blur(12px); }}
        .nav-logo {{ font-weight: 700; font-size: 1rem; letter-spacing: 0.05em; color: var(--accent); }}
        .nav-links {{ display: flex; gap: 1.5rem; }}
        .nav-links a {{ color: var(--muted); text-decoration: none; font-size: 0.85rem; font-weight: 500; cursor: pointer; transition: color 0.2s; }}
        .nav-links a:hover, .nav-links a.active {{ color: var(--text); }}
        .nav-meta {{ font-family: var(--mono); font-size: 0.72rem; color: var(--muted); }}

        /* PAGES */
        .page {{ display: none; padding: 2rem; max-width: 1100px; margin: 0 auto; }}
        .page.active {{ display: block; }}

        /* REGIME BANNER */
        .regime-banner {{ background: var(--surface); border: 1px solid var(--border); border-left: 4px solid {regime_color}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 2rem; display: flex; align-items: center; gap: 2rem; flex-wrap: wrap; }}
        .regime-pill {{ font-family: var(--mono); font-size: 0.8rem; font-weight: 600; color: {regime_color}; background: {regime_color}20; padding: 4px 12px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.08em; }}
        .regime-stats {{ display: flex; gap: 2rem; flex-wrap: wrap; }}
        .regime-stat {{ font-size: 0.82rem; }}
        .regime-stat span {{ color: var(--muted); margin-right: 4px; }}
        .regime-narrative {{ color: var(--muted); font-size: 0.82rem; flex: 1; min-width: 200px; font-style: italic; }}
        .risk-mod {{ font-family: var(--mono); font-size: 0.8rem; color: {'var(--green)' if risk_modifier >= 1.0 else 'var(--yellow)'}; }}

        /* METRICS ROW */
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .metric {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.25rem; }}
        .metric-label {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.4rem; }}
        .metric-value {{ font-family: var(--mono); font-size: 1.5rem; font-weight: 600; }}
        .metric-value.green {{ color: var(--green); }}
        .metric-value.red {{ color: var(--red); }}
        .metric-value.accent {{ color: var(--accent); }}

        /* SECTION TITLE */
        .section-title {{ font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }}
        .section-title::after {{ content: ''; flex: 1; height: 1px; background: var(--border); }}

        /* TRADE CARDS */
        .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.25rem; margin-bottom: 2.5rem; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; transition: all 0.2s ease; }}
        .card:hover {{ border-color: var(--accent); transform: translateY(-3px); box-shadow: 0 8px 32px rgba(122,162,247,0.08); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }}
        .ticker {{ font-size: 1.3rem; font-weight: 700; letter-spacing: 0.02em; font-family: var(--mono); }}
        .badge {{ display: inline-block; background: var(--border); color: var(--accent2); padding: 3px 8px; border-radius: 5px; font-size: 0.68rem; font-weight: 600; letter-spacing: 0.05em; margin-top: 4px; }}
        .confidence-ring {{ width: 44px; height: 44px; border-radius: 50%; background: conic-gradient(var(--accent) 0%, var(--border) 0%); display: flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 0.72rem; font-weight: 600; border: 2px solid var(--border); flex-shrink: 0; }}
        .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem 1rem; }}
        .stat {{ display: flex; flex-direction: column; }}
        .stat-label {{ font-size: 0.68rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }}
        .stat-value {{ font-family: var(--mono); font-size: 0.9rem; font-weight: 500; margin-top: 1px; }}
        .stat-value.green {{ color: var(--green); }}
        .stat-value.red {{ color: var(--red); }}
        .thesis {{ font-size: 0.8rem; color: var(--muted); line-height: 1.6; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); font-style: italic; }}

        /* HISTORY TABLE */
        .table-wrap {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
        th {{ padding: 0.75rem 1rem; text-align: left; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border); }}
        td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); font-family: var(--mono); }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: var(--card); }}
        .badge-sm {{ background: var(--border); color: var(--muted); padding: 2px 6px; border-radius: 4px; font-size: 0.68rem; white-space: nowrap; }}
        .green {{ color: var(--green); }}
        .red {{ color: var(--red); }}
        .status-open {{ color: var(--yellow); }}
        .status-closed {{ color: var(--muted); }}

        /* CHART */
        .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }}
        .chart-title {{ font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 1.25rem; }}
        .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }}
        @media (max-width: 700px) {{ .charts-grid {{ grid-template-columns: 1fr; }} .cards {{ grid-template-columns: 1fr; }} .regime-stats {{ gap: 1rem; }} }}

        /* SETUP PILLS */
        .setups {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 2rem; }}
        .setup-pill {{ padding: 6px 14px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid var(--accent); color: var(--accent); background: rgba(122,162,247,0.08); }}
        .feedback-grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 1.25rem; margin-top: 1.5rem; }}
        .feedback-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }}
        .feedback-copy {{ color: var(--muted); font-size: 0.88rem; line-height: 1.6; margin-bottom: 1rem; }}
        .feedback-list {{ display: grid; gap: 0.85rem; }}
        .feedback-item {{ border: 1px solid var(--border); border-radius: 10px; padding: 0.9rem 1rem; background: var(--card); }}
        .feedback-item strong {{ font-family: var(--mono); }}
        .feedback-meta {{ font-family: var(--mono); font-size: 0.76rem; color: var(--muted); margin-top: 0.35rem; }}
        .nudge-lean_in {{ color: var(--green); }}
        .nudge-trim_risk {{ color: var(--red); }}
        .nudge-stay_patient {{ color: var(--yellow); }}
        .bullets {{ display: grid; gap: 0.7rem; color: var(--text); font-size: 0.88rem; }}
        .bullets div {{ padding-left: 1rem; position: relative; }}
        .bullets div::before {{ content: '•'; position: absolute; left: 0; color: var(--accent); }}

        /* EMPTY STATE */
        .empty {{ text-align: center; padding: 4rem 2rem; color: var(--muted); }}
        .empty-icon {{ font-size: 3rem; margin-bottom: 1rem; }}
    </style>
</head>
<body>
<nav>
    <div class="nav-logo">⚡ NSE ALPHA ARMY</div>
    <div class="nav-links">
        <a class="active" onclick="showPage('today', this)">Today</a>
        <a onclick="showPage('history', this)">History</a>
        <a onclick="showPage('performance', this)">Performance</a>
    </div>
    <div class="nav-meta">Updated {last_updated}</div>
</nav>

<!-- TODAY PAGE -->
<div id="page-today" class="page active">
    <div class="regime-banner">
        <span class="regime-pill">{regime.replace('_', ' ')}</span>
        <div class="regime-stats">
            <div class="regime-stat"><span>NIFTY</span><b>{market_context.get('nifty_close', 0):,.0f}</b></div>
            <div class="regime-stat"><span>VIX</span><b>{market_context.get('vix', 0):.1f}</b></div>
            <div class="regime-stat"><span>FII</span><b>₹{market_context.get('fii_net', 0):,.0f} Cr</b></div>
            <div class="regime-stat"><span>5d Ret</span><b>{market_context.get('nifty_5d_return', 0):+.2f}%</b></div>
        </div>
        <div class="regime-narrative">{market_context.get('regime_narrative', 'No narrative available.')}</div>
        <div class="risk-mod">Risk mod: {risk_modifier}x</div>
    </div>

    {'<div class="setups">' + ''.join(f'<span class="setup-pill">{s.replace("_"," ").title()}</span>' for s in active_setups) + '</div>' if active_setups else ''}

    <div class="section-title">Today's Signals — {date}</div>

    {'<div class="cards">' + cards_html + '</div>' if trades else '<div class="empty"><div class="empty-icon">📭</div><p>No trades generated today.</p></div>'}
</div>

<!-- HISTORY PAGE -->
<div id="page-history" class="page">
    <div class="section-title">Trade History — Last 30 Days</div>
    {'<div class="table-wrap"><table><thead><tr><th>Date</th><th>Ticker</th><th>Setup</th><th>Entry</th><th>SL</th><th>Target</th><th>Qty</th><th>PnL R</th><th>Status</th></tr></thead><tbody>' + history_rows + '</tbody></table></div>' if recent_trades else '<div class="empty"><div class="empty-icon">📊</div><p>No trade history yet.</p></div>'}
</div>

<!-- PERFORMANCE PAGE -->
<div id="page-performance" class="page">
    <div class="metrics">
        <div class="metric">
            <div class="metric-label">30d Win Rate</div>
            <div class="metric-value {'green' if win_rate_30d >= 50 else 'red'}">{win_rate_30d}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">30d Total R</div>
            <div class="metric-value {'green' if total_r_30d >= 0 else 'red'}">{total_r_30d:+.2f}R</div>
        </div>
        <div class="metric">
            <div class="metric-label">Avg R/Trade</div>
            <div class="metric-value {'green' if avg_r >= 0 else 'red'}">{avg_r:+.2f}R</div>
        </div>
        <div class="metric">
            <div class="metric-label">Trades Closed</div>
            <div class="metric-value accent">{len(total_closed)}</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <div class="chart-title">Daily P&L (R)</div>
            <canvas id="chartR" height="180"></canvas>
        </div>
        <div class="chart-card">
            <div class="chart-title">Win Rate %</div>
            <canvas id="chartWR" height="180"></canvas>
        </div>
    </div>

    <div class="feedback-grid">
        <div class="feedback-card">
            <div class="section-title">Feedback Loop</div>
            <div class="feedback-copy">{feedback_headline}</div>
            {('<div class="feedback-list">' + ''.join(
                f'<div class="feedback-item"><strong>{item.get("setup","").replace("_"," ")}</strong> '
                f'<span class="nudge-{item.get("nudge","stay_patient")}">{item.get("nudge","stay_patient").replace("_"," ")}</span>'
                f'<div class="feedback-meta">{item.get("trades",0)} trades | {item.get("win_rate",0)}% win rate | '
                f'{item.get("total_R",0):+.2f}R | weight {item.get("weight_before",0.5):.2f} → {item.get("weight_after",0.5):.2f}</div>'
                f'<div class="feedback-copy" style="margin:0.5rem 0 0;">{item.get("nudge_text","")}</div></div>'
                for item in feedback_rows
            ) + '</div>') if feedback_rows else '<div class="empty"><p>No setup-level feedback yet.</p></div>'}
        </div>
        <div class="feedback-card">
            <div class="section-title">Next Cycle Nudges</div>
            <div class="bullets">{''.join(f'<div>{item}</div>' for item in feedback_actions)}</div>
            <div class="section-title" style="margin-top:1.5rem;">Setup Weights</div>
            {('<div class="feedback-list">' + ''.join(
                f'<div class="feedback-item"><strong>{row["setup"].replace("_"," ")}</strong>'
                f'<div class="feedback-meta">weight {row["weight"]:.2f} | {row["wins"]}/{row["trades"]} wins</div></div>'
                for row in setup_rows
            ) + '</div>') if setup_rows else '<div class="empty"><p>No strategy memory yet.</p></div>'}
        </div>
    </div>
</div>

<script>
function showPage(id, el) {{
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
    document.getElementById('page-' + id).classList.add('active');
    el.classList.add('active');
}}

const labels = {chart_labels};
const rData = {chart_r};
const wrData = {chart_wr};

const chartDefaults = {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
        x: {{ grid: {{ color: '#252535' }}, ticks: {{ color: '#565f89', font: {{ size: 10 }} }} }},
        y: {{ grid: {{ color: '#252535' }}, ticks: {{ color: '#565f89', font: {{ size: 10 }} }} }}
    }}
}};

new Chart(document.getElementById('chartR'), {{
    type: 'bar',
    data: {{ labels, datasets: [{{ data: rData, backgroundColor: rData.map(v => v >= 0 ? '#9ece6a55' : '#f7768e55'), borderColor: rData.map(v => v >= 0 ? '#9ece6a' : '#f7768e'), borderWidth: 1, borderRadius: 4 }}] }},
    options: chartDefaults
}});

new Chart(document.getElementById('chartWR'), {{
    type: 'line',
    data: {{ labels, datasets: [{{ data: wrData, borderColor: '#7aa2f7', backgroundColor: '#7aa2f715', fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: '#7aa2f7' }}] }},
    options: {{ ...chartDefaults, scales: {{ ...chartDefaults.scales, y: {{ ...chartDefaults.scales.y, min: 0, max: 100 }} }} }}
}});
</script>
</body>
</html>"""

    # Write to docs/index.html for GitHub Pages
    os.makedirs("docs", exist_ok=True)
    out_path = "docs/index.html"
    with open(out_path, 'w') as f:
        f.write(html)
    print(f"Dashboard generated: {out_path}")

    # Also write dated archive
    archive_dir = "docs/history"
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, f"{date}.html")
    with open(archive_path, 'w') as f:
        f.write(html)
    print(f"Archive saved: {archive_path}")


if __name__ == "__main__":
    generate_dashboard()

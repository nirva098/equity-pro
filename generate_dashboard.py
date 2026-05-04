import json
import os
from datetime import datetime

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

    html_header = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NSE Alpha Army Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0a0a0c;
            --card-bg: #16161e;
            --accent: #7aa2f7;
            --text: #c0caf5;
            --text-dim: #9aa5ce;
            --green: #9ece6a;
            --red: #f7768e;
            --border: #292e42;
        }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 2rem;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
        }}
        h1 {{ margin: 0; font-weight: 700; color: var(--accent); }}
        .date {{ font-family: 'JetBrains Mono'; color: var(--text-dim); }}
        
        .market-context {{
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 2rem;
        }}
        .regime-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            background: var(--border);
            color: var(--accent);
            margin-bottom: 1rem;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: transform 0.2s;
        }}
        .card:hover {{
            transform: translateY(-4px);
            border-color: var(--accent);
        }}
        .ticker {{
            font-size: 1.4rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
            display: flex;
            justify-content: space-between;
        }}
        .setup {{
            font-size: 0.75rem;
            background: #24283b;
            padding: 2px 8px;
            border-radius: 4px;
            color: var(--text-dim);
        }}
        .thesis-text {{
            font-style: italic;
            color: var(--text-dim);
            font-size: 0.9rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }}
        .stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin-top: 1rem;
            font-family: 'JetBrains Mono';
            font-size: 0.85rem;
        }}
        .stat-label {{ color: var(--text-dim); }}
        .stat-value {{ color: var(--green); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>NSE ALPHA ARMY</h1>
            <div class="date">{date}</div>
        </header>

        <section class="market-context">
            <div class="regime-badge">{market_context.get('regime', 'N/A')}</div>
            <p>{market_context.get('regime_narrative', 'No market narrative available.')}</p>
            <div style="display: flex; gap: 2rem; font-size: 0.8rem; color: var(--text-dim);">
                <span>VIX: <b>{market_context.get('vix', 'N/A')}</b></span>
                <span>NIFTY: <b>{market_context.get('nifty_close', 'N/A')}</b></span>
                <span>FII Net: <b>{market_context.get('fii_net', 'N/A')} Cr</b></span>
            </div>
        </section>

        <h2>Daily Signals</h2>
        <div class="grid">
"""

    cards_html = ""
    for trade in trades:
        t_ticker = trade.get('ticker', 'N/A')
        t_setup = trade.get('setup', 'N/A')
        t_info = thesis.get(t_ticker, {})
        t_thesis = t_info.get('thesis', 'No research thesis available.')
        t_conf = t_info.get('confidence', 0)
        
        cards_html += f"""
            <div class="card">
                <div class="ticker">
                    {t_ticker}
                    <span class="setup">{t_setup}</span>
                </div>
                <div class="stats">
                    <span class="stat-label">Entry</span><span class="stat-value">₹{trade.get('entry')}</span>
                    <span class="stat-label">Stop Loss</span><span class="stat-value" style="color: var(--red)">₹{trade.get('sl')}</span>
                    <span class="stat-label">Target</span><span class="stat-value">₹{trade.get('target')}</span>
                    <span class="stat-label">Confidence</span><span class="stat-value">{t_conf}%</span>
                </div>
                <div class="thesis-text">
                    "{t_thesis}"
                </div>
            </div>
        """

    html_footer = """
        </div>
    </div>
</body>
</html>
"""

    dashboard_path = os.path.join(reports_dir, "dashboard.html")
    with open(dashboard_path, 'w') as f:
        f.write(html_header + cards_html + html_footer)
    print(f"Dashboard generated: {dashboard_path}")

if __name__ == "__main__":
    generate_dashboard()

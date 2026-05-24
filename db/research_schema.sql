CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    regime TEXT,
    risk_modifier REAL,
    active_setups_json TEXT,
    scanned_count INTEGER DEFAULT 0,
    candidates_count INTEGER DEFAULT 0,
    trades_count INTEGER DEFAULT 0,
    error TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS screen_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    setup TEXT NOT NULL,
    rank INTEGER NOT NULL,
    score REAL NOT NULL,
    expected_R REAL,
    hard_pass INTEGER DEFAULT 0,
    quant_reasons_json TEXT,
    fundamentals_json TEXT,
    technicals_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
);

CREATE TABLE IF NOT EXISTS trade_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    setup TEXT NOT NULL,
    rank INTEGER NOT NULL,
    entry REAL NOT NULL,
    sl REAL NOT NULL,
    target REAL NOT NULL,
    qty INTEGER NOT NULL,
    risk_per_share REAL,
    total_risk REAL,
    expected_R REAL,
    kelly_f REAL,
    score REAL,
    confidence INTEGER,
    catalyst TEXT,
    catalyst_type TEXT,
    news_sentiment TEXT,
    thesis TEXT,
    bear_case TEXT,
    quant_reasons_json TEXT,
    hard_pass INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'recommended',
    execution_price REAL,
    exit_price REAL,
    exit_time TEXT,
    pnl_R REAL,
    pnl_abs REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
);

CREATE TABLE IF NOT EXISTS research_briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    setup TEXT,
    bull_case TEXT,
    setup_fit_score INTEGER,
    quant_evidence_json TEXT,
    missing_data_json TEXT,
    must_verify_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
);

CREATE TABLE IF NOT EXISTS catalyst_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    catalyst_type TEXT,
    catalyst TEXT,
    catalyst_strength INTEGER,
    freshness TEXT,
    evidence_json TEXT,
    source_urls_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
);

CREATE TABLE IF NOT EXISTS skeptic_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    bear_case TEXT,
    red_flags_json TEXT,
    kill_trade INTEGER DEFAULT 0,
    risk_penalty REAL,
    invalidation TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
);

CREATE TABLE IF NOT EXISTS final_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    setup TEXT,
    rank INTEGER,
    decision TEXT NOT NULL,
    conviction REAL,
    why_now TEXT,
    why_this_over_others TEXT,
    position_bias TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
);

CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_research_runs_date ON research_runs(trade_date, run_type);
CREATE INDEX IF NOT EXISTS idx_screen_candidates_run ON screen_candidates(run_id, rank);
CREATE INDEX IF NOT EXISTS idx_trade_recommendations_run ON trade_recommendations(run_id, rank);
CREATE INDEX IF NOT EXISTS idx_trade_recommendations_date ON trade_recommendations(trade_date, ticker);
CREATE INDEX IF NOT EXISTS idx_research_briefs_run ON research_briefs(run_id, ticker);
CREATE INDEX IF NOT EXISTS idx_catalyst_checks_run ON catalyst_checks(run_id, ticker);
CREATE INDEX IF NOT EXISTS idx_skeptic_reviews_run ON skeptic_reviews(run_id, ticker);
CREATE INDEX IF NOT EXISTS idx_final_rankings_run ON final_rankings(run_id, rank);

CREATE TABLE IF NOT EXISTS daily_runs (
    date TEXT PRIMARY KEY,
    regime TEXT,
    trades_taken INTEGER,
    win_rate REAL,
    total_R REAL,
    journal_entry TEXT
);

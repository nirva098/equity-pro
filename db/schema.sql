CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    setup TEXT NOT NULL,
    entry REAL NOT NULL,
    sl REAL NOT NULL,
    target REAL NOT NULL,
    qty INTEGER NOT NULL,
    entry_time TEXT,
    exit_time TEXT,
    exit_price REAL,
    pnl_R REAL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_runs (
    date TEXT PRIMARY KEY,
    regime TEXT NOT NULL,
    trades_taken INTEGER NOT NULL,
    win_rate REAL,
    total_R REAL,
    journal_entry TEXT
);

import sqlite3
from datetime import datetime
from core.config import DB_PATH

def init_db():
    """Initializes the database schema from db/schema.sql"""
    with sqlite3.connect(DB_PATH) as conn:
        with open('db/schema.sql', 'r') as f:
            schema_script = f.read()
            conn.executescript(schema_script)
        conn.commit()

def log_trade(trade_data: dict):
    """Insert a new trade into the trades table with status 'open'."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO trades (date, ticker, setup, entry, sl, target, qty, entry_time, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                trade_data['ticker'],
                trade_data['setup'],
                trade_data['entry'],
                trade_data['sl'],
                trade_data['target'],
                trade_data['qty'],
                trade_data.get('entry_time', '09:15:00'),
                'open'
            )
        )
        conn.commit()

def get_open_trades(date: str = None) -> list:
    """Get all open trades, optionally filtered by date."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if date:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'open' AND date = ?", (date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'open'"
            ).fetchall()
        return [dict(row) for row in rows]

def update_trade_exit(trade_id: int, exit_price: float, pnl_R: float):
    """Update a trade with exit data and mark as closed."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """UPDATE trades SET exit_price = ?, exit_time = ?, pnl_R = ?, status = 'closed'
               WHERE id = ?""",
            (exit_price, datetime.now().strftime('%H:%M:%S'), pnl_R, trade_id)
        )
        conn.commit()

def log_daily_run(date: str, regime: str, trades_taken: int,
                  win_rate: float, total_R: float, journal_entry: str):
    """Insert or replace a daily run summary."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO daily_runs (date, regime, trades_taken, win_rate, total_R, journal_entry)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date, regime, trades_taken, win_rate, total_R, journal_entry)
        )
        conn.commit()

def get_closed_trades(date: str = None) -> list:
    """Get all closed trades, optionally filtered by date."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if date:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'closed' AND date = ?", (date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'closed'"
            ).fetchall()
        return [dict(row) for row in rows]

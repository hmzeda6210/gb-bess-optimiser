"""SQLite storage for price series, including the leakage-safe as-of query."""

from sqlalchemy import create_engine, text

DB_PATH = "sqlite:///gb_prices.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS price_series (
    series_id TEXT NOT NULL,
    settlement_datetime TEXT NOT NULL,
    settlement_date TEXT NOT NULL,
    settlement_period INTEGER NOT NULL,
    published_at TEXT NOT NULL,
    published_at_source TEXT NOT NULL,
    settlement_run_type TEXT NOT NULL DEFAULT 'n/a',
    value REAL NOT NULL,
    volume_mwh REAL,
    source TEXT NOT NULL,
    PRIMARY KEY (series_id, settlement_datetime, source)
);
"""

#Connect to the SQLite engine and ensure price_series table exists
def get_engine():
    engine = create_engine(DB_PATH)
    with engine.begin() as conn:
        conn.execute(text(SCHEMA))
    return engine


def insert_rows(engine, rows: list[dict]):
    """Idempotent upsert — safe to re-run for the same window."""
    with engine.begin() as conn:
        for row in rows:
            row = {**row, "settlement_run_type": row.get("settlement_run_type", "n/a")}
            conn.execute(text("""
                INSERT OR REPLACE INTO price_series
                (series_id, settlement_datetime, settlement_date, settlement_period,
                 published_at, published_at_source, settlement_run_type, value, volume_mwh, source)
                VALUES (:series_id, :settlement_datetime, :settlement_date, :settlement_period,
                        :published_at, :published_at_source, :settlement_run_type, :value, :volume_mwh, :source)
            """), row)

#Return only rows knowable at decision_moment, core leakage filter
def get_as_of(engine, series_id: str, decision_moment: str) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT settlement_datetime, settlement_period, value, published_at, published_at_source
            FROM price_series
            WHERE series_id = :series_id AND published_at <= :decision_moment
            ORDER BY settlement_datetime
        """), {"series_id": series_id, "decision_moment": decision_moment})
        return [dict(row._mapping) for row in result]
"""
One-time database migration script.

Adds columns that were introduced in later versions of the schema
but are missing from databases created with an older version.

Safe to run multiple times — skips columns that already exist.

Columns covered:
  alerts.repeating                    BOOLEAN NOT NULL DEFAULT 0
  trades.realized_pnl                 FLOAT   (nullable)
  agent_analysis.fundamentals_snapshot TEXT/JSON (nullable)
  agent_analysis.structured_output    TEXT/JSON (nullable)
  agent_analysis.target_review_date   TEXT      (nullable)
  agent_analysis.news_context         TEXT/JSON (nullable)

Usage (from repo root, with venv activated):
  python scripts/migrate_db.py
"""
import pathlib
import sqlite3

DB_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "portfolio.db"


def add_if_missing(cur: sqlite3.Cursor, table: str, column: str, col_type: str) -> None:
    existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"✓  Added {table}.{column}")
    else:
        print(f"–  {table}.{column} already present, skipping")


def migrate():
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}")
        print("Start the backend once first so it creates the DB, then re-run.")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ── alerts ────────────────────────────────────────────────────────────────
    add_if_missing(cur, "alerts", "repeating", "BOOLEAN NOT NULL DEFAULT 0")

    # ── trades ────────────────────────────────────────────────────────────────
    add_if_missing(cur, "trades", "realized_pnl", "FLOAT")

    # ── agent_analysis ────────────────────────────────────────────────────────
    add_if_missing(cur, "agent_analysis", "fundamentals_snapshot", "TEXT")
    add_if_missing(cur, "agent_analysis", "structured_output",     "TEXT")
    add_if_missing(cur, "agent_analysis", "target_review_date",    "TEXT")
    add_if_missing(cur, "agent_analysis", "news_context",          "TEXT")

    con.commit()
    con.close()
    print("\nMigration complete. Restart the backend.")


if __name__ == "__main__":
    migrate()

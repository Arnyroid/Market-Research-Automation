"""
One-time database migration script.

Adds columns that were introduced in later versions of the schema
but are missing from databases created with an older version:

  alerts.repeating       BOOLEAN NOT NULL DEFAULT 0
  trades.realized_pnl    FLOAT (nullable)

Safe to run multiple times — skips columns that already exist.

Usage (from repo root, with venv activated):
  python scripts/migrate_db.py
"""
import pathlib
import sqlite3

DB_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "portfolio.db"


def migrate():
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}")
        print("Start the backend once first so it creates the DB, then re-run.")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ── alerts.repeating ─────────────────────────────────────────────────────
    existing_alerts = {row[1] for row in cur.execute("PRAGMA table_info(alerts)")}
    if "repeating" not in existing_alerts:
        cur.execute("ALTER TABLE alerts ADD COLUMN repeating BOOLEAN NOT NULL DEFAULT 0")
        print("✓  Added alerts.repeating")
    else:
        print("–  alerts.repeating already present, skipping")

    # ── trades.realized_pnl ───────────────────────────────────────────────────
    existing_trades = {row[1] for row in cur.execute("PRAGMA table_info(trades)")}
    if "realized_pnl" not in existing_trades:
        cur.execute("ALTER TABLE trades ADD COLUMN realized_pnl FLOAT")
        print("✓  Added trades.realized_pnl")
    else:
        print("–  trades.realized_pnl already present, skipping")

    con.commit()
    con.close()
    print("\nMigration complete. Restart the backend.")


if __name__ == "__main__":
    migrate()

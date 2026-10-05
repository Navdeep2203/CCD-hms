"""Tiny forward-only SQL migration runner.

    python -m app.migrate            # apply pending migrations
    python -m app.migrate --seed     # ...and load demo data if the database is empty

Applied files are recorded in the schema_migrations table, so it is safe to run on every deploy.
"""
import logging
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.database import _conninfo

logger = logging.getLogger("migrate")
ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = Path(os.getenv("MIGRATIONS_DIR", ROOT / "database" / "migrations"))
SEED_FILE = Path(os.getenv("SEED_FILE", ROOT / "database" / "seed_demo.sql"))

# Databases created before this runner existed already contain these changes; detect and baseline them.
_PROBES = {
    "001_initial_schema.sql": "SELECT to_regclass('public.users') IS NOT NULL AS present",
    "002_improvements.sql": "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'no_overlapping_bookings') AS present",
}


def run(seed: bool = False) -> list[str]:
    applied_now: list[str] = []
    with psycopg.connect(_conninfo(), row_factory=dict_row, autocommit=False) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT now())")
        conn.commit()
        done = {row["filename"] for row in conn.execute("SELECT filename FROM schema_migrations")}
        baseline = not done
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            probe = _PROBES.get(path.name)
            if baseline and probe and conn.execute(probe).fetchone()["present"]:
                logger.info("baseline (already present): %s", path.name)
            else:
                logger.info("applying %s", path.name)
                conn.execute(path.read_text(encoding="utf-8"))
                applied_now.append(path.name)
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            conn.commit()
        if seed and SEED_FILE.exists():
            if conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0:
                logger.info("loading demo seed data")
                conn.execute(SEED_FILE.read_text(encoding="utf-8"))
                conn.commit()
            else:
                logger.info("users already exist; skipping seed")
    return applied_now


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(seed="--seed" in sys.argv)

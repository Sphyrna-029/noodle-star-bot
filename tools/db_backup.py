"""Simple SQLite backup utility for noodle_stars.db.

Usage examples:
  python tools/db_backup.py --tier 15m
  python tools/db_backup.py --tier hourly --db path/to/noodle_stars.db

This is standalone and not integrated into the bot. It uses sqlite3's
backup API to produce consistent copies. Short-term tiers (15m, hourly,
3h) keep only the latest copy; daily backups are retained indefinitely.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys


TIERS = {
    "15m": "15min",
    "hourly": "hourly",
    "3h": "3hour",
    "daily": "daily",
}


def iso_timestamp_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def remove_old_short_term(backups_dir: Path, tier_dir: str, keep: Path) -> None:
    """Remove old .db files for short-term tiers, keeping the file at *keep*."""
    d = backups_dir / tier_dir
    if not d.exists():
        return
    for f in d.iterdir():
        if f.is_file() and f.suffix == ".db" and f != keep:
            try:
                f.unlink()
            except Exception:
                pass


def backup_sqlite(db_path: Path, dest_path: Path) -> None:
    """Perform a consistent SQLite backup using the backup API."""
    # Open source and destination connections
    src = sqlite3.connect(str(db_path))
    dest = sqlite3.connect(str(dest_path))
    try:
        with dest:
            src.backup(dest)
    finally:
        try:
            dest.close()
        except Exception:
            pass
        try:
            src.close()
        except Exception:
            pass


def integrity_check(db_path: Path) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("PRAGMA integrity_check;")
        row = cur.fetchone()
        return row is not None and row[0] == "ok"
    finally:
        conn.close()


def make_backup(db_path: str, tier: str, backups_root: str = "backups") -> int:
    db = Path(db_path)
    if not db.exists():
        print(f"Source DB not found: {db}")
        return 2

    if tier not in TIERS:
        print(f"Unknown tier: {tier}")
        return 3

    backups_dir = Path(backups_root)
    tier_dir = TIERS[tier]
    ensure_dir(backups_dir / tier_dir)

    ts = iso_timestamp_now()
    dest_name = f"{db.stem}.{ts}.{tier}.db"
    dest_path = backups_dir / tier_dir / dest_name

    print(f"Backing up {db} -> {dest_path}")
    try:
        backup_sqlite(db, dest_path)
    except Exception as e:
        print("Backup failed:", e)
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception:
                pass
        return 4

    ok = integrity_check(dest_path)
    if not ok:
        print("Integrity check failed for backup; removing file.")
        try:
            dest_path.unlink()
        except Exception:
            pass
        return 5

    # For short-term tiers, remove old backups now that the new one is verified
    if tier != "daily":
        remove_old_short_term(backups_dir, tier_dir, keep=dest_path)

    print("Backup successful:", dest_path)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create a safe SQLite backup for noodle_stars.db")
    p.add_argument("--tier", "-t", required=True, choices=list(TIERS.keys()),
                   help="Backup tier: 15m, hourly, 3h, or daily")
    p.add_argument("--db", default="noodle_stars.db", help="Path to source SQLite DB")
    p.add_argument("--out", default="backups", help="Backups root directory")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    return make_backup(args.db, args.tier, args.out)


if __name__ == "__main__":
    sys.exit(main())

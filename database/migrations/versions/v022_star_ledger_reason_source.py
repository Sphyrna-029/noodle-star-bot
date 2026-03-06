"""
Add source/reason metadata fields to star_ledger for better attribution.
"""

DESCRIPTION = "Add source and reason fields to star_ledger"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    """Apply the migration."""
    if not _column_exists(cursor, "star_ledger", "source"):
        cursor.execute(
            "ALTER TABLE star_ledger ADD COLUMN source TEXT NOT NULL DEFAULT 'unknown'"
        )
    if not _column_exists(cursor, "star_ledger", "reason"):
        cursor.execute(
            "ALTER TABLE star_ledger ADD COLUMN reason TEXT NOT NULL DEFAULT 'unknown'"
        )


def downgrade(cursor) -> None:
    """Rollback the migration."""
    if _column_exists(cursor, "star_ledger", "source"):
        cursor.execute("ALTER TABLE star_ledger DROP COLUMN source")
    if _column_exists(cursor, "star_ledger", "reason"):
        cursor.execute("ALTER TABLE star_ledger DROP COLUMN reason")

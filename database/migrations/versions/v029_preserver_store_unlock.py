"""Add preserver ownership column for store-based unlock."""

DESCRIPTION = "Add preserver ownership column"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    """Add preserver ownership flag."""
    if not _column_exists(cursor, "user_inventory", "preserver_owned"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN preserver_owned INTEGER DEFAULT 0
            """
        )


def downgrade(cursor) -> None:
    """No-op downgrade for SQLite compatibility."""
    return None

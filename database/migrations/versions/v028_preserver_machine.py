"""Add preserver machine state columns to user inventory."""

DESCRIPTION = "Add preserver machine columns"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    """Add columns used by the farming preserver machine."""
    if not _column_exists(cursor, "user_inventory", "preserver_level"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN preserver_level INTEGER DEFAULT 0
            """
        )

    if not _column_exists(cursor, "user_inventory", "preserver_pending_stars"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN preserver_pending_stars INTEGER DEFAULT 0
            """
        )

    if not _column_exists(cursor, "user_inventory", "preserver_ready_ts"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN preserver_ready_ts INTEGER DEFAULT 0
            """
        )


def downgrade(cursor) -> None:
    """No-op downgrade for SQLite compatibility."""
    # SQLite DROP COLUMN support is inconsistent across environments.
    return None

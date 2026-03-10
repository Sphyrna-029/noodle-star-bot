"""Add GrowBot ownership and level columns."""

DESCRIPTION = "Add growbot ownership and level columns"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    """Add GrowBot columns to user inventory."""
    if not _column_exists(cursor, "user_inventory", "growbot_owned"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN growbot_owned INTEGER DEFAULT 0
            """
        )

    if not _column_exists(cursor, "user_inventory", "growbot_level"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN growbot_level INTEGER DEFAULT 0
            """
        )


def downgrade(cursor) -> None:
    """No-op downgrade for SQLite compatibility."""
    return None

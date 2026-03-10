"""Add location tracking columns to user_activity."""

DESCRIPTION = "Add current_location and last_travel to user_activity"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    if not _column_exists(cursor, "user_activity", "current_location"):
        cursor.execute(
            """
            ALTER TABLE user_activity
            ADD COLUMN current_location TEXT DEFAULT 'noodle_town'
            """
        )
    if not _column_exists(cursor, "user_activity", "last_travel"):
        cursor.execute(
            """
            ALTER TABLE user_activity
            ADD COLUMN last_travel TEXT
            """
        )


def downgrade(cursor) -> None:
    pass

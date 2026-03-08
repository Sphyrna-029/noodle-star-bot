"""Add optional pet nickname column."""

DESCRIPTION = "Add pet nickname support"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    """Add nickname field for user pets."""
    if not _column_exists(cursor, "user_pets", "pet_nickname"):
        cursor.execute(
            """
            ALTER TABLE user_pets
            ADD COLUMN pet_nickname TEXT
            """
        )


def downgrade(cursor) -> None:
    """No-op downgrade for SQLite compatibility."""
    pass

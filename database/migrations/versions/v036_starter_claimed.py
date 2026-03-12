"""Add starter_claimed flag to user_progression."""

DESCRIPTION = "Add starter_claimed column to user_progression"


def upgrade(cursor) -> None:
    cursor.execute(
        "ALTER TABLE user_progression ADD COLUMN starter_claimed INTEGER NOT NULL DEFAULT 0"
    )


def downgrade(cursor) -> None:
    # SQLite doesn't support DROP COLUMN before 3.35; recreate would be needed.
    pass

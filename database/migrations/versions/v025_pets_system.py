"""Add Tamagotchi-style pets table."""

DESCRIPTION = "Add user pets table for adoption and care"


def upgrade(cursor) -> None:
    """Create user_pets table and indexes."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pet_key TEXT NOT NULL,
            pet_name TEXT NOT NULL,
            pet_nickname TEXT,
            hunger INTEGER NOT NULL DEFAULT 100,
            cleanliness INTEGER NOT NULL DEFAULT 100,
            happiness INTEGER NOT NULL DEFAULT 100,
            adopted_at TEXT NOT NULL,
            last_care_at TEXT,
            last_decay_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, pet_key)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_pets_user_id
        ON user_pets(user_id)
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_pets_single_active
        ON user_pets(user_id)
        WHERE is_active = 1
        """
    )


def downgrade(cursor) -> None:
    """Drop pet data tables/indexes."""
    cursor.execute("DROP INDEX IF EXISTS idx_user_pets_single_active")
    cursor.execute("DROP INDEX IF EXISTS idx_user_pets_user_id")
    cursor.execute("DROP TABLE IF EXISTS user_pets")

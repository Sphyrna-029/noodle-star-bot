"""
Migration v021: Add persistent user achievements and progress tracking.

Creates:
- user_achievements: permanent unlock records with timestamps
- user_achievement_progress: lifetime counters for achievement progress
"""

VERSION = "v021"
DESCRIPTION = "Add persistent user achievements and progress tables"


def upgrade(cursor):
    """Create achievement tables and indexes."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER NOT NULL,
            achievement_key TEXT NOT NULL,
            unlocked_at TEXT NOT NULL,
            PRIMARY KEY (user_id, achievement_key)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_achievement_progress (
            user_id INTEGER NOT NULL,
            progress_key TEXT NOT NULL,
            value INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, progress_key)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_achievements_user
        ON user_achievements(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_achievement_progress_user
        ON user_achievement_progress(user_id)
        """
    )


def downgrade(cursor):
    """Drop achievement tables."""
    cursor.execute("DROP INDEX IF EXISTS idx_user_achievement_progress_user")
    cursor.execute("DROP INDEX IF EXISTS idx_user_achievements_user")
    cursor.execute("DROP TABLE IF EXISTS user_achievement_progress")
    cursor.execute("DROP TABLE IF EXISTS user_achievements")

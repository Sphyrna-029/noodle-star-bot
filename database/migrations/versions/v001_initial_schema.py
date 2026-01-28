"""
Initial database schema for Noodle Star Bot.

Creates the noodle_stars table with all columns from the original bot.py.
Uses IF NOT EXISTS to handle existing databases gracefully.
"""

DESCRIPTION = "Initial schema with noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS noodle_stars (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            stars INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            last_mine TEXT,
            gold_pickaxe INTEGER DEFAULT 0,
            helmet INTEGER DEFAULT 0,
            sword INTEGER DEFAULT 0,
            raw_potato INTEGER DEFAULT 0,
            golden_mushroom INTEGER DEFAULT 0,
            telescope INTEGER DEFAULT 0
        )
    """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute("DROP TABLE IF EXISTS noodle_stars")

"""
Migration v010: Add blackjack cooldown column.

Adds last_blackjack column to track cooldown for blackjack games.
"""

VERSION = "v010"
DESCRIPTION = "Add blackjack cooldown"


def upgrade(cursor):
    """Add the last_blackjack column."""
    cursor.execute(
        """
        ALTER TABLE noodle_stars ADD COLUMN last_blackjack TEXT
        """
    )


def downgrade(cursor):
    """Remove the last_blackjack column (SQLite doesn't support DROP COLUMN easily)."""
    # SQLite doesn't support DROP COLUMN in older versions
    # This would require recreating the table, so we'll leave it as a no-op
    pass

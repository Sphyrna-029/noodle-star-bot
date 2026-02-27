"""
Migration v014: Add bank insurance column.

Adds bank_insurance column to track uses of bank protection item.
"""

VERSION = "v014"
DESCRIPTION = "Add bank insurance item"


def upgrade(cursor):
    """Add the bank_insurance column."""
    cursor.execute(
        """
        ALTER TABLE user_inventory ADD COLUMN bank_insurance INTEGER DEFAULT 0
        """
    )


def downgrade(cursor):
    """Remove the bank_insurance column (SQLite doesn't support DROP COLUMN easily)."""
    # SQLite doesn't support DROP COLUMN in older versions
    # This would require recreating the table, so we'll leave it as a no-op
    pass

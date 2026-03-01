"""
Migration v019: Add farm level progression column.

Adds farm_level to user_inventory for farming quality progression.
"""

VERSION = "v019"
DESCRIPTION = "Add farm level progression"


def upgrade(cursor):
    """Add farm_level column to user_inventory."""
    cursor.execute(
        """
        ALTER TABLE user_inventory ADD COLUMN farm_level INTEGER DEFAULT 1
        """
    )


def downgrade(cursor):
    """Remove farm_level column (SQLite doesn't support DROP COLUMN easily)."""
    pass

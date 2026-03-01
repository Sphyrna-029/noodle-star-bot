"""
Migration v018: Add space mining columns.

Adds rocket_ship, space_planet_level, and active_space_planet columns
to user_inventory for the space mining system.
"""

VERSION = "v018"
DESCRIPTION = "Add space mining columns"


def upgrade(cursor):
    """Add space mining columns to user_inventory."""
    cursor.execute(
        """
        ALTER TABLE user_inventory ADD COLUMN rocket_ship INTEGER DEFAULT 0
        """
    )
    cursor.execute(
        """
        ALTER TABLE user_inventory ADD COLUMN space_planet_level INTEGER DEFAULT 0
        """
    )
    cursor.execute(
        """
        ALTER TABLE user_inventory ADD COLUMN active_space_planet INTEGER DEFAULT 0
        """
    )


def downgrade(cursor):
    """Remove space mining columns (SQLite doesn't support DROP COLUMN easily)."""
    pass

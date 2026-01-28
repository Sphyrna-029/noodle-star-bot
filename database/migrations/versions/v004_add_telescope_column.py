"""
Add telescope column to noodle_stars table.

This migration adds the telescope column to support the new telescope item
that users can purchase and use to generate starfields.
"""

DESCRIPTION = "Add telescope column to noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    # Add telescope column to existing table
    cursor.execute("""
        ALTER TABLE noodle_stars
        ADD COLUMN IF NOT EXISTS telescope INTEGER DEFAULT 0
    """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    # Remove telescope column from table
    cursor.execute("""
        ALTER TABLE noodle_stars
        DROP COLUMN IF EXISTS telescope
    """)
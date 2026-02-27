"""Add weather bonus multiplier to planted crops.

This supports farming weather events that boost harvest yields.
"""


def upgrade(cursor):
    """Add weather_bonus column to planted_crops table."""
    cursor.execute("""
        ALTER TABLE planted_crops
        ADD COLUMN weather_bonus REAL DEFAULT 1.0
    """)


def downgrade(cursor):
    """Remove weather_bonus column."""
    cursor.execute("""
        ALTER TABLE planted_crops
        DROP COLUMN weather_bonus
    """)

"""Add first_weather_bonus flag to track beginner farmer bonus.

This supports giving new farmers a guaranteed weather event.
"""


def upgrade(cursor):
    """Add first_weather_bonus column to user_inventory table."""
    cursor.execute("""
        ALTER TABLE user_inventory
        ADD COLUMN first_weather_bonus INTEGER DEFAULT 0
    """)


def downgrade(cursor):
    """Remove first_weather_bonus column."""
    cursor.execute("""
        ALTER TABLE user_inventory
        DROP COLUMN first_weather_bonus
    """)

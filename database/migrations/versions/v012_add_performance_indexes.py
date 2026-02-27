"""
Add targeted indexes for common query patterns after normalization.
"""

DESCRIPTION = "Add performance indexes for leaderboard queries"


def upgrade(cursor) -> None:
    """Apply the migration."""
    # Leaderboard sorts by stars in ascending/descending order.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_noodle_stars_stars
        ON noodle_stars(stars)
    """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute("DROP INDEX IF EXISTS idx_noodle_stars_stars")

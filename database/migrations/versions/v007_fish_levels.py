"""
Add active_fish_level column to noodle_stars table.

Fishing levels share the mining unlock progression (mine_level),
but need a separate active level since a player might mine at level 3
but fish at level 1.
"""

DESCRIPTION = "Add active_fish_level column to noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute(
        "SELECT name FROM pragma_table_info('noodle_stars') WHERE name='active_fish_level'"
    )
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN active_fish_level INTEGER DEFAULT 1
        """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute(
        "SELECT name FROM pragma_table_info('noodle_stars') WHERE name='active_fish_level'"
    )
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN active_fish_level")

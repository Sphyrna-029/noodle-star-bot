"""
Add mine level columns to noodle_stars table.

This migration adds mine_level (highest unlocked) and active_mine_level
(currently selected) columns to support the multi-level mine system.
"""

DESCRIPTION = "Add mine level columns to noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='mine_level'")
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN mine_level INTEGER DEFAULT 1
        """)

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='active_mine_level'")
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN active_mine_level INTEGER DEFAULT 1
        """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='mine_level'")
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN mine_level")

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='active_mine_level'")
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN active_mine_level")

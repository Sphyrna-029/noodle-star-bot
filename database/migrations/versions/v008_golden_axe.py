"""
Add golden_axe column to noodle_stars table.

The golden axe is a rare drop from legendary fishing catches (1% chance).
It has 50 uses and protects against sword-type hazards in both fishing and mining.
The column stores remaining uses (0 = none, 50 = fresh).
"""

DESCRIPTION = "Add golden_axe column to noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute(
        "SELECT name FROM pragma_table_info('noodle_stars') WHERE name='golden_axe'"
    )
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN golden_axe INTEGER DEFAULT 0
        """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute(
        "SELECT name FROM pragma_table_info('noodle_stars') WHERE name='golden_axe'"
    )
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN golden_axe")

"""
Add mithril_shield column to noodle_stars table.

The mithril shield is a rare drop from any fishing catch (0.1% chance).
It has 10 uses and protects against helmet-type hazards in both fishing and mining.
The column stores remaining uses (0 = none, 10 = fresh).
"""

DESCRIPTION = "Add mithril_shield column to noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute(
        "SELECT name FROM pragma_table_info('noodle_stars') WHERE name='mithril_shield'"
    )
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN mithril_shield INTEGER DEFAULT 0
        """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute(
        "SELECT name FROM pragma_table_info('noodle_stars') WHERE name='mithril_shield'"
    )
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN mithril_shield")

"""
Add duel stamina fields to noodle_stars table.

Adds stamina tracking columns to support duel stamina costs and regeneration.
"""

DESCRIPTION = "Add duel stamina fields to noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='stamina'")
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN stamina INTEGER DEFAULT 100
        """)

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='stamina_last_updated'")
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN stamina_last_updated TEXT
        """)

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='stamina_last_reset'")
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN stamina_last_reset TEXT
        """)

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='last_duel_amount'")
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN last_duel_amount INTEGER DEFAULT 0
        """)

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='last_duel_at'")
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN last_duel_at TEXT
        """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='stamina'")
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN stamina")

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='stamina_last_updated'")
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN stamina_last_updated")

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='stamina_last_reset'")
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN stamina_last_reset")

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='last_duel_amount'")
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN last_duel_amount")

    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='last_duel_at'")
    if cursor.fetchone():
        cursor.execute("ALTER TABLE noodle_stars DROP COLUMN last_duel_at")

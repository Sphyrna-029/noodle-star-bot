"""
Add telescope column to noodle_stars table.

This migration adds the telescope column to support the new telescope item
that users can purchase and use to generate starfields.
"""

DESCRIPTION = "Add telescope column to noodle_stars table"


def upgrade(cursor) -> None:
    """Apply the migration."""
    # Check if column already exists
    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='telescope'")
    result = cursor.fetchone()

    # Only add column if it doesn't exist
    if not result:
        cursor.execute("""
            ALTER TABLE noodle_stars
            ADD COLUMN telescope INTEGER DEFAULT 0
        """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    # Check if column exists before dropping
    cursor.execute("SELECT name FROM pragma_table_info('noodle_stars') WHERE name='telescope'")
    result = cursor.fetchone()

    # Only drop column if it exists
    if result:
        cursor.execute("""
            ALTER TABLE noodle_stars
            DROP COLUMN telescope
        """)
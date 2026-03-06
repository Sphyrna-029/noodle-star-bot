"""
Migration v020: Add columns for rare effect items to user_inventory.

Mining drops: rune_fragment (5 uses), fossilized_noodle (5 uses)
Fishing drops: bucktail_jig (count), jig_active (flag), ray_gun (2 uses),
               star_magnet (20 uses), lucky_charm (50 uses),
               heart_of_leviathan (1 use)
"""

VERSION = "v020"
DESCRIPTION = "Add rare effect item columns to user_inventory"

_COLUMNS = (
    ("rune_fragment", "INTEGER DEFAULT 0"),
    ("fossilized_noodle", "INTEGER DEFAULT 0"),
    ("bucktail_jig", "INTEGER DEFAULT 0"),
    ("jig_active", "INTEGER DEFAULT 0"),
    ("ray_gun", "INTEGER DEFAULT 0"),
    ("star_magnet", "INTEGER DEFAULT 0"),
    ("lucky_charm", "INTEGER DEFAULT 0"),
    ("heart_of_leviathan", "INTEGER DEFAULT 0"),
)


def upgrade(cursor):
    """Add rare effect item columns."""
    for col_name, col_type in _COLUMNS:
        cursor.execute(
            f"SELECT name FROM pragma_table_info('user_inventory') WHERE name='{col_name}'"
        )
        if not cursor.fetchone():
            cursor.execute(
                f"ALTER TABLE user_inventory ADD COLUMN {col_name} {col_type}"
            )


def downgrade(cursor):
    """Rollback — SQLite doesn't easily support DROP COLUMN."""
    pass

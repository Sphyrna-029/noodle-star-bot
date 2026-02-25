"""
Add fishing system tables and columns.

Adds bait inventory columns (worm, herring, sturgeon),
equipped_bait for tracking selected bait, and last_fish for cooldown.
"""

DESCRIPTION = "Add fishing system columns"


def upgrade(cursor) -> None:
    """Apply the migration."""
    # Add bait inventory columns
    cursor.execute("""
        ALTER TABLE noodle_stars ADD COLUMN bait_worm INTEGER DEFAULT 0
    """)
    cursor.execute("""
        ALTER TABLE noodle_stars ADD COLUMN bait_herring INTEGER DEFAULT 0
    """)
    cursor.execute("""
        ALTER TABLE noodle_stars ADD COLUMN bait_sturgeon INTEGER DEFAULT 0
    """)
    # Equipped bait (NULL = none, 'worm', 'herring', 'sturgeon')
    cursor.execute("""
        ALTER TABLE noodle_stars ADD COLUMN equipped_bait TEXT
    """)
    # Last fishing attempt timestamp for cooldown
    cursor.execute("""
        ALTER TABLE noodle_stars ADD COLUMN last_fish TEXT
    """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    # SQLite doesn't support DROP COLUMN directly in older versions
    # We need to recreate the table without the columns
    cursor.execute("""
        CREATE TABLE noodle_stars_backup (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            stars INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            stamina INTEGER DEFAULT 100,
            stamina_last_updated TEXT,
            stamina_last_reset TEXT,
            last_duel_amount INTEGER DEFAULT 0,
            last_duel_at TEXT,
            last_mine TEXT,
            gold_pickaxe INTEGER DEFAULT 0,
            helmet INTEGER DEFAULT 0,
            sword INTEGER DEFAULT 0,
            raw_potato INTEGER DEFAULT 0,
            golden_mushroom INTEGER DEFAULT 0,
            last_deposit TEXT,
            last_withdraw TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO noodle_stars_backup
        SELECT user_id, username, stars, bank, stamina, stamina_last_updated,
               stamina_last_reset, last_duel_amount, last_duel_at, last_mine,
               gold_pickaxe, helmet, sword, raw_potato, golden_mushroom,
               last_deposit, last_withdraw
        FROM noodle_stars
    """)
    cursor.execute("DROP TABLE noodle_stars")
    cursor.execute("ALTER TABLE noodle_stars_backup RENAME TO noodle_stars")

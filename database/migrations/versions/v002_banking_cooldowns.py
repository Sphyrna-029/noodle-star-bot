"""
Add banking cooldown columns for deposit and withdraw.

Adds last_deposit and last_withdraw columns to track when users
last performed each banking action.
"""

DESCRIPTION = "Add banking cooldown columns"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute("""
        ALTER TABLE noodle_stars ADD COLUMN last_deposit TEXT
    """)
    cursor.execute("""
        ALTER TABLE noodle_stars ADD COLUMN last_withdraw TEXT
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
            last_mine TEXT,
            gold_pickaxe INTEGER DEFAULT 0,
            helmet INTEGER DEFAULT 0,
            sword INTEGER DEFAULT 0,
            raw_potato INTEGER DEFAULT 0,
            golden_mushroom INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        INSERT INTO noodle_stars_backup
        SELECT user_id, username, stars, bank, last_mine,
               gold_pickaxe, helmet, sword, raw_potato, golden_mushroom
        FROM noodle_stars
    """)
    cursor.execute("DROP TABLE noodle_stars")
    cursor.execute("ALTER TABLE noodle_stars_backup RENAME TO noodle_stars")

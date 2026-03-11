"""Combat system — progression columns, combat log, and crafting recipes.

Adds combat-related columns to user_progression:
- HP/stamina tracking with timestamps for passive regen
- Combat level and active dungeon level
- Equipped weapon, shield, and armor keys

Creates combat_log table for tracking battle history.
"""

DESCRIPTION = "Combat system: HP, stamina, combat level, equipment slots, combat log"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


# Columns to add to user_progression
_NEW_PROGRESSION_COLUMNS = [
    ("current_hp", "INTEGER NOT NULL DEFAULT 100"),
    ("max_hp", "INTEGER NOT NULL DEFAULT 100"),
    ("hp_updated_at", "TEXT"),
    ("current_stamina", "INTEGER NOT NULL DEFAULT 50"),
    ("max_stamina", "INTEGER NOT NULL DEFAULT 50"),
    ("stamina_updated_at", "TEXT"),
    ("combat_level", "INTEGER NOT NULL DEFAULT 0"),
    ("active_combat_level", "INTEGER NOT NULL DEFAULT 1"),
    ("equipped_weapon", "TEXT"),
    ("equipped_shield", "TEXT"),
    ("equipped_armor", "TEXT"),
]


def upgrade(cursor) -> None:
    # ── 1. Add combat columns to user_progression ──────────────
    for col_name, col_type in _NEW_PROGRESSION_COLUMNS:
        if not _column_exists(cursor, "user_progression", col_name):
            cursor.execute(
                f"ALTER TABLE user_progression ADD COLUMN {col_name} {col_type}"
            )

    # ── 2. Create combat_log table ─────────────────────────────
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS combat_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            dungeon_level   INTEGER NOT NULL,
            mob_key         TEXT    NOT NULL,
            result          TEXT    NOT NULL,
            stars_change    INTEGER NOT NULL DEFAULT 0,
            items_lost      TEXT,
            equipment_lost  TEXT,
            bank_loss       INTEGER NOT NULL DEFAULT 0,
            fought_at       TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_combat_log_user
        ON combat_log(user_id)
        """
    )


def downgrade(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS combat_log")
    # SQLite doesn't support DROP COLUMN before 3.35.0;
    # the columns will simply be ignored if not used.

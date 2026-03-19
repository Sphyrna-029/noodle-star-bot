"""Add Aetherdepths dungeon system — progression fields, stash, PvP log, daily modifier."""

DESCRIPTION = "Add Aetherdepths dungeon tables and progression fields"


def upgrade(cursor) -> None:
    # Add aether progression columns to user_progression
    for col, default in [
        ("aether_level", 0),
        ("active_aether_level", 0),
        ("aether_active", 0),
    ]:
        try:
            cursor.execute(
                f"ALTER TABLE user_progression ADD COLUMN {col} INTEGER NOT NULL DEFAULT {default}"
            )
        except Exception:
            pass  # column already exists

    # Aether stash — items protected from death penalties
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aether_stash (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_key TEXT NOT NULL,
            category TEXT NOT NULL,
            base_sell_value INTEGER NOT NULL DEFAULT 0,
            stashed_at TEXT NOT NULL
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_aether_stash_user ON aether_stash (user_id)"
    )

    # PvP combat log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pvp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER NOT NULL,
            defender_id INTEGER NOT NULL,
            aether_level INTEGER NOT NULL,
            result TEXT NOT NULL,
            attacker_stars_change INTEGER NOT NULL DEFAULT 0,
            defender_stars_change INTEGER NOT NULL DEFAULT 0,
            fought_at TEXT NOT NULL
        )
    """)

    # Daily modifier (single-row table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aether_daily_modifier (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            modifier_key TEXT,
            active_date TEXT,
            rolled_at TEXT
        )
    """)
    cursor.execute(
        "INSERT OR IGNORE INTO aether_daily_modifier (id) VALUES (1)"
    )


def downgrade(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS aether_daily_modifier")
    cursor.execute("DROP TABLE IF EXISTS pvp_log")
    cursor.execute("DROP TABLE IF EXISTS aether_stash")
    # SQLite doesn't support DROP COLUMN easily; leave columns in place

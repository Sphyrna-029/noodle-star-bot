"""
Normalize per-user feature data into dedicated tables.

Splits the overloaded noodle_stars table into:
- noodle_stars: core identity/economy fields
- user_inventory: items, bait, progression selectors
- user_activity: cooldowns and combat/activity state
"""

DESCRIPTION = "Normalize noodle_stars into core/inventory/activity tables"


def _table_has_column(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info('{table}')")
    return any(row["name"] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_inventory (
            user_id INTEGER PRIMARY KEY,
            gold_pickaxe INTEGER DEFAULT 0,
            helmet INTEGER DEFAULT 0,
            sword INTEGER DEFAULT 0,
            raw_potato INTEGER DEFAULT 0,
            golden_mushroom INTEGER DEFAULT 0,
            bait_worm INTEGER DEFAULT 0,
            bait_herring INTEGER DEFAULT 0,
            bait_sturgeon INTEGER DEFAULT 0,
            equipped_bait TEXT,
            telescope INTEGER DEFAULT 0,
            mine_level INTEGER DEFAULT 1,
            active_mine_level INTEGER DEFAULT 1,
            active_fish_level INTEGER DEFAULT 1,
            golden_axe INTEGER DEFAULT 0,
            mithril_shield INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            user_id INTEGER PRIMARY KEY,
            stamina INTEGER DEFAULT 100,
            stamina_last_updated TEXT,
            stamina_last_reset TEXT,
            last_duel_amount INTEGER DEFAULT 0,
            last_duel_at TEXT,
            last_mine TEXT,
            last_deposit TEXT,
            last_withdraw TEXT,
            last_fish TEXT,
            last_blackjack TEXT
        )
    """)

    if _table_has_column(cursor, "noodle_stars", "gold_pickaxe"):
        cursor.execute("""
            INSERT OR IGNORE INTO user_inventory (
                user_id, gold_pickaxe, helmet, sword, raw_potato, golden_mushroom,
                bait_worm, bait_herring, bait_sturgeon, equipped_bait, telescope,
                mine_level, active_mine_level, active_fish_level, golden_axe, mithril_shield
            )
            SELECT
                user_id,
                COALESCE(gold_pickaxe, 0),
                COALESCE(helmet, 0),
                COALESCE(sword, 0),
                COALESCE(raw_potato, 0),
                COALESCE(golden_mushroom, 0),
                COALESCE(bait_worm, 0),
                COALESCE(bait_herring, 0),
                COALESCE(bait_sturgeon, 0),
                equipped_bait,
                COALESCE(telescope, 0),
                COALESCE(mine_level, 1),
                COALESCE(active_mine_level, 1),
                COALESCE(active_fish_level, 1),
                COALESCE(golden_axe, 0),
                COALESCE(mithril_shield, 0)
            FROM noodle_stars
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO user_activity (
                user_id, stamina, stamina_last_updated, stamina_last_reset,
                last_duel_amount, last_duel_at, last_mine, last_deposit,
                last_withdraw, last_fish, last_blackjack
            )
            SELECT
                user_id,
                COALESCE(stamina, 100),
                stamina_last_updated,
                stamina_last_reset,
                COALESCE(last_duel_amount, 0),
                last_duel_at,
                last_mine,
                last_deposit,
                last_withdraw,
                last_fish,
                last_blackjack
            FROM noodle_stars
        """)

        cursor.execute("ALTER TABLE noodle_stars RENAME TO noodle_stars_backup_v011")
        cursor.execute("""
            CREATE TABLE noodle_stars (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                stars INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            INSERT INTO noodle_stars (user_id, username, stars, bank)
            SELECT user_id, username, COALESCE(stars, 0), COALESCE(bank, 0)
            FROM noodle_stars_backup_v011
        """)
        cursor.execute("DROP TABLE noodle_stars_backup_v011")


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_inventory (
            user_id INTEGER PRIMARY KEY,
            gold_pickaxe INTEGER DEFAULT 0,
            helmet INTEGER DEFAULT 0,
            sword INTEGER DEFAULT 0,
            raw_potato INTEGER DEFAULT 0,
            golden_mushroom INTEGER DEFAULT 0,
            bait_worm INTEGER DEFAULT 0,
            bait_herring INTEGER DEFAULT 0,
            bait_sturgeon INTEGER DEFAULT 0,
            equipped_bait TEXT,
            telescope INTEGER DEFAULT 0,
            mine_level INTEGER DEFAULT 1,
            active_mine_level INTEGER DEFAULT 1,
            active_fish_level INTEGER DEFAULT 1,
            golden_axe INTEGER DEFAULT 0,
            mithril_shield INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            user_id INTEGER PRIMARY KEY,
            stamina INTEGER DEFAULT 100,
            stamina_last_updated TEXT,
            stamina_last_reset TEXT,
            last_duel_amount INTEGER DEFAULT 0,
            last_duel_at TEXT,
            last_mine TEXT,
            last_deposit TEXT,
            last_withdraw TEXT,
            last_fish TEXT,
            last_blackjack TEXT
        )
    """)

    if not _table_has_column(cursor, "noodle_stars", "gold_pickaxe"):
        cursor.execute("ALTER TABLE noodle_stars RENAME TO noodle_stars_core_backup_v011")
        cursor.execute("""
            CREATE TABLE noodle_stars (
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
                last_withdraw TEXT,
                bait_worm INTEGER DEFAULT 0,
                bait_herring INTEGER DEFAULT 0,
                bait_sturgeon INTEGER DEFAULT 0,
                equipped_bait TEXT,
                last_fish TEXT,
                telescope INTEGER DEFAULT 0,
                mine_level INTEGER DEFAULT 1,
                active_mine_level INTEGER DEFAULT 1,
                active_fish_level INTEGER DEFAULT 1,
                golden_axe INTEGER DEFAULT 0,
                mithril_shield INTEGER DEFAULT 0,
                last_blackjack TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO noodle_stars (
                user_id, username, stars, bank, stamina, stamina_last_updated, stamina_last_reset,
                last_duel_amount, last_duel_at, last_mine, gold_pickaxe, helmet, sword, raw_potato,
                golden_mushroom, last_deposit, last_withdraw, bait_worm, bait_herring, bait_sturgeon,
                equipped_bait, last_fish, telescope, mine_level, active_mine_level, active_fish_level,
                golden_axe, mithril_shield, last_blackjack
            )
            SELECT
                ns.user_id,
                ns.username,
                COALESCE(ns.stars, 0),
                COALESCE(ns.bank, 0),
                COALESCE(ua.stamina, 100),
                ua.stamina_last_updated,
                ua.stamina_last_reset,
                COALESCE(ua.last_duel_amount, 0),
                ua.last_duel_at,
                ua.last_mine,
                COALESCE(ui.gold_pickaxe, 0),
                COALESCE(ui.helmet, 0),
                COALESCE(ui.sword, 0),
                COALESCE(ui.raw_potato, 0),
                COALESCE(ui.golden_mushroom, 0),
                ua.last_deposit,
                ua.last_withdraw,
                COALESCE(ui.bait_worm, 0),
                COALESCE(ui.bait_herring, 0),
                COALESCE(ui.bait_sturgeon, 0),
                ui.equipped_bait,
                ua.last_fish,
                COALESCE(ui.telescope, 0),
                COALESCE(ui.mine_level, 1),
                COALESCE(ui.active_mine_level, 1),
                COALESCE(ui.active_fish_level, 1),
                COALESCE(ui.golden_axe, 0),
                COALESCE(ui.mithril_shield, 0),
                ua.last_blackjack
            FROM noodle_stars_core_backup_v011 ns
            LEFT JOIN user_inventory ui ON ui.user_id = ns.user_id
            LEFT JOIN user_activity ua ON ua.user_id = ns.user_id
        """)
        cursor.execute("DROP TABLE noodle_stars_core_backup_v011")

    cursor.execute("DROP TABLE IF EXISTS user_inventory")
    cursor.execute("DROP TABLE IF EXISTS user_activity")

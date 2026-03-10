"""Inventory overhaul — Phase 1: new tables and data migration.

Splits the monolithic user_inventory table into three purpose-built tables:
- user_equipment: permanent items that survive disasters
- user_inventory_items: slotted consumable/resource items (wiped by disasters)
- user_progression: levels, machine state, bag capacity

Existing data is migrated from user_inventory, which is then renamed to
user_inventory_legacy as a backup.
"""

DESCRIPTION = "Inventory overhaul: equipment, inventory items, and progression tables"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


# ── Equipment columns on user_inventory ──────────────────────────
# Each tuple is (column_name, item_key) — item_key is what goes into
# user_equipment.item_key.  The column value becomes `uses`.
_EQUIPMENT_COLUMNS = [
    ("helmet", "helmet"),
    ("sword", "sword"),
    ("golden_axe", "golden_axe"),
    ("mithril_shield", "mithril_shield"),
    ("bank_insurance", "bank_insurance"),
    ("ray_gun", "ray_gun"),
    ("star_magnet", "star_magnet"),
    ("lucky_charm", "lucky_charm"),
    ("heart_of_leviathan", "heart_of_leviathan"),
    ("rune_fragment", "rune_fragment"),
    ("fossilized_noodle", "fossilized_noodle"),
    ("bucktail_jig", "bucktail_jig"),
]

# Ownership flags that become equipment rows with uses=1.
_OWNERSHIP_COLUMNS = [
    ("preserver_owned", "preserver"),
    ("growbot_owned", "growbot"),
]

# ── Consumable columns on user_inventory ─────────────────────────
# Each count is expanded into individual rows in user_inventory_items.
_CONSUMABLE_COLUMNS = [
    "raw_potato",
    "golden_mushroom",
    "bait_worm",
    "bait_herring",
    "bait_sturgeon",
    "fertilizer",
    "water",
]


def upgrade(cursor) -> None:
    # ── 1. Create user_equipment ─────────────────────────────────
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_equipment (
            user_id     INTEGER NOT NULL,
            item_key    TEXT    NOT NULL,
            uses        INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item_key)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_equipment_user
        ON user_equipment(user_id)
        """
    )

    # ── 2. Create user_inventory_items ───────────────────────────
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_inventory_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            item_key    TEXT    NOT NULL,
            category    TEXT    NOT NULL DEFAULT 'consumable',
            base_sell_value INTEGER NOT NULL DEFAULT 0,
            quality     TEXT,
            acquired_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_inventory_items_user
        ON user_inventory_items(user_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_inventory_items_user_item
        ON user_inventory_items(user_id, item_key)
        """
    )

    # ── 3. Create user_progression ───────────────────────────────
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_progression (
            user_id                 INTEGER PRIMARY KEY,
            mine_level              INTEGER NOT NULL DEFAULT 1,
            active_mine_level       INTEGER NOT NULL DEFAULT 1,
            active_fish_level       INTEGER NOT NULL DEFAULT 1,
            space_planet_level      INTEGER NOT NULL DEFAULT 0,
            active_space_planet     INTEGER NOT NULL DEFAULT 0,
            farm_level              INTEGER NOT NULL DEFAULT 1,
            farm_plots              INTEGER NOT NULL DEFAULT 0,
            first_weather_bonus     INTEGER NOT NULL DEFAULT 0,
            inventory_capacity      INTEGER NOT NULL DEFAULT 50,
            equipped_bait           TEXT,
            jig_active              INTEGER NOT NULL DEFAULT 0,
            preserver_level         INTEGER NOT NULL DEFAULT 0,
            preserver_pending_stars  INTEGER NOT NULL DEFAULT 0,
            preserver_ready_ts      INTEGER NOT NULL DEFAULT 0,
            growbot_level           INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # ── Guard: nothing to migrate if user_inventory doesn't exist ─
    if not _table_exists(cursor, "user_inventory"):
        return

    # ── 4. Migrate progression data ──────────────────────────────
    has_farm_plots = _column_exists(cursor, "user_inventory", "farm_plots")
    has_first_weather_bonus = _column_exists(
        cursor, "user_inventory", "first_weather_bonus"
    )
    has_preserver_level = _column_exists(
        cursor, "user_inventory", "preserver_level"
    )
    has_preserver_pending = _column_exists(
        cursor, "user_inventory", "preserver_pending_stars"
    )
    has_preserver_ready = _column_exists(
        cursor, "user_inventory", "preserver_ready_ts"
    )
    has_growbot_level = _column_exists(
        cursor, "user_inventory", "growbot_level"
    )
    has_jig_active = _column_exists(cursor, "user_inventory", "jig_active")

    farm_plots_expr = "COALESCE(farm_plots, 0)" if has_farm_plots else "0"
    first_weather_expr = (
        "COALESCE(first_weather_bonus, 0)" if has_first_weather_bonus else "0"
    )
    preserver_level_expr = (
        "COALESCE(preserver_level, 0)" if has_preserver_level else "0"
    )
    preserver_pending_expr = (
        "COALESCE(preserver_pending_stars, 0)" if has_preserver_pending else "0"
    )
    preserver_ready_expr = (
        "COALESCE(preserver_ready_ts, 0)" if has_preserver_ready else "0"
    )
    growbot_level_expr = (
        "COALESCE(growbot_level, 0)" if has_growbot_level else "0"
    )
    jig_active_expr = "COALESCE(jig_active, 0)" if has_jig_active else "0"

    cursor.execute(
        f"""
        INSERT INTO user_progression (
            user_id, mine_level, active_mine_level, active_fish_level,
            space_planet_level, active_space_planet, farm_level, farm_plots,
            first_weather_bonus, equipped_bait, jig_active,
            preserver_level, preserver_pending_stars, preserver_ready_ts,
            growbot_level
        )
        SELECT
            user_id,
            COALESCE(mine_level, 1), COALESCE(active_mine_level, 1),
            COALESCE(active_fish_level, 1), COALESCE(space_planet_level, 0),
            COALESCE(active_space_planet, 0), COALESCE(farm_level, 1),
            {farm_plots_expr}, {first_weather_expr},
            equipped_bait, {jig_active_expr},
            {preserver_level_expr}, {preserver_pending_expr},
            {preserver_ready_expr}, {growbot_level_expr}
        FROM user_inventory
        """
    )

    # ── 5. Migrate equipment ─────────────────────────────────────
    for col, item_key in _EQUIPMENT_COLUMNS:
        if not _column_exists(cursor, "user_inventory", col):
            continue
        cursor.execute(
            f"""
            INSERT INTO user_equipment (user_id, item_key, uses)
            SELECT user_id, '{item_key}', COALESCE({col}, 0)
            FROM user_inventory
            WHERE COALESCE({col}, 0) > 0
            """
        )

    for col, item_key in _OWNERSHIP_COLUMNS:
        if not _column_exists(cursor, "user_inventory", col):
            continue
        cursor.execute(
            f"""
            INSERT INTO user_equipment (user_id, item_key, uses)
            SELECT user_id, '{item_key}', 1
            FROM user_inventory
            WHERE COALESCE({col}, 0) > 0
            """
        )

    # ── 6. Migrate consumable items ──────────────────────────────
    for col in _CONSUMABLE_COLUMNS:
        if not _column_exists(cursor, "user_inventory", col):
            continue
        cursor.execute(
            f"""
            WITH RECURSIVE cnt(n) AS (
                SELECT 1 UNION ALL SELECT n + 1 FROM cnt WHERE n < 9999
            )
            INSERT INTO user_inventory_items (user_id, item_key, category, acquired_at)
            SELECT ui.user_id, '{col}', 'consumable', datetime('now')
            FROM user_inventory ui
            JOIN cnt ON cnt.n <= COALESCE(ui.{col}, 0)
            WHERE COALESCE(ui.{col}, 0) > 0
            """
        )

    # ── 7. Rename old table as backup ────────────────────────────
    cursor.execute("ALTER TABLE user_inventory RENAME TO user_inventory_legacy")


def downgrade(cursor) -> None:
    """Restore user_inventory from legacy backup and drop new tables."""
    if _table_exists(cursor, "user_inventory_legacy"):
        # If someone already recreated user_inventory, drop it first
        if _table_exists(cursor, "user_inventory"):
            cursor.execute("DROP TABLE user_inventory")
        cursor.execute(
            "ALTER TABLE user_inventory_legacy RENAME TO user_inventory"
        )

    cursor.execute("DROP TABLE IF EXISTS user_equipment")
    cursor.execute("DROP TABLE IF EXISTS user_inventory_items")
    cursor.execute("DROP TABLE IF EXISTS user_progression")

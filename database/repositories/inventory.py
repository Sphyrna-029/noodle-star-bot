"""Inventory repository operations — legacy shim layer."""

from database.repositories.base import BaseRepository


class InventoryRepository(BaseRepository):
    """Backward-compatible inventory operations.

    Routes reads/writes to the appropriate new table:
    - user_equipment for equipment items
    - user_inventory_items for consumable resources
    - user_progression for levels and state
    """

    _EQUIPMENT_KEYS = {
        "helmet", "sword", "golden_axe", "mithril_shield", "bank_insurance",
        "ray_gun", "star_magnet", "lucky_charm", "heart_of_leviathan",
        "rune_fragment", "fossilized_noodle", "bucktail_jig",
    }

    _PROGRESSION_KEYS = {
        "mine_level", "active_mine_level", "active_fish_level",
        "space_planet_level", "active_space_planet", "farm_level",
        "farm_plots", "first_weather_bonus", "inventory_capacity",
        "equipped_bait", "jig_active",
        "preserver_level", "preserver_pending_stars", "preserver_ready_ts",
        "growbot_level",
    }

    _OWNERSHIP_MAP = {
        "preserver_owned": "preserver",
        "growbot_owned": "growbot",
        "gold_pickaxe": "gold_pickaxe",
        "telescope": "telescope",
        "rocket_ship": "rocket_ship",
        "lucky_dice": "lucky_dice",
        "wooden_sword": "wooden_sword",
        "wooden_shield": "wooden_shield",
        "leather_vest": "leather_vest",
        "iron_dagger": "iron_dagger",
    }

    _CONSUMABLE_KEYS = {
        "raw_potato", "golden_mushroom", "bait_worm", "bait_herring",
        "bait_sturgeon", "fertilizer", "water",
    }

    _PROGRESSION_DEFAULTS = {
        "mine_level": 1, "active_mine_level": 1, "active_fish_level": 1,
        "space_planet_level": 0, "active_space_planet": 0,
        "farm_level": 1, "farm_plots": 0, "first_weather_bonus": 0,
        "inventory_capacity": 50, "equipped_bait": None, "jig_active": 0,
        "preserver_level": 0, "preserver_pending_stars": 0,
        "preserver_ready_ts": 0, "growbot_level": 0,
    }

    # Combined set for validation
    _INVENTORY_COLUMNS = (
        _EQUIPMENT_KEYS | _PROGRESSION_KEYS | _CONSUMABLE_KEYS
        | set(_OWNERSHIP_MAP.keys())
    )

    def _ensure_progression_row(self, cursor, user_id: int) -> None:
        cursor.execute(
            "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
            (user_id,),
        )

    def get_user_inventory(self, user_id: int) -> dict:
        """Get user's inventory as a dictionary. LEGACY SHIM — reads from 3 new tables."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)

            # 1. Read equipment
            cursor.execute(
                "SELECT item_key, uses FROM user_equipment WHERE user_id = ?",
                (user_id,),
            )
            equip = {row["item_key"]: row["uses"] for row in cursor.fetchall()}

            # 2. Read progression
            cursor.execute(
                """SELECT mine_level, active_mine_level, active_fish_level,
                          space_planet_level, active_space_planet,
                          farm_level, farm_plots, first_weather_bonus,
                          inventory_capacity, equipped_bait, jig_active,
                          preserver_level, preserver_pending_stars, preserver_ready_ts,
                          growbot_level
                   FROM user_progression WHERE user_id = ?""",
                (user_id,),
            )
            prog_row = cursor.fetchone()

            # 3. Read consumable counts from inventory_items
            cursor.execute(
                """SELECT item_key, COUNT(*) as cnt
                   FROM user_inventory_items WHERE user_id = ?
                   GROUP BY item_key""",
                (user_id,),
            )
            consumables = {row["item_key"]: row["cnt"] for row in cursor.fetchall()}

        # Build the unified dict
        result = {}

        # Equipment items
        for key in self._EQUIPMENT_KEYS:
            result[key] = equip.get(key, 0)

        # Ownership flags (equipment table, different key names)
        for legacy_key, equip_key in self._OWNERSHIP_MAP.items():
            result[legacy_key] = 1 if equip.get(equip_key, 0) > 0 else 0

        # Progression values
        if prog_row:
            for key in self._PROGRESSION_KEYS:
                val = prog_row[key]
                result[key] = val if val is not None else self._PROGRESSION_DEFAULTS.get(key, 0)
        else:
            for key in self._PROGRESSION_KEYS:
                result[key] = self._PROGRESSION_DEFAULTS.get(key, 0)

        # Consumable counts
        for key in self._CONSUMABLE_KEYS:
            result[key] = consumables.get(key, 0)

        return result

    def update_user_inventory(self, user_id: int, item: str, amount: int) -> None:
        """Update a specific inventory item. LEGACY SHIM — routes to correct table."""
        if item in self._EQUIPMENT_KEYS:
            # Equipment table: set uses directly
            with self.db.get_cursor() as cursor:
                if amount <= 0:
                    cursor.execute(
                        "DELETE FROM user_equipment WHERE user_id = ? AND item_key = ?",
                        (user_id, item),
                    )
                else:
                    cursor.execute(
                        """INSERT INTO user_equipment (user_id, item_key, uses) VALUES (?, ?, ?)
                           ON CONFLICT(user_id, item_key) DO UPDATE SET uses = ?""",
                        (user_id, item, amount, amount),
                    )

        elif item in self._OWNERSHIP_MAP:
            equip_key = self._OWNERSHIP_MAP[item]
            with self.db.get_cursor() as cursor:
                if amount <= 0:
                    cursor.execute(
                        "DELETE FROM user_equipment WHERE user_id = ? AND item_key = ?",
                        (user_id, equip_key),
                    )
                else:
                    cursor.execute(
                        """INSERT INTO user_equipment (user_id, item_key, uses) VALUES (?, ?, ?)
                           ON CONFLICT(user_id, item_key) DO UPDATE SET uses = ?""",
                        (user_id, equip_key, amount, amount),
                    )

        elif item in self._PROGRESSION_KEYS:
            with self.db.get_cursor() as cursor:
                self._ensure_progression_row(cursor, user_id)
                cursor.execute(
                    f"UPDATE user_progression SET {item} = ? WHERE user_id = ?",
                    (amount, user_id),
                )

        elif item in self._CONSUMABLE_KEYS:
            # Consumable: sync the count by adding/removing rows
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM user_inventory_items WHERE user_id = ? AND item_key = ?",
                    (user_id, item),
                )
                current = cursor.fetchone()["cnt"]
                delta = amount - current
                if delta > 0:
                    for _ in range(delta):
                        cursor.execute(
                            """INSERT INTO user_inventory_items
                               (user_id, item_key, category, base_sell_value)
                               VALUES (?, ?, 'consumable', 0)""",
                            (user_id, item),
                        )
                elif delta < 0:
                    # Remove oldest items
                    cursor.execute(
                        """SELECT id FROM user_inventory_items
                           WHERE user_id = ? AND item_key = ?
                           ORDER BY acquired_at ASC LIMIT ?""",
                        (user_id, item, -delta),
                    )
                    ids = [row["id"] for row in cursor.fetchall()]
                    if ids:
                        placeholders = ",".join("?" * len(ids))
                        cursor.execute(
                            f"DELETE FROM user_inventory_items WHERE id IN ({placeholders})",
                            ids,
                        )
        else:
            raise ValueError(f"Unsupported inventory column: {item}")

    def clear_user_inventory(self, user_id: int) -> None:
        """Disaster wipe: clear all inventory items (resources + consumables). Equipment survives."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_inventory_items WHERE user_id = ?",
                (user_id,),
            )

    def clear_all_items(self, user_id: int) -> None:
        """Alien abduction: wipe equipment AND inventory items. Progression untouched."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_equipment WHERE user_id = ?",
                (user_id,),
            )
            cursor.execute(
                "DELETE FROM user_inventory_items WHERE user_id = ?",
                (user_id,),
            )

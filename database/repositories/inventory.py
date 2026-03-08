"""Inventory repository operations."""


from database.repositories.base import BaseRepository


class InventoryRepository(BaseRepository):
    """Item inventory read/write operations."""

    _INVENTORY_COLUMNS = {
        "gold_pickaxe",
        "helmet",
        "sword",
        "raw_potato",
        "golden_mushroom",
        "bait_worm",
        "bait_herring",
        "bait_sturgeon",
        "equipped_bait",
        "telescope",
        "mine_level",
        "active_mine_level",
        "active_fish_level",
        "golden_axe",
        "mithril_shield",
        "bank_insurance",
        "rocket_ship",
        "space_planet_level",
        "active_space_planet",
        "farm_level",
        "fertilizer",
        "water",
        "rune_fragment",
        "fossilized_noodle",
        "bucktail_jig",
        "jig_active",
        "ray_gun",
        "star_magnet",
        "lucky_charm",
        "heart_of_leviathan",
    }

    def _ensure_inventory_row(self, cursor, user_id: int) -> None:
        cursor.execute(
            """
            INSERT INTO user_inventory (
                user_id, gold_pickaxe, helmet, sword, raw_potato, golden_mushroom,
                bait_worm, bait_herring, bait_sturgeon, equipped_bait, telescope,
                mine_level, active_mine_level, active_fish_level, golden_axe, mithril_shield,
                bank_insurance, rocket_ship, space_planet_level, active_space_planet, farm_level,
                fertilizer, water,
                rune_fragment, fossilized_noodle, bucktail_jig, jig_active,
                ray_gun, star_magnet, lucky_charm, heart_of_leviathan
            ) VALUES (?, 0, 0, 0, 0, 0, 0, 0, 0, NULL, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )

    def get_user_inventory(self, user_id: int) -> dict:
        """Get user's inventory as a dictionary."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                """
                SELECT gold_pickaxe, helmet, sword, raw_potato, golden_mushroom,
                       bait_worm, bait_herring, bait_sturgeon, telescope,
                       mine_level, active_mine_level, golden_axe, mithril_shield,
                       bank_insurance, rocket_ship, space_planet_level,
                       active_space_planet, farm_level, fertilizer, water,
                       rune_fragment, fossilized_noodle, bucktail_jig, jig_active,
                       ray_gun, star_magnet, lucky_charm, heart_of_leviathan
                FROM user_inventory WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return {
                    "gold_pickaxe": 0,
                    "helmet": 0,
                    "sword": 0,
                    "raw_potato": 0,
                    "golden_mushroom": 0,
                    "bait_worm": 0,
                    "bait_herring": 0,
                    "bait_sturgeon": 0,
                    "telescope": 0,
                    "mine_level": 1,
                    "active_mine_level": 1,
                    "golden_axe": 0,
                    "mithril_shield": 0,
                    "bank_insurance": 0,
                    "rocket_ship": 0,
                    "space_planet_level": 0,
                    "active_space_planet": 0,
                    "farm_level": 1,
                    "fertilizer": 0,
                    "water": 0,
                    "rune_fragment": 0,
                    "fossilized_noodle": 0,
                    "bucktail_jig": 0,
                    "jig_active": 0,
                    "ray_gun": 0,
                    "star_magnet": 0,
                    "lucky_charm": 0,
                    "heart_of_leviathan": 0,
                }

            return {
                "gold_pickaxe": row["gold_pickaxe"] or 0,
                "helmet": row["helmet"] or 0,
                "sword": row["sword"] or 0,
                "raw_potato": row["raw_potato"] or 0,
                "golden_mushroom": row["golden_mushroom"] or 0,
                "bait_worm": row["bait_worm"] or 0,
                "bait_herring": row["bait_herring"] or 0,
                "bait_sturgeon": row["bait_sturgeon"] or 0,
                "telescope": row["telescope"] or 0,
                "mine_level": row["mine_level"] or 1,
                "active_mine_level": row["active_mine_level"] or 1,
                "golden_axe": row["golden_axe"] or 0,
                "mithril_shield": row["mithril_shield"] or 0,
                "bank_insurance": (row["bank_insurance"] if "bank_insurance" in row.keys() else 0) or 0,
                "rocket_ship": row["rocket_ship"] or 0,
                "space_planet_level": row["space_planet_level"] or 0,
                "active_space_planet": row["active_space_planet"] or 0,
                "farm_level": row["farm_level"] or 1,
                "fertilizer": (row["fertilizer"] if "fertilizer" in row.keys() else 0) or 0,
                "water": (row["water"] if "water" in row.keys() else 0) or 0,
                "rune_fragment": row["rune_fragment"] or 0,
                "fossilized_noodle": row["fossilized_noodle"] or 0,
                "bucktail_jig": row["bucktail_jig"] or 0,
                "jig_active": row["jig_active"] or 0,
                "ray_gun": row["ray_gun"] or 0,
                "star_magnet": row["star_magnet"] or 0,
                "lucky_charm": row["lucky_charm"] or 0,
                "heart_of_leviathan": row["heart_of_leviathan"] or 0,
            }

    def update_user_inventory(self, user_id: int, item: str, amount: int) -> None:
        """Update a specific inventory item for a user."""
        if item not in self._INVENTORY_COLUMNS:
            raise ValueError(f"Unsupported inventory column: {item}")

        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                f"UPDATE user_inventory SET {item} = ? WHERE user_id = ?",
                (amount, user_id),
            )

    def clear_user_inventory(self, user_id: int) -> None:
        """Remove all items from user's inventory except gold pickaxe."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                """
                UPDATE user_inventory
                SET helmet = 0, sword = 0, raw_potato = 0, golden_mushroom = 0
                WHERE user_id = ?
                """,
                (user_id,),
            )

    def clear_all_items(self, user_id: int) -> None:
        """Remove all inventory items, including tools and bait."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                """
                UPDATE user_inventory
                SET gold_pickaxe = 0, helmet = 0, sword = 0,
                    raw_potato = 0, golden_mushroom = 0, telescope = 0,
                    bait_worm = 0, bait_herring = 0, bait_sturgeon = 0,
                    equipped_bait = NULL, golden_axe = 0, mithril_shield = 0,
                    bank_insurance = 0, rocket_ship = 0,
                    rune_fragment = 0, fossilized_noodle = 0,
                    bucktail_jig = 0, jig_active = 0,
                    ray_gun = 0, star_magnet = 0,
                    lucky_charm = 0, heart_of_leviathan = 0,
                    fertilizer = 0, water = 0
                WHERE user_id = ?
                """,
                (user_id,),
            )

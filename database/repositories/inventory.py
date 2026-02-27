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
    }

    def _ensure_inventory_row(self, cursor, user_id: int) -> None:
        cursor.execute(
            """
            INSERT INTO user_inventory (
                user_id, gold_pickaxe, helmet, sword, raw_potato, golden_mushroom,
                bait_worm, bait_herring, bait_sturgeon, equipped_bait, telescope,
                mine_level, active_mine_level, active_fish_level, golden_axe, mithril_shield
            ) VALUES (?, 0, 0, 0, 0, 0, 0, 0, 0, NULL, 0, 1, 1, 1, 0, 0)
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
                       mine_level, active_mine_level, golden_axe, mithril_shield
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
                    equipped_bait = NULL, golden_axe = 0, mithril_shield = 0
                WHERE user_id = ?
                """,
                (user_id,),
            )

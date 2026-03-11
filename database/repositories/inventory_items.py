"""Inventory items repository operations."""
from database.repositories.base import BaseRepository

class InventoryItemsRepository(BaseRepository):
    """Slotted inventory items read/write operations (user_inventory_items table)."""

    def get_inventory_items(self, user_id: int) -> list[dict]:
        """Return all inventory item rows for user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, category, base_sell_value, quality, acquired_at
                   FROM user_inventory_items WHERE user_id = ? ORDER BY id""",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_inventory_count(self, user_id: int) -> int:
        """Total number of items in inventory (slot count)."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_inventory_items WHERE user_id = ?",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

    def get_item_count(self, user_id: int, item_key: str) -> int:
        """Count of a specific item type in inventory."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_inventory_items WHERE user_id = ? AND item_key = ?",
                (user_id, item_key),
            )
            return cursor.fetchone()["cnt"]

    def get_inventory_capacity(self, user_id: int) -> int:
        """Get user's inventory capacity from progression table."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT inventory_capacity FROM user_progression WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return row["inventory_capacity"] if row else 50

    def has_space(self, user_id: int, slots_needed: int = 1) -> bool:
        """Check if inventory has room for more items."""
        count = self.get_inventory_count(user_id)
        capacity = self.get_inventory_capacity(user_id)
        return count + slots_needed <= capacity

    def add_item(self, user_id: int, item_key: str, category: str = "consumable",
                 base_sell_value: int = 0, quality: str = None) -> bool:
        """Add one item to inventory. Returns False if no space."""
        if not self.has_space(user_id):
            return False
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_inventory_items
                   (user_id, item_key, category, base_sell_value, quality)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, item_key, category, base_sell_value, quality),
            )
        return True

    def add_items(self, user_id: int, item_key: str, quantity: int,
                  category: str = "consumable", base_sell_value: int = 0,
                  quality: str = None) -> int:
        """Add multiple items. Returns number actually added (may be less if inventory fills)."""
        capacity = self.get_inventory_capacity(user_id)
        count = self.get_inventory_count(user_id)
        space = capacity - count
        to_add = min(quantity, space)
        if to_add <= 0:
            return 0
        with self.db.get_cursor() as cursor:
            for _ in range(to_add):
                cursor.execute(
                    """INSERT INTO user_inventory_items
                       (user_id, item_key, category, base_sell_value, quality)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, item_key, category, base_sell_value, quality),
                )
        return to_add

    def remove_items(self, user_id: int, item_key: str, quantity: int = 1) -> int:
        """Remove N items of a type (oldest first). Returns number actually removed."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id FROM user_inventory_items
                   WHERE user_id = ? AND item_key = ?
                   ORDER BY acquired_at ASC LIMIT ?""",
                (user_id, item_key, quantity),
            )
            ids = [row["id"] for row in cursor.fetchall()]
            if ids:
                placeholders = ",".join("?" * len(ids))
                cursor.execute(
                    f"DELETE FROM user_inventory_items WHERE id IN ({placeholders}) AND user_id = ?",
                    [*ids, user_id],
                )
            return len(ids)

    def remove_items_by_category(self, user_id: int, category: str) -> int:
        """Remove all items in a category. Returns count removed."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_inventory_items WHERE user_id = ? AND category = ?",
                (user_id, category),
            )
            count = cursor.fetchone()["cnt"]
            cursor.execute(
                "DELETE FROM user_inventory_items WHERE user_id = ? AND category = ?",
                (user_id, category),
            )
            return count

    def clear_inventory(self, user_id: int) -> None:
        """Disaster wipe: delete ALL inventory items for user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_inventory_items WHERE user_id = ?",
                (user_id,),
            )

    def get_items_by_category(self, user_id: int, category: str) -> list[dict]:
        """Get all items of a specific category."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, category, base_sell_value, quality, acquired_at
                   FROM user_inventory_items
                   WHERE user_id = ? AND category = ?
                   ORDER BY item_key, acquired_at""",
                (user_id, category),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_items_by_key(self, user_id: int, item_key: str) -> list[dict]:
        """Get all inventory items matching an item_key."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, category, base_sell_value, quality, acquired_at
                   FROM user_inventory_items
                   WHERE user_id = ? AND item_key = ?
                   ORDER BY acquired_at ASC""",
                (user_id, item_key),
            )
            return [dict(row) for row in cursor.fetchall()]

    def remove_items_by_ids(self, user_id: int, ids: list[int]) -> int:
        """Remove specific inventory item rows by id. Returns count removed."""
        if not ids:
            return 0
        with self.db.get_cursor() as cursor:
            placeholders = ",".join("?" * len(ids))
            cursor.execute(
                f"DELETE FROM user_inventory_items WHERE id IN ({placeholders}) AND user_id = ?",
                [*ids, user_id],
            )
            return len(ids)

    def get_items_summary(self, user_id: int) -> dict[str, list[dict]]:
        """Get inventory grouped by category. Returns {category: [{item_key, count, total_value}, ...]}."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT category, item_key, COUNT(*) as count,
                          SUM(base_sell_value) as total_value,
                          MIN(quality) as quality
                   FROM user_inventory_items
                   WHERE user_id = ?
                   GROUP BY category, item_key, quality
                   ORDER BY category, item_key""",
                (user_id,),
            )
            result = {}
            for row in cursor.fetchall():
                cat = row["category"]
                if cat not in result:
                    result[cat] = []
                result[cat].append({
                    "item_key": row["item_key"],
                    "count": row["count"],
                    "total_value": row["total_value"],
                    "quality": row["quality"],
                })
            return result

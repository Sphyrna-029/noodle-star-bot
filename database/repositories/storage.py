"""Storage repository operations — safe vault for items."""

from database.repositories.base import BaseRepository


class StorageRepository(BaseRepository):
    """Read/write operations for the user_storage table."""

    def get_storage_items(self, user_id: int) -> list[dict]:
        """Return all stored items for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, item_type, uses, category, base_sell_value, stored_at
                   FROM user_storage WHERE user_id = ?
                   ORDER BY item_key, stored_at""",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_storage_summary(self, user_id: int) -> list[dict]:
        """Get storage grouped by item_key and item_type."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT item_key, item_type,
                          COUNT(*) as count,
                          SUM(uses) as total_uses
                   FROM user_storage WHERE user_id = ?
                   GROUP BY item_key, item_type
                   ORDER BY item_type, item_key""",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_storage_count(self, user_id: int) -> int:
        """Count total items in storage."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_storage WHERE user_id = ?",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

    def add_to_storage(self, user_id: int, item_key: str,
                       item_type: str = "inventory", uses: int = 1,
                       category: str = "consumable", base_sell_value: int = 0) -> None:
        """Add an item to storage."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_storage (user_id, item_key, item_type, uses, category, base_sell_value)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, item_key, item_type, uses, category, base_sell_value),
            )

    def remove_from_storage(self, user_id: int, item_key: str,
                            item_type: str = "inventory") -> dict | None:
        """Remove one item from storage (oldest first). Returns the removed row or None."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, item_type, uses, category, base_sell_value
                   FROM user_storage
                   WHERE user_id = ? AND item_key = ? AND item_type = ?
                   ORDER BY stored_at ASC LIMIT 1""",
                (user_id, item_key, item_type),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute(
                "DELETE FROM user_storage WHERE id = ? AND user_id = ?",
                (row["id"], user_id),
            )
            return dict(row)

    def add_to_storage_bulk(self, user_id: int,
                            items: list[tuple]) -> None:
        """Add multiple items to storage.

        Each tuple is (item_key, item_type, uses) or
        (item_key, item_type, uses, category, base_sell_value).
        """
        with self.db.get_cursor() as cursor:
            for t in items:
                if len(t) >= 5:
                    key, itype, uses, cat, sell = t[0], t[1], t[2], t[3], t[4]
                else:
                    key, itype, uses = t[0], t[1], t[2]
                    cat, sell = "consumable", 0
                cursor.execute(
                    """INSERT INTO user_storage
                       (user_id, item_key, item_type, uses, category, base_sell_value)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, key, itype, uses, cat, sell),
                )

    def remove_from_storage_by_key(self, user_id: int, item_key: str,
                                   item_type: str, amount: int) -> list[dict]:
        """Remove up to `amount` items of a specific key from storage (oldest first).
        Returns list of removed rows."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, item_type, uses, category, base_sell_value
                   FROM user_storage
                   WHERE user_id = ? AND item_key = ? AND item_type = ?
                   ORDER BY stored_at ASC LIMIT ?""",
                (user_id, item_key, item_type, amount),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                ids = [r["id"] for r in rows]
                placeholders = ",".join("?" * len(ids))
                cursor.execute(
                    f"DELETE FROM user_storage WHERE id IN ({placeholders}) AND user_id = ?",
                    [*ids, user_id],
                )
            return rows

    def remove_from_storage_by_category(self, user_id: int,
                                        category_keys: set[str]) -> list[dict]:
        """Remove all inventory items matching any of the given item_keys.
        Returns list of removed rows."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, item_type, uses, category, base_sell_value
                   FROM user_storage
                   WHERE user_id = ? AND item_type = 'inventory'
                   ORDER BY item_key, stored_at""",
                (user_id,),
            )
            rows = [dict(r) for r in cursor.fetchall() if r["item_key"] in category_keys]
            if rows:
                ids = [r["id"] for r in rows]
                placeholders = ",".join("?" * len(ids))
                cursor.execute(
                    f"DELETE FROM user_storage WHERE id IN ({placeholders}) AND user_id = ?",
                    [*ids, user_id],
                )
            return rows

    def count_stored_item(self, user_id: int, item_key: str,
                          item_type: str = "inventory") -> int:
        """Count how many of a specific item are in storage."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*) as cnt FROM user_storage
                   WHERE user_id = ? AND item_key = ? AND item_type = ?""",
                (user_id, item_key, item_type),
            )
            return cursor.fetchone()["cnt"]

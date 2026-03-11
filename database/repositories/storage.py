"""Storage repository operations — safe vault for items."""

from database.repositories.base import BaseRepository


class StorageRepository(BaseRepository):
    """Read/write operations for the user_storage table."""

    def get_storage_items(self, user_id: int) -> list[dict]:
        """Return all stored items for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, item_type, uses, stored_at
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
                       item_type: str = "inventory", uses: int = 1) -> None:
        """Add an item to storage."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_storage (user_id, item_key, item_type, uses)
                   VALUES (?, ?, ?, ?)""",
                (user_id, item_key, item_type, uses),
            )

    def remove_from_storage(self, user_id: int, item_key: str,
                            item_type: str = "inventory") -> dict | None:
        """Remove one item from storage (oldest first). Returns the removed row or None."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT id, item_key, item_type, uses FROM user_storage
                   WHERE user_id = ? AND item_key = ? AND item_type = ?
                   ORDER BY stored_at ASC LIMIT 1""",
                (user_id, item_key, item_type),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute(
                "DELETE FROM user_storage WHERE id = ?",
                (row["id"],),
            )
            return dict(row)

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

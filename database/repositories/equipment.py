"""Equipment repository operations."""
from database.repositories.base import BaseRepository

class EquipmentRepository(BaseRepository):
    """Equipment items read/write operations (user_equipment table)."""

    def _ensure_equipment_row(self, cursor, user_id: int, item_key: str) -> None:
        cursor.execute(
            "INSERT OR IGNORE INTO user_equipment (user_id, item_key, uses) VALUES (?, ?, 0)",
            (user_id, item_key),
        )

    def get_user_equipment(self, user_id: int) -> dict[str, int]:
        """Get all equipment as {item_key: uses}."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT item_key, uses FROM user_equipment WHERE user_id = ?",
                (user_id,),
            )
            return {row["item_key"]: row["uses"] for row in cursor.fetchall()}

    def get_equipment_uses(self, user_id: int, item_key: str) -> int:
        """Get remaining uses for a specific equipment item. Returns 0 if not owned."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT uses FROM user_equipment WHERE user_id = ? AND item_key = ?",
                (user_id, item_key),
            )
            row = cursor.fetchone()
            return row["uses"] if row else 0

    def has_equipment(self, user_id: int, item_key: str) -> bool:
        """Check if user owns equipment (uses > 0)."""
        return self.get_equipment_uses(user_id, item_key) > 0

    def set_equipment(self, user_id: int, item_key: str, uses: int) -> None:
        """Set uses for equipment. Removes row if uses <= 0."""
        with self.db.get_cursor() as cursor:
            if uses <= 0:
                cursor.execute(
                    "DELETE FROM user_equipment WHERE user_id = ? AND item_key = ?",
                    (user_id, item_key),
                )
            else:
                cursor.execute(
                    """INSERT INTO user_equipment (user_id, item_key, uses) VALUES (?, ?, ?)
                       ON CONFLICT(user_id, item_key) DO UPDATE SET uses = ?""",
                    (user_id, item_key, uses, uses),
                )

    def add_equipment_uses(self, user_id: int, item_key: str, amount: int) -> None:
        """Add uses to equipment (for buying stacking items like helmets)."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_equipment (user_id, item_key, uses) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, item_key) DO UPDATE SET uses = uses + ?""",
                (user_id, item_key, amount, amount),
            )

    def consume_equipment_use(self, user_id: int, item_key: str) -> bool:
        """Decrement uses by 1. Returns False if already 0 or not owned."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT uses FROM user_equipment WHERE user_id = ? AND item_key = ?",
                (user_id, item_key),
            )
            row = cursor.fetchone()
            if not row or row["uses"] <= 0:
                return False
            new_uses = row["uses"] - 1
            if new_uses <= 0:
                cursor.execute(
                    "DELETE FROM user_equipment WHERE user_id = ? AND item_key = ?",
                    (user_id, item_key),
                )
            else:
                cursor.execute(
                    "UPDATE user_equipment SET uses = ? WHERE user_id = ? AND item_key = ?",
                    (new_uses, user_id, item_key),
                )
            return True

    def clear_all_equipment(self, user_id: int) -> None:
        """Alien abduction: delete all equipment rows for user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_equipment WHERE user_id = ?",
                (user_id,),
            )

    def get_equipment_count(self, user_id: int) -> int:
        """Count distinct equipment items owned."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_equipment WHERE user_id = ? AND uses > 0",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

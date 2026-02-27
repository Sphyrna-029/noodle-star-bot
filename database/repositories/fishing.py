"""Fishing repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository


class FishingRepository(BaseRepository):
    """Fishing cooldown, level, and bait operations."""

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

    def _ensure_activity_row(self, cursor, user_id: int) -> None:
        cursor.execute(
            """
            INSERT INTO user_activity (
                user_id, stamina, stamina_last_updated, stamina_last_reset,
                last_duel_amount, last_duel_at, last_mine, last_deposit,
                last_withdraw, last_fish, last_blackjack
            ) VALUES (?, 100, NULL, NULL, 0, NULL, NULL, NULL, NULL, NULL, NULL)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )

    def get_bait_inventory(self, user_id: int) -> dict:
        """Get user's bait inventory."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                """
                SELECT bait_worm, bait_herring, bait_sturgeon
                FROM user_inventory WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return {
                    "worm": 0,
                    "herring": 0,
                    "sturgeon": 0,
                }

            return {
                "worm": row["bait_worm"] or 0,
                "herring": row["bait_herring"] or 0,
                "sturgeon": row["bait_sturgeon"] or 0,
            }

    def get_equipped_bait(self, user_id: int) -> Optional[str]:
        """Get user's currently equipped bait type."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                "SELECT equipped_bait FROM user_inventory WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["equipped_bait"] is None:
                return None

            return row["equipped_bait"]

    def set_equipped_bait(self, user_id: int, bait_type: Optional[str]) -> None:
        """Set user's equipped bait type (None to unequip)."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                "UPDATE user_inventory SET equipped_bait = ? WHERE user_id = ?",
                (bait_type, user_id),
            )

    def consume_bait(self, user_id: int, bait_type: str) -> bool:
        """Consume one bait of the specified type."""
        column = f"bait_{bait_type}"
        if column not in {"bait_worm", "bait_herring", "bait_sturgeon"}:
            return False
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                f"SELECT {column} FROM user_inventory WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row[column] is None or row[column] <= 0:
                return False

            cursor.execute(
                f"UPDATE user_inventory SET {column} = {column} - 1 WHERE user_id = ?",
                (user_id,),
            )
            return True

    def get_last_fish(self, user_id: int) -> Optional[datetime]:
        """Get the user's last fishing timestamp."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                "SELECT last_fish FROM user_activity WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["last_fish"] is None:
                return None

            return datetime.fromisoformat(row["last_fish"])

    def update_last_fish(self, user_id: int) -> None:
        """Update the user's last fishing timestamp to now."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE user_activity SET last_fish = ? WHERE user_id = ?",
                (now, user_id),
            )

    def get_active_fish_level(self, user_id: int) -> int:
        """Get user's currently selected fishing level."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                "SELECT active_fish_level FROM user_inventory WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["active_fish_level"] is None:
                return 1
            return row["active_fish_level"]

    def set_active_fish_level(self, user_id: int, level: int) -> None:
        """Update user's active fishing level."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                "UPDATE user_inventory SET active_fish_level = ? WHERE user_id = ?",
                (level, user_id),
            )

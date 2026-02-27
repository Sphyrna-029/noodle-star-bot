"""Mining repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository


class MiningRepository(BaseRepository):
    """Mining cooldown and mine level operations."""

    def get_last_mine(self, user_id: int) -> Optional[datetime]:
        """Get the user's last mining timestamp."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT last_mine FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["last_mine"] is None:
                return None

            return datetime.fromisoformat(row["last_mine"])

    def update_last_mine(self, user_id: int) -> None:
        """Update the user's last mining timestamp to now."""
        with self.db.get_cursor() as cursor:
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE noodle_stars SET last_mine = ? WHERE user_id = ?",
                (now, user_id),
            )

    def get_mine_level(self, user_id: int) -> int:
        """Get user's highest unlocked mine level."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT mine_level FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["mine_level"] is None:
                return 1
            return row["mine_level"]

    def get_active_mine_level(self, user_id: int) -> int:
        """Get user's currently selected mine level."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT active_mine_level FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["active_mine_level"] is None:
                return 1
            return row["active_mine_level"]

    def set_mine_level(self, user_id: int, level: int) -> None:
        """Update user's highest unlocked mine level."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE noodle_stars SET mine_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def set_active_mine_level(self, user_id: int, level: int) -> None:
        """Update user's active mine level."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE noodle_stars SET active_mine_level = ? WHERE user_id = ?",
                (level, user_id),
            )

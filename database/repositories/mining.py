"""Mining repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository


class MiningRepository(BaseRepository):
    """Mining cooldown and mine level operations."""

    def _ensure_progression_row(self, cursor, user_id: int) -> None:
        cursor.execute(
            "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
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

    def get_last_mine(self, user_id: int) -> Optional[datetime]:
        """Get the user's last mining timestamp."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                "SELECT last_mine FROM user_activity WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["last_mine"] is None:
                return None

            return datetime.fromisoformat(row["last_mine"])

    def update_last_mine(self, user_id: int) -> None:
        """Update the user's last mining timestamp to now."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE user_activity SET last_mine = ? WHERE user_id = ?",
                (now, user_id),
            )

    def get_mine_level(self, user_id: int) -> int:
        """Get user's highest unlocked mine level."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "SELECT mine_level FROM user_progression WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["mine_level"] is None:
                return 1
            return row["mine_level"]

    def get_active_mine_level(self, user_id: int) -> int:
        """Get user's currently selected mine level."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "SELECT active_mine_level FROM user_progression WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["active_mine_level"] is None:
                return 1
            return row["active_mine_level"]

    def set_mine_level(self, user_id: int, level: int) -> None:
        """Update user's highest unlocked mine level."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "UPDATE user_progression SET mine_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def set_active_mine_level(self, user_id: int, level: int) -> None:
        """Update user's active mine level."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "UPDATE user_progression SET active_mine_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def get_space_planet_level(self, user_id: int) -> int:
        """Get user's highest unlocked space planet level (0 = not in space)."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "SELECT space_planet_level FROM user_progression WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["space_planet_level"] is None:
                return 0
            return row["space_planet_level"]

    def set_space_planet_level(self, user_id: int, level: int) -> None:
        """Update user's highest unlocked space planet level."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "UPDATE user_progression SET space_planet_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def get_active_space_planet(self, user_id: int) -> int:
        """Get user's currently active space planet (0 = none)."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "SELECT active_space_planet FROM user_progression WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["active_space_planet"] is None:
                return 0
            return row["active_space_planet"]

    def set_active_space_planet(self, user_id: int, planet: int) -> None:
        """Update user's active space planet."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "UPDATE user_progression SET active_space_planet = ? WHERE user_id = ?",
                (planet, user_id),
            )

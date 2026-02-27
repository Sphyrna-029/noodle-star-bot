"""Economy repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository


class EconomyRepository(BaseRepository):
    """Wallet, bank, leaderboard, and bank cooldown operations."""

    def get_user_bank(self, user_id: int) -> int:
        """Get user's bank balance."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT bank FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return row["bank"] if row else 0

    def get_all_total_stars(self) -> int:
        """Get total stars in the economy."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT SUM(stars) AS total FROM noodle_stars"
            )
            row = cursor.fetchone()
            return row["total"] if row else 0

    def update_user_stars(self, user_id: int, username: str, stars: int) -> None:
        """Update user's wallet stars."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE noodle_stars SET stars = ?, username = ? WHERE user_id = ?",
                (stars, username, user_id),
            )

    def update_user_bank(self, user_id: int, username: str, bank: int) -> None:
        """Update user's bank balance."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE noodle_stars SET bank = ?, username = ? WHERE user_id = ?",
                (bank, username, user_id),
            )

    def get_leaderboard(self, limit: int = 10, ascending: bool = False) -> list[tuple]:
        """Get leaderboard of users sorted by wallet stars."""
        order = "ASC" if ascending else "DESC"
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"SELECT username, stars FROM noodle_stars ORDER BY stars {order} LIMIT ?",
                (limit,),
            )
            return [(row["username"], row["stars"]) for row in cursor.fetchall()]

    def get_last_deposit(self, user_id: int) -> Optional[datetime]:
        """Get the user's last deposit timestamp."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT last_deposit FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["last_deposit"] is None:
                return None

            return datetime.fromisoformat(row["last_deposit"])

    def update_last_deposit(self, user_id: int) -> None:
        """Update the user's last deposit timestamp to now."""
        with self.db.get_cursor() as cursor:
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE noodle_stars SET last_deposit = ? WHERE user_id = ?",
                (now, user_id),
            )

    def get_last_withdraw(self, user_id: int) -> Optional[datetime]:
        """Get the user's last withdraw timestamp."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT last_withdraw FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["last_withdraw"] is None:
                return None

            return datetime.fromisoformat(row["last_withdraw"])

    def update_last_withdraw(self, user_id: int) -> None:
        """Update the user's last withdraw timestamp to now."""
        with self.db.get_cursor() as cursor:
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE noodle_stars SET last_withdraw = ? WHERE user_id = ?",
                (now, user_id),
            )

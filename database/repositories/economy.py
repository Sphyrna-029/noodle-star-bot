"""Economy repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository


class EconomyRepository(BaseRepository):
    """Wallet, bank, leaderboard, and bank cooldown operations."""

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        return start, end

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
                "SELECT SUM(stars + bank) AS total FROM noodle_stars"
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
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                "SELECT last_deposit FROM user_activity WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["last_deposit"] is None:
                return None

            return datetime.fromisoformat(row["last_deposit"])

    def update_last_deposit(self, user_id: int) -> None:
        """Update the user's last deposit timestamp to now."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE user_activity SET last_deposit = ? WHERE user_id = ?",
                (now, user_id),
            )

    def get_last_withdraw(self, user_id: int) -> Optional[datetime]:
        """Get the user's last withdraw timestamp."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                "SELECT last_withdraw FROM user_activity WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None or row["last_withdraw"] is None:
                return None

            return datetime.fromisoformat(row["last_withdraw"])

    def update_last_withdraw(self, user_id: int) -> None:
        """Update the user's last withdraw timestamp to now."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE user_activity SET last_withdraw = ? WHERE user_id = ?",
                (now, user_id),
            )

    def get_stars_earned_between(self, start: datetime, end: datetime) -> int:
        """Get total stars earned (positive deltas only) in a time range."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END), 0) AS earned
                FROM star_ledger
                WHERE changed_at >= ? AND changed_at < ?
                """,
                (start.isoformat(), end.isoformat()),
            )
            row = cursor.fetchone()
            return row["earned"] if row else 0

    def get_top_gainers_between(
        self,
        start: datetime,
        end: datetime,
        limit: int = 3,
    ) -> list[tuple[str, int]]:
        """Get top users by stars gained (positive deltas) in a time range."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT ns.username, COALESCE(SUM(sl.delta), 0) AS gained
                FROM star_ledger sl
                JOIN noodle_stars ns ON ns.user_id = sl.user_id
                WHERE sl.changed_at >= ? AND sl.changed_at < ? AND sl.delta > 0
                GROUP BY sl.user_id, ns.username
                ORDER BY gained DESC
                LIMIT ?
                """,
                (start.isoformat(), end.isoformat(), limit),
            )
            return [(row["username"], row["gained"]) for row in cursor.fetchall()]

    def get_monthly_stars_earned(self, year: int, month: int) -> int:
        """Get total stars earned in a specific calendar month."""
        start, end = self._month_bounds(year, month)
        return self.get_stars_earned_between(start, end)

    def get_top_gainers_for_month(
        self,
        year: int,
        month: int,
        limit: int = 3,
    ) -> list[tuple[str, int]]:
        """Get top users by stars gained for a specific calendar month."""
        start, end = self._month_bounds(year, month)
        return self.get_top_gainers_between(start, end, limit)

    def get_last_month_stars_earned(self) -> int:
        """Get total stars earned in the previous calendar month."""
        now = datetime.now()
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1
        return self.get_monthly_stars_earned(year, month)

    def get_top_gainers_last_month(self, limit: int = 3) -> list[tuple[str, int]]:
        """Get top users by stars gained in the previous calendar month."""
        now = datetime.now()
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1
        return self.get_top_gainers_for_month(year, month, limit)

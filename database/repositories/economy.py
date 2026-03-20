"""Economy repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository
from utils.star_ledger_context import get_context


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

    def update_user_stars(
        self, user_id: int, username: str, stars: int, reason: str | None = None
    ) -> None:
        """Update user's wallet stars and optionally annotate the ledger reason/source."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT stars FROM noodle_stars WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            old_stars = row["stars"] if row else None
            cursor.execute(
                "UPDATE noodle_stars SET stars = ?, username = ? WHERE user_id = ?",
                (stars, username, user_id),
            )
            if old_stars is None or old_stars == stars:
                return
            source, context_reason = get_context()
            if reason and ":" in reason:
                source, reason = reason.split(":", 1)
            reason = reason or context_reason
            try:
                cursor.execute(
                    """
                    UPDATE star_ledger
                    SET source = ?, reason = ?
                    WHERE id = (
                        SELECT id
                        FROM star_ledger
                        WHERE user_id = ?
                        ORDER BY id DESC
                        LIMIT 1
                    )
                    """,
                    (source or "unknown", reason or "unknown", user_id),
                )
            except Exception:
                # Keep star updates resilient if ledger columns are not present yet.
                pass

    def update_user_bank(self, user_id: int, username: str, bank: int) -> None:
        """Update user's bank balance."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE noodle_stars SET bank = ?, username = ? WHERE user_id = ?",
                (bank, username, user_id),
            )

    def get_leaderboard(self, limit: int = 10, ascending: bool = False) -> list[tuple]:
        """Get leaderboard of users sorted by net worth (wallet + item values)."""
        order = "ASC" if ascending else "DESC"
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"""
                SELECT ns.username, ns.stars,
                       COALESCE(inv.total_value, 0) + COALESCE(stash.total_value, 0) AS item_value,
                       ns.stars + COALESCE(inv.total_value, 0) + COALESCE(stash.total_value, 0) AS net_worth
                FROM noodle_stars ns
                LEFT JOIN (
                    SELECT user_id, SUM(base_sell_value) AS total_value
                    FROM user_inventory_items
                    WHERE base_sell_value > 0
                    GROUP BY user_id
                ) inv ON ns.user_id = inv.user_id
                LEFT JOIN (
                    SELECT user_id, SUM(base_sell_value) AS total_value
                    FROM aether_stash
                    WHERE base_sell_value > 0
                    GROUP BY user_id
                ) stash ON ns.user_id = stash.user_id
                ORDER BY net_worth {order}
                LIMIT ?
                """,
                (limit,),
            )
            return [
                (row["username"], row["stars"], row["item_value"], row["net_worth"])
                for row in cursor.fetchall()
            ]

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

    def get_stars_lost_between(self, start: datetime, end: datetime) -> int:
        """Get total stars lost (negative deltas only) in a time range."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN delta < 0 THEN -delta ELSE 0 END), 0) AS lost
                FROM star_ledger
                WHERE changed_at >= ? AND changed_at < ?
                """,
                (start.isoformat(), end.isoformat()),
            )
            row = cursor.fetchone()
            return row["lost"] if row else 0

    def get_user_stars_lost_by_source(self, user_id: int, source: str) -> int:
        """Get total stars lost by a user for a specific ledger source."""
        with self.db.get_cursor() as cursor:
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(CASE WHEN delta < 0 THEN -delta ELSE 0 END), 0) AS lost
                    FROM star_ledger
                    WHERE user_id = ? AND source = ?
                    """,
                    (user_id, source),
                )
                row = cursor.fetchone()
                return row["lost"] if row else 0
            except Exception:
                return 0

    def get_user_stars_earned_by_source(self, user_id: int, source: str) -> int:
        """Get total stars earned by a user for a specific ledger source."""
        with self.db.get_cursor() as cursor:
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END), 0) AS earned
                    FROM star_ledger
                    WHERE user_id = ? AND source = ?
                    """,
                    (user_id, source),
                )
                row = cursor.fetchone()
                return row["earned"] if row else 0
            except Exception:
                return 0

    def get_user_stars_earned_by_source_reason(
        self, user_id: int, source: str, reason: str
    ) -> int:
        """Get total stars earned by a user for a specific ledger source and reason."""
        with self.db.get_cursor() as cursor:
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END), 0) AS earned
                    FROM star_ledger
                    WHERE user_id = ? AND source = ? AND reason = ?
                    """,
                    (user_id, source, reason),
                )
                row = cursor.fetchone()
                return row["earned"] if row else 0
            except Exception:
                return 0

    def get_user_daily_star_activity(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> list[tuple[str, int, int, int, int]]:
        """
        Get per-day star activity for a user.

        Returns list of (day, earned, lost, net, volume) where:
        - day is YYYY-MM-DD
        - earned is sum of positive deltas
        - lost is sum of absolute value of negative deltas
        - net is sum of deltas
        - volume is sum of absolute deltas
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    date(changed_at) AS day,
                    COALESCE(SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END), 0) AS earned,
                    COALESCE(SUM(CASE WHEN delta < 0 THEN -delta ELSE 0 END), 0) AS lost,
                    COALESCE(SUM(delta), 0) AS net,
                    COALESCE(SUM(ABS(delta)), 0) AS volume
                FROM star_ledger
                WHERE user_id = ? AND changed_at >= ? AND changed_at < ?
                GROUP BY date(changed_at)
                ORDER BY day ASC
                """,
                (user_id, start.isoformat(), end.isoformat()),
            )
            return [
                (row["day"], row["earned"], row["lost"], row["net"], row["volume"])
                for row in cursor.fetchall()
            ]

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

    def get_monthly_stars_lost(self, year: int, month: int) -> int:
        """Get total stars lost in a specific calendar month."""
        start, end = self._month_bounds(year, month)
        return self.get_stars_lost_between(start, end)

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

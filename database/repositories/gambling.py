"""Gambling repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository


class GamblingRepository(BaseRepository):
    """Duel stamina and blackjack cooldown operations."""

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

    def get_duel_stamina_state(self, user_id: int) -> dict:
        """Get stamina state for duels."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                """
                SELECT stamina, stamina_last_updated, stamina_last_reset,
                       last_duel_amount, last_duel_at
                FROM user_activity WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "stamina": 0,
                    "stamina_last_updated": None,
                    "stamina_last_reset": None,
                    "last_duel_amount": 0,
                    "last_duel_at": None,
                }

            stamina_last_updated = (
                datetime.fromisoformat(row["stamina_last_updated"])
                if row["stamina_last_updated"]
                else None
            )
            stamina_last_reset = (
                datetime.fromisoformat(row["stamina_last_reset"])
                if row["stamina_last_reset"]
                else None
            )
            last_duel_at = (
                datetime.fromisoformat(row["last_duel_at"]) if row["last_duel_at"] else None
            )

            return {
                "stamina": row["stamina"] or 0,
                "stamina_last_updated": stamina_last_updated,
                "stamina_last_reset": stamina_last_reset,
                "last_duel_amount": row["last_duel_amount"] or 0,
                "last_duel_at": last_duel_at,
            }

    def update_duel_stamina_state(
        self,
        user_id: int,
        stamina: int,
        stamina_last_updated: datetime,
        stamina_last_reset: datetime,
        last_duel_amount: int,
        last_duel_at: datetime | None,
    ) -> None:
        """Update stamina state for duels."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                """
                UPDATE user_activity
                SET stamina = ?,
                    stamina_last_updated = ?,
                    stamina_last_reset = ?,
                    last_duel_amount = ?,
                    last_duel_at = ?
                WHERE user_id = ?
                """,
                (
                    stamina,
                    stamina_last_updated.isoformat(),
                    stamina_last_reset.isoformat(),
                    last_duel_amount,
                    last_duel_at.isoformat() if last_duel_at else None,
                    user_id,
                ),
            )

    def get_last_blackjack(self, user_id: int) -> Optional[datetime]:
        """Get the user's last blackjack game timestamp."""
        with self.db.get_cursor() as cursor:
            try:
                self._ensure_activity_row(cursor, user_id)
                cursor.execute(
                    "SELECT last_blackjack FROM user_activity WHERE user_id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()

                if row is None or row["last_blackjack"] is None:
                    return None

                return datetime.fromisoformat(row["last_blackjack"])
            except Exception:
                return None

    def update_last_blackjack(self, user_id: int) -> None:
        """Update the user's last blackjack game timestamp to now."""
        with self.db.get_cursor() as cursor:
            try:
                self._ensure_activity_row(cursor, user_id)
                now = datetime.now().isoformat()
                cursor.execute(
                    "UPDATE user_activity SET last_blackjack = ? WHERE user_id = ?",
                    (now, user_id),
                )
            except Exception:
                pass

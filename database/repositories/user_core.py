"""Core user repository operations."""

from datetime import datetime

from cogs.economy.constants import STARTING_BANK, STARTING_STARS
from database.models import User


from database.repositories.base import BaseRepository


class UserCoreRepository(BaseRepository):
    """Core user operations such as creation and profile updates."""

    def _ensure_profile_rows(self, cursor, user_id: int) -> None:
        """Ensure per-user rows exist in normalized tables."""
        cursor.execute(
            "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
            (user_id,),
        )
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO user_activity (
                user_id, stamina, stamina_last_updated, stamina_last_reset,
                last_duel_amount, last_duel_at, last_mine, last_deposit,
                last_withdraw, last_fish, last_blackjack
            ) VALUES (?, 100, ?, ?, 0, NULL, NULL, NULL, NULL, NULL, NULL)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, now, now),
        )

    def get_user(self, user_id: int, username: str) -> User:
        """Get a user by ID, creating them if they don't exist."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ns.user_id, ns.username, ns.stars, ns.bank,
                    COALESCE(ua.stamina, 100) AS stamina,
                    ua.stamina_last_updated,
                    ua.stamina_last_reset,
                    COALESCE(ua.last_duel_amount, 0) AS last_duel_amount,
                    ua.last_duel_at,
                    ua.last_mine,
                    COALESCE(up.mine_level, 1) AS mine_level,
                    COALESCE(up.active_mine_level, 1) AS active_mine_level
                FROM noodle_stars ns
                LEFT JOIN user_progression up ON up.user_id = ns.user_id
                LEFT JOIN user_activity ua ON ua.user_id = ns.user_id
                WHERE ns.user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None:
                cursor.execute(
                    """
                    INSERT INTO noodle_stars (user_id, username, stars, bank)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        STARTING_STARS,
                        STARTING_BANK,
                    ),
                )
                self._ensure_profile_rows(cursor, user_id)

                return User(
                    user_id=user_id,
                    username=username,
                    stars=STARTING_STARS,
                    bank=STARTING_BANK,
                )

            self._ensure_profile_rows(cursor, user_id)
            return User.from_row(row)

    def get_user_stars(self, user_id: int, username: str) -> int:
        """Get user's wallet stars (creating user if needed)."""
        user = self.get_user(user_id, username)
        return user.stars

    def update_username(self, user_id: int, username: str) -> None:
        """Update the stored username for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE noodle_stars SET username = ? WHERE user_id = ?",
                (username, user_id),
            )

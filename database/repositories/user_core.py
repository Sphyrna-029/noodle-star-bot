"""Core user repository operations."""

from datetime import datetime

from cogs.economy.constants import STARTING_BANK, STARTING_STARS
from database.models import User


from database.repositories.base import BaseRepository


class UserCoreRepository(BaseRepository):
    """Core user operations such as creation and profile updates."""

    def get_user(self, user_id: int, username: str) -> User:
        """Get a user by ID, creating them if they don't exist."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None:
                now = datetime.now().isoformat()
                cursor.execute(
                    """
                    INSERT INTO noodle_stars
                    (user_id, username, stars, bank, last_mine,
                     gold_pickaxe, helmet, sword, raw_potato, golden_mushroom, telescope,
                     stamina, stamina_last_updated, stamina_last_reset, last_duel_amount, last_duel_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        STARTING_STARS,
                        STARTING_BANK,
                        None,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        100,
                        now,
                        now,
                        0,
                        None,
                    ),
                )

                return User(
                    user_id=user_id,
                    username=username,
                    stars=STARTING_STARS,
                    bank=STARTING_BANK,
                )

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

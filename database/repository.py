"""Repository for all database operations."""

from datetime import datetime
from typing import List, Optional

from config import STARTING_BANK, STARTING_STARS
from database.connection import get_connection
from database.models import User


class UserRepository:
    """Handles all database operations for users."""

    def __init__(self):
        self.db = get_connection()

    def get_user(self, user_id: int, username: str) -> User:
        """
        Get a user by ID, creating them if they don't exist.

        Args:
            user_id: Discord user ID
            username: Discord username (for display)

        Returns:
            User object
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None:
                # Create new user
                cursor.execute(
                    """
                    INSERT INTO noodle_stars
                    (user_id, username, stars, bank, last_mine,
                     gold_pickaxe, helmet, sword, raw_potato, golden_mushroom)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def get_user_bank(self, user_id: int) -> int:
        """Get user's bank balance."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT bank FROM noodle_stars WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return row["bank"] if row else 0

    def get_user_inventory(self, user_id: int) -> dict:
        """Get user's inventory as a dictionary."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT gold_pickaxe, helmet, sword, raw_potato, golden_mushroom
                FROM noodle_stars WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return {
                    "gold_pickaxe": 0,
                    "helmet": 0,
                    "sword": 0,
                    "raw_potato": 0,
                    "golden_mushroom": 0,
                }

            return {
                "gold_pickaxe": row["gold_pickaxe"],
                "helmet": row["helmet"],
                "sword": row["sword"],
                "raw_potato": row["raw_potato"],
                "golden_mushroom": row["golden_mushroom"],
            }

    def update_user_stars(self, user_id: int, username: str, stars: int) -> None:
        """
        Update user's wallet stars.

        Uses INSERT OR REPLACE preserving bank and last_mine (matching original behavior).
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO noodle_stars
                (user_id, username, stars, bank, last_mine,
                 gold_pickaxe, helmet, sword, raw_potato, golden_mushroom)
                VALUES (
                    ?, ?, ?,
                    COALESCE((SELECT bank FROM noodle_stars WHERE user_id = ?), 0),
                    (SELECT last_mine FROM noodle_stars WHERE user_id = ?),
                    COALESCE((SELECT gold_pickaxe FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT helmet FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT sword FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT raw_potato FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT golden_mushroom FROM noodle_stars WHERE user_id = ?), 0)
                )
                """,
                (
                    user_id,
                    username,
                    stars,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                ),
            )

    def update_user_bank(self, user_id: int, username: str, bank: int) -> None:
        """
        Update user's bank balance.

        Uses INSERT OR REPLACE preserving stars and last_mine.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO noodle_stars
                (user_id, username, stars, bank, last_mine,
                 gold_pickaxe, helmet, sword, raw_potato, golden_mushroom)
                VALUES (
                    ?, ?,
                    COALESCE((SELECT stars FROM noodle_stars WHERE user_id = ?), 0),
                    ?,
                    (SELECT last_mine FROM noodle_stars WHERE user_id = ?),
                    COALESCE((SELECT gold_pickaxe FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT helmet FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT sword FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT raw_potato FROM noodle_stars WHERE user_id = ?), 0),
                    COALESCE((SELECT golden_mushroom FROM noodle_stars WHERE user_id = ?), 0)
                )
                """,
                (
                    user_id,
                    username,
                    user_id,
                    bank,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                ),
            )

    def update_username(self, user_id: int, username: str) -> None:
        """Update the stored username for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE noodle_stars SET username = ? WHERE user_id = ?",
                (username, user_id),
            )

    def update_user_inventory(self, user_id: int, item: str, amount: int) -> None:
        """Update a specific inventory item for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"UPDATE noodle_stars SET {item} = ? WHERE user_id = ?",
                (amount, user_id),
            )

    def clear_user_inventory(self, user_id: int) -> None:
        """Remove all items from user's inventory except gold pickaxe."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE noodle_stars
                SET helmet = 0, sword = 0, raw_potato = 0, golden_mushroom = 0
                WHERE user_id = ?
                """,
                (user_id,),
            )

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

    def get_leaderboard(self, limit: int = 10, ascending: bool = False) -> List[tuple]:
        """
        Get leaderboard of users sorted by wallet stars.

        Args:
            limit: Maximum number of users to return
            ascending: If True, return lowest stars first (bottom leaderboard)

        Returns:
            List of (username, stars) tuples
        """
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

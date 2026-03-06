"""Achievement repository operations."""

from datetime import datetime

from database.repositories.base import BaseRepository


class AchievementsRepository(BaseRepository):
    """Persistence helpers for achievement unlocks and progress counters."""

    def get_unlocked_achievements(self, user_id: int) -> dict[str, str]:
        """Get unlocked achievement keys mapped to unlock timestamps."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT achievement_key, unlocked_at
                FROM user_achievements
                WHERE user_id = ?
                """,
                (user_id,),
            )
            return {
                row["achievement_key"]: row["unlocked_at"]
                for row in cursor.fetchall()
            }

    def unlock_achievement(self, user_id: int, achievement_key: str) -> bool:
        """
        Permanently unlock an achievement for a user.

        Returns:
            True if newly unlocked, False if already unlocked.
        """
        with self.db.get_cursor() as cursor:
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_key, unlocked_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, achievement_key) DO NOTHING
                """,
                (user_id, achievement_key, now),
            )
            return cursor.rowcount > 0

    def get_achievement_progress(self, user_id: int) -> dict[str, int]:
        """Get all achievement counters for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT progress_key, value
                FROM user_achievement_progress
                WHERE user_id = ?
                """,
                (user_id,),
            )
            return {row["progress_key"]: int(row["value"]) for row in cursor.fetchall()}

    def increment_achievement_progress(
        self, user_id: int, progress_key: str, amount: int = 1
    ) -> int:
        """Increment a progress counter and return the new value."""
        with self.db.get_cursor() as cursor:
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO user_achievement_progress (user_id, progress_key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, progress_key) DO UPDATE SET
                    value = user_achievement_progress.value + excluded.value,
                    updated_at = excluded.updated_at
                """,
                (user_id, progress_key, amount, now),
            )
            cursor.execute(
                """
                SELECT value
                FROM user_achievement_progress
                WHERE user_id = ? AND progress_key = ?
                """,
                (user_id, progress_key),
            )
            row = cursor.fetchone()
            return int(row["value"]) if row else 0

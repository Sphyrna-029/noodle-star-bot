"""Pet repository operations."""

from __future__ import annotations

from datetime import datetime

from database.repositories.base import BaseRepository


class PetsRepository(BaseRepository):
    """Pet ownership and status persistence."""

    _PET_NEED_COLUMNS = {"hunger", "cleanliness", "happiness"}

    def user_owns_pet(self, user_id: int, pet_key: str) -> bool:
        """Return whether a user owns a specific pet."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM user_pets WHERE user_id = ? AND pet_key = ? LIMIT 1",
                (user_id, pet_key),
            )
            return cursor.fetchone() is not None

    def user_has_active_pet(self, user_id: int) -> bool:
        """Return whether a user currently has an active pet."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM user_pets WHERE user_id = ? AND is_active = 1 LIMIT 1",
                (user_id,),
            )
            return cursor.fetchone() is not None

    def create_user_pet(self, user_id: int, pet_key: str, pet_name: str, is_active: bool) -> None:
        """Create a newly adopted pet for a user."""
        now = datetime.now().isoformat()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_pets (
                    user_id, pet_key, pet_name, pet_nickname, hunger, cleanliness, happiness,
                    adopted_at, last_care_at, last_decay_at, is_active
                ) VALUES (?, ?, ?, NULL, 100, 100, 100, ?, ?, ?, ?)
                ON CONFLICT(user_id, pet_key) DO NOTHING
                """,
                (user_id, pet_key, pet_name, now, now, now, 1 if is_active else 0),
            )

    def get_active_pet(self, user_id: int):
        """Get the active pet row for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, pet_key, pet_name, pet_nickname, hunger, cleanliness, happiness, is_active
                FROM user_pets
                WHERE user_id = ? AND is_active = 1
                LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone()

    def get_user_pets(self, user_id: int):
        """Get all pet rows owned by a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, pet_key, pet_name, pet_nickname, hunger, cleanliness, happiness, is_active
                FROM user_pets
                WHERE user_id = ?
                ORDER BY adopted_at ASC
                """,
                (user_id,),
            )
            return cursor.fetchall()

    def get_user_pet(self, user_id: int, pet_key: str):
        """Get one pet row owned by a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, pet_key, pet_name, pet_nickname, hunger, cleanliness, happiness, is_active
                FROM user_pets
                WHERE user_id = ? AND pet_key = ?
                LIMIT 1
                """,
                (user_id, pet_key),
            )
            return cursor.fetchone()

    def set_active_pet(self, user_id: int, pet_key: str) -> None:
        """Set one pet active and deactivate the rest."""
        with self.db.get_cursor() as cursor:
            cursor.execute("UPDATE user_pets SET is_active = 0 WHERE user_id = ?", (user_id,))
            cursor.execute(
                "UPDATE user_pets SET is_active = 1 WHERE user_id = ? AND pet_key = ?",
                (user_id, pet_key),
            )

    def update_pet_nickname(self, user_id: int, pet_key: str, nickname: str | None) -> None:
        """Set or clear a pet nickname."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE user_pets SET pet_nickname = ? WHERE user_id = ? AND pet_key = ?",
                (nickname, user_id, pet_key),
            )

    def update_pet_need(self, user_id: int, pet_key: str, need: str, value: int) -> None:
        """Update one pet need stat."""
        if need not in self._PET_NEED_COLUMNS:
            raise ValueError(f"Unsupported pet need: {need}")

        now = datetime.now().isoformat()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE user_pets
                SET {need} = ?, last_care_at = ?, last_decay_at = ?
                WHERE user_id = ? AND pet_key = ?
                """,
                (max(0, min(100, value)), now, now, user_id, pet_key),
            )

    def apply_pet_decay(
        self,
        user_id: int,
        hunger_decay_per_hour: int,
        cleanliness_decay_per_hour: int,
        happiness_decay_per_hour: int,
    ) -> None:
        """Decay all owned pet stats based on elapsed time."""
        now = datetime.now()

        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, pet_key, hunger, cleanliness, happiness, last_decay_at
                FROM user_pets
                WHERE user_id = ?
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

            for row in rows:
                last_decay_raw = row["last_decay_at"]
                if not last_decay_raw:
                    continue

                try:
                    last_decay = datetime.fromisoformat(last_decay_raw)
                except ValueError:
                    continue

                elapsed_hours = int((now - last_decay).total_seconds() // 3600)
                if elapsed_hours <= 0:
                    continue

                hunger = max(0, int(row["hunger"]) - elapsed_hours * hunger_decay_per_hour)
                cleanliness = max(
                    0,
                    int(row["cleanliness"]) - elapsed_hours * cleanliness_decay_per_hour,
                )
                happiness = max(0, int(row["happiness"]) - elapsed_hours * happiness_decay_per_hour)

                cursor.execute(
                    """
                    UPDATE user_pets
                    SET hunger = ?, cleanliness = ?, happiness = ?, last_decay_at = ?
                    WHERE user_id = ? AND pet_key = ?
                    """,
                    (
                        hunger,
                        cleanliness,
                        happiness,
                        now.isoformat(),
                        row["user_id"],
                        row["pet_key"],
                    ),
                )

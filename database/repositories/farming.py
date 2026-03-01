from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database.repositories.base import BaseRepository


@dataclass
class PlantedCropRow:
    """Database row for a planted crop."""

    id: int
    user_id: int
    plot_number: int
    crop_type: str
    planted_at: datetime
    ready_at: datetime
    weather_bonus: float = 1.0  # Default no bonus


class FarmingRepository(BaseRepository):
    """Farming plot and crop operations."""

    def get_farm_level(self, user_id: int) -> int:
        """Get a user's farm level."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT farm_level FROM user_inventory WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["farm_level"] is None:
                return 1
            return row["farm_level"]

    def set_farm_level(self, user_id: int, level: int) -> None:
        """Set a user's farm level."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE user_inventory SET farm_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def get_farm_plots(self, user_id: int) -> int:
        """Get the number of farm plots a user owns."""
        with self.db.get_cursor() as cursor:
            # Check if user has inventory row, create minimal one if not
            cursor.execute(
                "SELECT farm_plots FROM user_inventory WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return 0
            if row["farm_plots"] is None:
                return 0
            return row["farm_plots"]

    def set_farm_plots(self, user_id: int, count: int) -> None:
        """Set the number of farm plots for a user."""
        with self.db.get_cursor() as cursor:
            # User should already exist from buy_plot flow, just update
            cursor.execute(
                "UPDATE user_inventory SET farm_plots = ? WHERE user_id = ?",
                (count, user_id),
            )

    def get_planted_crops(self, user_id: int) -> list[PlantedCropRow]:
        """Get all planted crops for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, plot_number, crop_type, planted_at, ready_at,
                       COALESCE(weather_bonus, 1.0) as weather_bonus
                FROM planted_crops
                WHERE user_id = ?
                ORDER BY plot_number
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            return [
                PlantedCropRow(
                    id=row["id"],
                    user_id=row["user_id"],
                    plot_number=row["plot_number"],
                    crop_type=row["crop_type"],
                    planted_at=datetime.fromisoformat(row["planted_at"]),
                    ready_at=datetime.fromisoformat(row["ready_at"]),
                    weather_bonus=float(row["weather_bonus"]),
                )
                for row in rows
            ]

    def get_planted_crop(self, user_id: int, plot_number: int) -> Optional[PlantedCropRow]:
        """Get a specific planted crop by plot number."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, plot_number, crop_type, planted_at, ready_at,
                       COALESCE(weather_bonus, 1.0) as weather_bonus
                FROM planted_crops
                WHERE user_id = ? AND plot_number = ?
                """,
                (user_id, plot_number),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return PlantedCropRow(
                id=row["id"],
                user_id=row["user_id"],
                plot_number=row["plot_number"],
                crop_type=row["crop_type"],
                planted_at=datetime.fromisoformat(row["planted_at"]),
                ready_at=datetime.fromisoformat(row["ready_at"]),
                weather_bonus=float(row["weather_bonus"]),
            )

    def plant_crop(
        self,
        user_id: int,
        plot_number: int,
        crop_type: str,
        planted_at: datetime,
        ready_at: datetime,
    ) -> None:
        """Plant a crop in a plot."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO planted_crops (user_id, plot_number, crop_type, planted_at, ready_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, plot_number) DO UPDATE SET
                    crop_type = excluded.crop_type,
                    planted_at = excluded.planted_at,
                    ready_at = excluded.ready_at
                """,
                (user_id, plot_number, crop_type, planted_at.isoformat(), ready_at.isoformat()),
            )

    def remove_crop(self, user_id: int, plot_number: int) -> None:
        """Remove a crop from a plot (after harvest)."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM planted_crops WHERE user_id = ? AND plot_number = ?",
                (user_id, plot_number),
            )

    def remove_crops(self, user_id: int, plot_numbers: list[int]) -> None:
        """Remove multiple crops at once."""
        if not plot_numbers:
            return
        with self.db.get_cursor() as cursor:
            placeholders = ",".join("?" * len(plot_numbers))
            cursor.execute(
                f"DELETE FROM planted_crops WHERE user_id = ? AND plot_number IN ({placeholders})",
                (user_id, *plot_numbers),
            )

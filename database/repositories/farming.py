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


@dataclass
class FarmPlotStateRow:
    """Database row for persistent per-plot farm state."""

    user_id: int
    plot_number: int
    soil_condition: int = 100
    last_crop_type: Optional[str] = None
    same_crop_streak: int = 0


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
            # Ensure plot state rows exist for all owned plots.
            for plot_number in range(1, count + 1):
                cursor.execute(
                    """
                    INSERT INTO farm_plot_state (user_id, plot_number, soil_condition, last_crop_type, same_crop_streak)
                    VALUES (?, ?, 100, NULL, 0)
                    ON CONFLICT(user_id, plot_number) DO NOTHING
                    """,
                    (user_id, plot_number),
                )

    def get_plot_states(self, user_id: int) -> dict[int, FarmPlotStateRow]:
        """Get all persistent plot states for a user keyed by plot number."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, plot_number, COALESCE(soil_condition, 100) AS soil_condition,
                       last_crop_type, COALESCE(same_crop_streak, 0) AS same_crop_streak
                FROM farm_plot_state
                WHERE user_id = ?
                ORDER BY plot_number
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            return {
                int(row["plot_number"]): FarmPlotStateRow(
                    user_id=int(row["user_id"]),
                    plot_number=int(row["plot_number"]),
                    soil_condition=int(row["soil_condition"]),
                    last_crop_type=row["last_crop_type"],
                    same_crop_streak=int(row["same_crop_streak"]),
                )
                for row in rows
            }

    def get_plot_state(self, user_id: int, plot_number: int) -> FarmPlotStateRow:
        """Get persistent state for one plot, creating a default row if missing."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO farm_plot_state (user_id, plot_number, soil_condition, last_crop_type, same_crop_streak)
                VALUES (?, ?, 100, NULL, 0)
                ON CONFLICT(user_id, plot_number) DO NOTHING
                """,
                (user_id, plot_number),
            )
            cursor.execute(
                """
                SELECT user_id, plot_number, COALESCE(soil_condition, 100) AS soil_condition,
                       last_crop_type, COALESCE(same_crop_streak, 0) AS same_crop_streak
                FROM farm_plot_state
                WHERE user_id = ? AND plot_number = ?
                """,
                (user_id, plot_number),
            )
            row = cursor.fetchone()
            return FarmPlotStateRow(
                user_id=int(row["user_id"]),
                plot_number=int(row["plot_number"]),
                soil_condition=int(row["soil_condition"]),
                last_crop_type=row["last_crop_type"],
                same_crop_streak=int(row["same_crop_streak"]),
            )

    def set_plot_soil_condition(self, user_id: int, plot_number: int, soil_condition: int) -> None:
        """Set soil condition for a plot."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO farm_plot_state (user_id, plot_number, soil_condition, last_crop_type, same_crop_streak)
                VALUES (?, ?, ?, NULL, 0)
                ON CONFLICT(user_id, plot_number) DO UPDATE SET
                    soil_condition = excluded.soil_condition
                """,
                (user_id, plot_number, soil_condition),
            )

    def set_plot_crop_streak(
        self,
        user_id: int,
        plot_number: int,
        crop_type: str,
        same_crop_streak: int,
    ) -> None:
        """Set crop history fields used for rotation penalties."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO farm_plot_state (user_id, plot_number, soil_condition, last_crop_type, same_crop_streak)
                VALUES (?, ?, 100, ?, ?)
                ON CONFLICT(user_id, plot_number) DO UPDATE SET
                    last_crop_type = excluded.last_crop_type,
                    same_crop_streak = excluded.same_crop_streak
                """,
                (user_id, plot_number, crop_type, same_crop_streak),
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

    def force_ready_all_crops(self, user_id: int, ready_at: Optional[datetime] = None) -> int:
        """Force all currently growing crops for a user to be ready now.

        Returns the number of crops that were still growing and got updated.
        """
        target_ready_at = ready_at or datetime.now()
        target_iso = target_ready_at.isoformat()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE planted_crops
                SET ready_at = ?
                WHERE user_id = ? AND ready_at > ?
                """,
                (target_iso, user_id, target_iso),
            )
            return max(0, cursor.rowcount or 0)

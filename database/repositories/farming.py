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


class FarmingRepository(BaseRepository):
    """Farming plot and crop operations."""

    def _ensure_inventory_row(self, cursor, user_id: int) -> None:
        """Ensure user has an inventory row (reuse from other repos)."""
        cursor.execute(
            """
            INSERT INTO user_inventory (
                user_id, gold_pickaxe, helmet, sword, raw_potato, golden_mushroom,
                bait_worm, bait_herring, bait_sturgeon, equipped_bait, telescope,
                mine_level, active_mine_level, active_fish_level, golden_axe, mithril_shield,
                bank_insurance, farm_plots
            ) VALUES (?, 0, 0, 0, 0, 0, 0, 0, 0, NULL, 0, 1, 1, 1, 0, 0, 0, 0)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )

    def get_farm_plots(self, user_id: int) -> int:
        """Get the number of farm plots a user owns."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                "SELECT farm_plots FROM user_inventory WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["farm_plots"] is None:
                return 0
            return row["farm_plots"]

    def set_farm_plots(self, user_id: int, count: int) -> None:
        """Set the number of farm plots for a user."""
        with self.db.get_cursor() as cursor:
            self._ensure_inventory_row(cursor, user_id)
            cursor.execute(
                "UPDATE user_inventory SET farm_plots = ? WHERE user_id = ?",
                (count, user_id),
            )

    def get_planted_crops(self, user_id: int) -> list[PlantedCropRow]:
        """Get all planted crops for a user."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, plot_number, crop_type, planted_at, ready_at
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
                )
                for row in rows
            ]

    def get_planted_crop(self, user_id: int, plot_number: int) -> Optional[PlantedCropRow]:
        """Get a specific planted crop by plot number."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, plot_number, crop_type, planted_at, ready_at
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

"""Progression repository operations."""
from database.repositories.base import BaseRepository

class ProgressionRepository(BaseRepository):
    """Player progression state (user_progression table)."""

    def _ensure_progression_row(self, cursor, user_id: int) -> None:
        cursor.execute(
            "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
            (user_id,),
        )

    def get_progression(self, user_id: int) -> dict:
        """Get all progression data as a dict."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                """SELECT mine_level, active_mine_level, active_fish_level,
                          space_planet_level, active_space_planet,
                          farm_level, farm_plots, first_weather_bonus,
                          inventory_capacity, equipped_bait, jig_active,
                          preserver_level, preserver_pending_stars, preserver_ready_ts,
                          growbot_level
                   FROM user_progression WHERE user_id = ?""",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return self._default_progression()
            return {
                "mine_level": row["mine_level"] or 1,
                "active_mine_level": row["active_mine_level"] or 1,
                "active_fish_level": row["active_fish_level"] or 1,
                "space_planet_level": row["space_planet_level"] or 0,
                "active_space_planet": row["active_space_planet"] or 0,
                "farm_level": row["farm_level"] or 1,
                "farm_plots": row["farm_plots"] or 0,
                "first_weather_bonus": row["first_weather_bonus"] or 0,
                "inventory_capacity": row["inventory_capacity"] or 50,
                "equipped_bait": row["equipped_bait"],
                "jig_active": row["jig_active"] or 0,
                "preserver_level": row["preserver_level"] or 0,
                "preserver_pending_stars": row["preserver_pending_stars"] or 0,
                "preserver_ready_ts": row["preserver_ready_ts"] or 0,
                "growbot_level": row["growbot_level"] or 0,
            }

    def _default_progression(self) -> dict:
        return {
            "mine_level": 1, "active_mine_level": 1, "active_fish_level": 1,
            "space_planet_level": 0, "active_space_planet": 0,
            "farm_level": 1, "farm_plots": 0, "first_weather_bonus": 0,
            "inventory_capacity": 50, "equipped_bait": None, "jig_active": 0,
            "preserver_level": 0, "preserver_pending_stars": 0,
            "preserver_ready_ts": 0, "growbot_level": 0,
        }

    def update_progression(self, user_id: int, field: str, value) -> None:
        """Update a single progression field."""
        _VALID_FIELDS = {
            "mine_level", "active_mine_level", "active_fish_level",
            "space_planet_level", "active_space_planet",
            "farm_level", "farm_plots", "first_weather_bonus",
            "inventory_capacity", "equipped_bait", "jig_active",
            "preserver_level", "preserver_pending_stars", "preserver_ready_ts",
            "growbot_level",
        }
        if field not in _VALID_FIELDS:
            raise ValueError(f"Invalid progression field: {field}")
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                f"UPDATE user_progression SET {field} = ? WHERE user_id = ?",
                (value, user_id),
            )

    def get_inventory_capacity(self, user_id: int) -> int:
        """Get user's inventory capacity."""
        with self.db.get_cursor() as cursor:
            self._ensure_progression_row(cursor, user_id)
            cursor.execute(
                "SELECT inventory_capacity FROM user_progression WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return row["inventory_capacity"] if row else 50

    def set_inventory_capacity(self, user_id: int, capacity: int) -> None:
        """Set user's inventory capacity (for bag upgrades)."""
        self.update_progression(user_id, "inventory_capacity", capacity)

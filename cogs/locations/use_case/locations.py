"""Location use-cases for travel and location checks."""

from datetime import datetime
from typing import Optional

from cogs.locations.constants import (
    DEFAULT_LOCATION,
    LOCATIONS,
    TRAVEL_COOLDOWN_SECONDS,
)
from cogs.locations.dto import TravelResult
from database.repositories.base import BaseRepository


class LocationUseCases(BaseRepository):
    """Handles location and travel logic."""

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

    def get_location(self, user_id: int) -> str:
        """Get user's current location key."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                "SELECT current_location FROM user_activity WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None or row["current_location"] is None:
                return DEFAULT_LOCATION
            return row["current_location"]

    def _get_last_travel(self, cursor, user_id: int) -> Optional[datetime]:
        cursor.execute(
            "SELECT last_travel FROM user_activity WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None or row["last_travel"] is None:
            return None
        return datetime.fromisoformat(row["last_travel"])

    def travel(self, user_id: int, destination: str) -> TravelResult:
        """Travel to a new location."""
        if destination not in LOCATIONS:
            return TravelResult(
                success=False,
                message="That location doesn't exist!",
            )

        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)

            # Check current location
            cursor.execute(
                "SELECT current_location, last_travel FROM user_activity WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            current = row["current_location"] or DEFAULT_LOCATION

            if current == destination:
                loc = LOCATIONS[destination]
                return TravelResult(
                    success=False,
                    message=f"You're already at **{loc.name}** {loc.emoji}!",
                    destination=destination,
                )

            # Check cooldown (free to return to noodle_town)
            if destination != "noodle_town":
                last_travel = None
                if row["last_travel"]:
                    last_travel = datetime.fromisoformat(row["last_travel"])

                if last_travel is not None:
                    elapsed = (datetime.now() - last_travel).total_seconds()
                    remaining = TRAVEL_COOLDOWN_SECONDS - elapsed
                    if remaining > 0:
                        return TravelResult(
                            success=False,
                            message=f"You need to rest before traveling again! **{int(remaining)}s** remaining.",
                            cooldown_remaining=int(remaining),
                        )

            # Update location and cooldown
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE user_activity SET current_location = ?, last_travel = ? WHERE user_id = ?",
                (destination, now, user_id),
            )

            loc = LOCATIONS[destination]
            return TravelResult(
                success=True,
                message=f"You traveled to **{loc.name}** {loc.emoji}!",
                destination=destination,
            )

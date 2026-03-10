"""Composed farming use-case facade."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from database.repository import UserRepository

from .crop_flow import CropFlowMixin
from .growbot import GrowBotMixin
from .preserver import PreserverMixin
from .progression import FarmProgressionMixin
from .tending import TendingMixin


class FarmingUseCases(
    FarmProgressionMixin,
    PreserverMixin,
    CropFlowMixin,
    TendingMixin,
    GrowBotMixin,
):
    """Handles all farming-related business logic via focused mixins."""

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repo = repository or UserRepository()

    def force_grow_all_crops(self, user_id: int) -> int:
        """Developer/testing helper: mark all active crops as ready for harvest."""
        return self.repo.force_ready_all_crops(user_id)

    def force_finish_preserver(self, user_id: int) -> tuple[bool, int]:
        """Developer/testing helper: finish active preserver processing immediately."""
        inventory = self.repo.get_user_inventory(user_id)
        pending_stars = int(inventory.get("preserver_pending_stars", 0) or 0)
        ready_ts = int(inventory.get("preserver_ready_ts", 0) or 0)
        now_ts = int(datetime.now().timestamp())

        if pending_stars <= 0 or ready_ts <= now_ts:
            return False, pending_stars

        self.repo.update_user_inventory(user_id, "preserver_ready_ts", now_ts)
        return True, pending_stars

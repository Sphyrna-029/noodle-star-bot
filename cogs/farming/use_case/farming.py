"""Composed farming use-case facade."""

from __future__ import annotations

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

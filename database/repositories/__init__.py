"""Composable repository mixins for user database operations."""

from database.repositories.base import BaseRepository
from database.repositories.achievements import AchievementsRepository
from database.repositories.economy import EconomyRepository
from database.repositories.farming import FarmingRepository
from database.repositories.fishing import FishingRepository
from database.repositories.gambling import GamblingRepository
from database.repositories.inventory import InventoryRepository
from database.repositories.mining import MiningRepository
from database.repositories.pets import PetsRepository
from database.repositories.user_core import UserCoreRepository

__all__ = [
    "BaseRepository",
    "AchievementsRepository",
    "UserCoreRepository",
    "EconomyRepository",
    "InventoryRepository",
    "MiningRepository",
    "FishingRepository",
    "GamblingRepository",
    "FarmingRepository",
    "PetsRepository",
]

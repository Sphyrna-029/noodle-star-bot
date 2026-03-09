"""Composed user repository interface."""

from database.repositories import (
    AchievementsRepository,
    EconomyRepository,
    FarmingRepository,
    FishingRepository,
    GamblingRepository,
    InventoryRepository,
    MiningRepository,
    PetsRepository,
    UserCoreRepository,
)


class UserRepository(
    AchievementsRepository,
    UserCoreRepository,
    EconomyRepository,
    InventoryRepository,
    MiningRepository,
    FishingRepository,
    GamblingRepository,
    FarmingRepository,
    PetsRepository,
):
    """Unified repository composed from smaller domain repositories."""

    def __init__(self):
        super().__init__()

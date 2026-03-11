"""Composed user repository interface."""

from database.repositories import (
    AchievementsRepository,
    CombatRepository,
    EconomyRepository,
    EquipmentRepository,
    FarmingRepository,
    FishingRepository,
    GamblingRepository,
    InventoryRepository,
    InventoryItemsRepository,
    MiningRepository,
    PetsRepository,
    ProgressionRepository,
    UserCoreRepository,
)


class UserRepository(
    AchievementsRepository,
    CombatRepository,
    UserCoreRepository,
    EconomyRepository,
    EquipmentRepository,
    InventoryRepository,
    InventoryItemsRepository,
    MiningRepository,
    FishingRepository,
    GamblingRepository,
    FarmingRepository,
    PetsRepository,
    ProgressionRepository,
):
    """Unified repository composed from smaller domain repositories."""

    def __init__(self):
        super().__init__()

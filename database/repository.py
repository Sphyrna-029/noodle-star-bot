"""Composed user repository interface."""

from database.repositories import (
    AchievementsRepository,
    AetherdepthsRepository,
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
    StorageRepository,
    UserCoreRepository,
)


class UserRepository(
    AchievementsRepository,
    AetherdepthsRepository,
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
    StorageRepository,
):
    """Unified repository composed from smaller domain repositories."""

    def __init__(self):
        super().__init__()

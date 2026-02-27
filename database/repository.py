"""Composed user repository interface."""

from database.repositories import (
    EconomyRepository,
    FishingRepository,
    GamblingRepository,
    InventoryRepository,
    MiningRepository,
    UserCoreRepository,
)


class UserRepository(
    UserCoreRepository,
    EconomyRepository,
    InventoryRepository,
    MiningRepository,
    FishingRepository,
    GamblingRepository,
):
    """Unified repository composed from smaller domain repositories."""

    def __init__(self):
        super().__init__()

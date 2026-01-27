"""Service layer for Noodle Star Bot."""

from .economy import EconomyService
from .fishing import FishingService
from .gambling import GamblingService
from .mining import MiningService
from .shop import ShopService
from .trading import TradeService

__all__ = [
    "EconomyService",
    "FishingService",
    "GamblingService",
    "MiningService",
    "ShopService",
    "TradeService",
]

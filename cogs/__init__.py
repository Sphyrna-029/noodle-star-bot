"""Discord Cogs for Noodle Star Bot."""

from .economy.handlers import EconomyCog
from .fishing.handlers import FishingCog
from .gambling.handlers import GamblingCog
from .mining.handlers import MiningCog
from .moderator.handlers import ModeratorCog
from .shop.handlers import ShopCog

__all__ = [
    "EconomyCog",
    "FishingCog",
    "GamblingCog",
    "MiningCog",
    "ModeratorCog",
    "ShopCog",
]

from _typeshed import OpenBinaryMode
from datetime import timedelta
from typing import Final, Optional

from .models import BaitTier, CatchBucket, Mineral, ShopItem

# db
DATABASE_FILE: Final[str]
TABLE_NAME: Final[str]

# bot
COMMAND_PREFIX: Final[str]

# economy
STARTING_STARS: Final[int]
STARTING_BANK: Final[int]
BANKING_DEPOSIT_COOLDOWN_MINUTES: Final[int]
BANKING_WITHDRAW_COOLDOWN_MINUTES: Final[int]

# gambling
GAMBLE_DICE_SIDES: Final[int]
GAMBLE_WIN_TARGET: Final[int]
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]]

COINFLIP_WIN_MULTIPLIER: Final[float]
COINFLIP_MIN_BET: Final[int]

DUEL_DICE_SIDES: Final[int]
DUEL_STAMINA_MAX: Final[int]
DUEL_STAMINA_BASE_COST: Final[int]
DUEL_STAMINA_COST_PER_50: Final[int]
DUEL_STAMINA_REGEN_BASE_MINUTES: Final[int]
DUEL_STAMINA_REGEN_AMOUNT_DIVISOR: Final[int]
DUEL_STAMINA_REGEN_MAX_EXTRA_MINUTES: Final[int]

# mining
MINING_BASE_COOLDOWN: Final[timedelta]
MINING_POTATO_COOLDOWN: Final[timedelta]
MINING_DISASTER_CHANCE: Final[float]
MINING_COLLAPSE_LOSS_PERCENT: Final[float]
MINING_GOBLIN_LOSS_PERCENT: Final[float]
MINERALS_NORMAL: Final[tuple[Mineral, ...]]
MINERALS_GOLD_PICKAXE: Final[tuple[Mineral, ...]]
MINE_LEVELS: Final[dict[int, dict]]

# fishing
FISHING_COOLDOWN: Final[timedelta]
FISHING_BAIT_TIERS: Final[dict[str, BaitTier]]
FISHING_CATCH_TABLE: Final[dict[str, CatchBucket]]
FISH_LEVELS: Final[dict[int, dict]]

# shop
SHOP_ITEMS: Final[dict[str, ShopItem]]

def get_item_by_alias(alias: str) -> Optional[tuple[str, ShopItem]]: ...

from dataclasses import dataclass
from datetime import timedelta
from typing import Final

__all__ = ["Mineral", "MineHazard", "ShopItem", "BaitTier", "Catch", "CatchBucket"]


@dataclass(frozen=True, slots=True)
class Mineral:
    name: str
    emoji: str
    stars: int
    weight: int


@dataclass(frozen=True, slots=True)
class MineHazard:
    name: str
    emoji: str
    header: str
    wallet_loss_pct: float
    bank_loss_pct: float
    protection_item: str  # "helmet" or "sword"
    protected_msg: str
    unprotected_msg: str


@dataclass(frozen=True, slots=True)
class ShopItem:
    price: int
    db_column: str
    consumable: bool
    emoji: str
    display_name: str
    description: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BaitTier:
    emoji: str
    display_name: str
    bite_wait_min: timedelta
    bite_wait_max: timedelta
    pull_window: timedelta
    rare_boost: float


@dataclass(frozen=True, slots=True)
class Catch:
    name: str
    emoji: str
    stars: int
    weight: int


@dataclass(frozen=True, slots=True)
class CatchBucket:
    weight: int
    catches: tuple[Catch, ...]

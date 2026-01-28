from dataclasses import dataclass
from datetime import timedelta
from typing import Final

__all__ = ["Mineral", "ShopItem", "BaitTier", "Catch", "CatchBucket"]


@dataclass(frozen=True, slots=True)
class Mineral:
    name: str
    emoji: str
    stars: int
    weight: int


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

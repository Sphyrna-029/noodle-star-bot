from datetime import timedelta
from typing import Final

from .models import Mineral

__all__ = [
    "MINING_BASE_COOLDOWN",
    "MINING_POTATO_COOLDOWN",
    "MINING_DISASTER_CHANCE",
    "MINING_COLLAPSE_LOSS_PERCENT",
    "MINING_GOBLIN_LOSS_PERCENT",
    "MINERALS_NORMAL",
    "MINERALS_GOLD_PICKAXE",
]

MINING_BASE_COOLDOWN: Final[timedelta] = timedelta(minutes=30)
MINING_POTATO_COOLDOWN: Final[timedelta] = timedelta(minutes=5)

MINING_DISASTER_CHANCE: Final[float] = 0.10
MINING_COLLAPSE_LOSS_PERCENT: Final[float] = 0.50
MINING_GOBLIN_LOSS_PERCENT: Final[float] = 0.75

MINERALS_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Stone", "🪨", 5, 40),
    Mineral("Coal", "⚫", 10, 30),
    Mineral("Iron", "⚙️", 20, 15),
    Mineral("Gold", "🟡", 40, 10),
    Mineral("Diamond", "💎", 100, 5),
)

MINERALS_GOLD_PICKAXE: Final[tuple[Mineral, ...]] = (
    Mineral("Stone", "🪨", 5, 30),
    Mineral("Coal", "⚫", 10, 25),
    Mineral("Iron", "⚙️", 20, 20),
    Mineral("Gold", "🟡", 40, 15),
    Mineral("Diamond", "💎", 100, 10),
)

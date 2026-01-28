from typing import Final

__all__ = [
    "GAMBLE_DICE_SIDES",
    "GAMBLE_WIN_TARGET",
    "GAMBLE_MULTIPLIER_CDF",
    "COINFLIP_WIN_MULTIPLIER",
    "COINFLIP_MIN_BET",
    "DUEL_DICE_SIDES",
]

GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (20, 0.01),
    (5, 0.34),
    (7, 0.67),
    (8, 1.00),
)

GAMBLE_DICE_SIDES: Final[int] = 7
GAMBLE_WIN_TARGET: Final[int] = 7
COINFLIP_WIN_MULTIPLIER: Final[float] = 1.95
COINFLIP_MIN_BET: Final[int] = 20

DUEL_DICE_SIDES: Final[int] = 20

from typing import Final

__all__ = [
    "GAMBLE_DICE_SIDES",
    "GAMBLE_WIN_TARGET",
    "GAMBLE_MULTIPLIER_CDF",
    "COINFLIP_WIN_MULTIPLIER",
    "COINFLIP_MIN_BET",
    "DUEL_DICE_SIDES",
    "DUEL_STAMINA_MAX",
    "DUEL_STAMINA_BASE_COST",
    "DUEL_STAMINA_COST_PER_50",
    "DUEL_STAMINA_REGEN_BASE_MINUTES",
    "DUEL_STAMINA_REGEN_AMOUNT_DIVISOR",
    "DUEL_STAMINA_REGEN_MAX_EXTRA_MINUTES",
    "BLACKJACK_DECKS",
    "BLACKJACK_PAYOUT",
    "BLACKJACK_WIN_MULTIPLIER",
]

# -- Gambling
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (20, 0.01),
    (5, 0.34),
    (7, 0.67),
    (8, 1.00),
)
GAMBLE_DICE_SIDES: Final[int] = 7
GAMBLE_WIN_TARGET: Final[int] = 7

# -- Coinflip
COINFLIP_WIN_MULTIPLIER: Final[float] = 1.95
COINFLIP_MIN_BET: Final[int] = 20

# -- Dueling
DUEL_DICE_SIDES: Final[int] = 20
DUEL_STAMINA_MAX: Final[int] = 100
DUEL_STAMINA_BASE_COST: Final[int] = 8
DUEL_STAMINA_COST_PER_50: Final[int] = 25
DUEL_STAMINA_REGEN_BASE_MINUTES: Final[int] = 10
DUEL_STAMINA_REGEN_AMOUNT_DIVISOR: Final[int] = 100
DUEL_STAMINA_REGEN_MAX_EXTRA_MINUTES: Final[int] = 20

# -- BlackJack
BLACKJACK_DECKS: Final[int] = 2
BLACKJACK_PAYOUT: Final[float] = 1.5  # 3:2 payout for natural blackjack
BLACKJACK_WIN_MULTIPLIER: Final[float] = 1.0  # 1:1 payout for normal win
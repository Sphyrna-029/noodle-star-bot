from typing import Final

__all__ = [
    "GAMBLE_DICE_SIDES",
    "GAMBLE_WIN_TARGET",
    "GAMBLE_MULTIPLIER_CDF",
    "COINFLIP_WIN_MULTIPLIER",
    "COINFLIP_MIN_BET",
    "DUEL_INVITE_TIMEOUT",
    "DUEL_TURN_TIMEOUT",
    "BLACKJACK_DECKS",
    "BLACKJACK_PAYOUT",
    "BLACKJACK_WIN_MULTIPLIER",
    "BLACKJACK_MIN_BET",
    "BLACKJACK_COOLDOWN_SECONDS",
    "ROULETTE_CHAMBERS",
    "ROULETTE_INVITE_TTL_HOURS",
    "RUSSIAN_TURN_TIMEOUT_SECONDS",
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

# -- PvP Duel
DUEL_INVITE_TIMEOUT: Final[int] = 60      # seconds before invite expires
DUEL_TURN_TIMEOUT: Final[int] = 300       # seconds (5 min) per turn

# -- BlackJack
BLACKJACK_DECKS: Final[int] = 2
BLACKJACK_PAYOUT: Final[float] = 1.5  # 3:2 payout for natural blackjack
BLACKJACK_WIN_MULTIPLIER: Final[float] = 1.0  # 1:1 payout for normal win
BLACKJACK_MIN_BET: Final[int] = 20
BLACKJACK_COOLDOWN_SECONDS: Final[int] = 30

# -- Russian Roulette
ROULETTE_CHAMBERS: Final[int] = 6
ROULETTE_INVITE_TTL_HOURS: Final[int] = 6
RUSSIAN_TURN_TIMEOUT_SECONDS: Final[int] = 3600

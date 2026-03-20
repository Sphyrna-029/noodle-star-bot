from typing import Final

__all__ = [
    "GAMBLE_TIER_CDF",
    "COINFLIP_WIN_MULTIPLIER",
    "COINFLIP_MIN_BET",
    "DUEL_INVITE_TIMEOUT",
    "DUEL_TURN_TIMEOUT",
    "DUEL_PLAYER_CLOCK",
    "BLACKJACK_DECKS",
    "BLACKJACK_PAYOUT",
    "BLACKJACK_WIN_MULTIPLIER",
    "BLACKJACK_MIN_BET",
    "BLACKJACK_COOLDOWN_SECONDS",
    "ROULETTE_CHAMBERS",
    "ROULETTE_INVITE_TTL_HOURS",
    "RUSSIAN_TURN_TIMEOUT_SECONDS",
    "PICKPOCKET_DICE_SIDES",
    "PICKPOCKET_STAMINA_MAX",
    "PICKPOCKET_STAMINA_BASE_COST",
    "PICKPOCKET_STAMINA_COST_PER_50",
    "PICKPOCKET_STAMINA_REGEN_BASE_MINUTES",
    "PICKPOCKET_STAMINA_REGEN_AMOUNT_DIVISOR",
    "PICKPOCKET_STAMINA_REGEN_MAX_EXTRA_MINUTES",
]

# -- Gambling  (single-roll tier system, 4% house edge, EV = 0.96)
# Format: (multiplier, cumulative_probability)
# Probabilities: 100x 0.05%, 50x 0.10%, 25x 0.40%, 10x 1.50%, 3x 7%, 2x 20%, loss 70.95%
GAMBLE_TIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (100, 0.0005),
    (50, 0.0015),
    (25, 0.0055),
    (10, 0.0205),
    (3, 0.0905),
    (2, 0.2905),
    (0, 1.0),
)

# -- Coinflip
COINFLIP_WIN_MULTIPLIER: Final[float] = 1.95
COINFLIP_MIN_BET: Final[int] = 20

# -- PvP Duel
DUEL_INVITE_TIMEOUT: Final[int] = 60      # seconds before invite expires
DUEL_TURN_TIMEOUT: Final[int] = 600       # seconds — safety net for entire view
DUEL_PLAYER_CLOCK: Final[int] = 180       # seconds — per-player time bank

# -- BlackJack
BLACKJACK_DECKS: Final[int] = 2
BLACKJACK_PAYOUT: Final[float] = 1.5  # 3:2 payout for natural blackjack
BLACKJACK_WIN_MULTIPLIER: Final[float] = 1.0  # 1:1 payout for normal win
BLACKJACK_MIN_BET: Final[int] = 20
BLACKJACK_COOLDOWN_SECONDS: Final[int] = 30

# -- Pickpocket
PICKPOCKET_DICE_SIDES: Final[int] = 20
PICKPOCKET_STAMINA_MAX: Final[int] = 100
PICKPOCKET_STAMINA_BASE_COST: Final[int] = 8
PICKPOCKET_STAMINA_COST_PER_50: Final[int] = 25
PICKPOCKET_STAMINA_REGEN_BASE_MINUTES: Final[int] = 10
PICKPOCKET_STAMINA_REGEN_AMOUNT_DIVISOR: Final[int] = 100
PICKPOCKET_STAMINA_REGEN_MAX_EXTRA_MINUTES: Final[int] = 20

# -- Russian Roulette
ROULETTE_CHAMBERS: Final[int] = 6
ROULETTE_INVITE_TTL_HOURS: Final[int] = 6
RUSSIAN_TURN_TIMEOUT_SECONDS: Final[int] = 3600

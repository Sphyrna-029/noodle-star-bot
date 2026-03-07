"""DTOs for gambling use-cases."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


@dataclass(slots=True)
class GambleResult:
    """Result of a gambling operation."""

    success: bool
    won: bool
    message: str
    roll: int = 0
    multiplier: float = 0
    amount_changed: int = 0
    new_balance: int = 0


@dataclass(slots=True)
class CoinflipResult:
    """Result of a coinflip."""

    success: bool
    won: bool
    message: str
    result: str = ""
    amount_changed: int = 0
    new_balance: int = 0


@dataclass(slots=True)
class DuelResult:
    """Result of a duel."""

    success: bool
    message: str
    challenger_roll: int = 0
    opponent_roll: int = 0
    winner_id: Optional[int] = None
    amount: int = 0
    challenger_new_balance: int = 0
    opponent_new_balance: int = 0
    stamina_cost: int = 0
    challenger_stamina_before: int = 0
    challenger_stamina_after: int = 0


@dataclass(slots=True)
class RouletteInviteResult:
    """Result payload for PvP invite actions."""

    success: bool
    message: str
    amount: int = 0
    inviter_id: int = 0
    opponent_id: int = 0
    expires_at: Optional[str] = None


@dataclass(slots=True)
class RoulettePvpResult:
    """Result payload for completed PvP roulette games."""

    success: bool
    message: str
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    amount: int = 0
    bullet_chamber: int = 0
    trigger_log: list[int] = None
    challenger_wallet: int = 0
    challenger_bank: int = 0
    opponent_wallet: int = 0
    opponent_bank: int = 0

    def __post_init__(self):
        if self.trigger_log is None:
            self.trigger_log = []


@dataclass(slots=True)
class BlackJackResult:
    """Result of BlackJack."""

    success: bool
    message: str
    won: Optional[bool] = None
    game_over: bool = False
    player_hand: list = None
    dealer_hand: list = None
    player_value: int = 0
    dealer_value: int = 0
    amount_changed: int = 0
    new_balance: int = 0
    is_blackjack: bool = False
    is_bust: bool = False
    deck: list = None

    def __post_init__(self):
        if self.player_hand is None:
            self.player_hand = []
        if self.dealer_hand is None:
            self.dealer_hand = []
        if self.deck is None:
            self.deck = []


class BlackJackSuits(IntEnum):
    CLUB = 0
    DIAMOND = 1
    HEART = 2
    SPADE = 3


@dataclass(frozen=True, slots=True)
class BlackJackCard:
    rank: int
    suit: BlackJackSuits

    def get_value(self) -> int:
        """Get the value of the card (Ace=11, Face=10)."""
        if self.rank >= 11:  # Jack, Queen, King
            return 10
        return self.rank

    def get_display_rank(self) -> str:
        """Get display string for card rank."""
        if self.rank == 14:
            return "A"
        elif self.rank == 13:
            return "K"
        elif self.rank == 12:
            return "Q"
        elif self.rank == 11:
            return "J"
        return str(self.rank)

    def get_suit_emoji(self) -> str:
        """Get emoji representation of suit."""
        suit_map = {
            BlackJackSuits.CLUB: "♣️",
            BlackJackSuits.DIAMOND: "♦️",
            BlackJackSuits.HEART: "♥️",
            BlackJackSuits.SPADE: "♠️",
        }
        return suit_map[self.suit]

    def __str__(self) -> str:
        return f"{self.get_display_rank()}{self.get_suit_emoji()}"


@dataclass(slots=True)
class BlackJackGameState:
    """State of an active blackjack game."""

    user_id: int
    username: str
    bet_amount: int
    deck: list
    player_hand: list
    dealer_hand: list
    game_over: bool = False

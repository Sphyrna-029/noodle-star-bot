"""DTOs for gambling use-cases."""

from dataclasses import dataclass, field
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
class DuelState:
    """Mutable state during a PvP duel."""

    p1_id: int
    p1_name: str
    p2_id: int
    p2_name: str
    wager: int
    # P1 combat stats
    p1_hp: int
    p1_max_hp: int
    p1_stamina: int
    p1_max_stamina: int
    p1_attack: int
    p1_defense: int
    # P2 combat stats
    p2_hp: int
    p2_max_hp: int
    p2_stamina: int
    p2_max_stamina: int
    p2_attack: int
    p2_defense: int
    # Tracking
    turn: int = 0
    turns: list = field(default_factory=list)
    active_player: int = 0  # user ID of whose turn it is
    finished: bool = False
    winner_id: int | None = None
    # Defend flags — cleared after opponent's next attack
    p1_defending: bool = False
    p2_defending: bool = False


@dataclass(slots=True)
class DuelResult:
    """Result of a completed PvP duel."""

    success: bool
    message: str
    winner_id: int | None = None
    loser_id: int | None = None
    amount: int = 0
    winner_new_balance: int = 0
    loser_new_balance: int = 0
    unlocked_achievement_keys: list[str] = None

    def __post_init__(self):
        if self.unlocked_achievement_keys is None:
            self.unlocked_achievement_keys = []


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
    game_over: bool = False
    fired: bool = False
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    amount: int = 0
    bullet_chamber: int = 0
    selected_chamber: int = 0
    next_turn_user_id: Optional[int] = None
    trigger_log: list[tuple[int, int, bool]] = None
    challenger_wallet: int = 0
    challenger_bank: int = 0
    opponent_wallet: int = 0
    opponent_bank: int = 0
    unlocked_achievements: list[tuple[int, str]] = None

    def __post_init__(self):
        if self.trigger_log is None:
            self.trigger_log = []
        if self.unlocked_achievements is None:
            self.unlocked_achievements = []


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

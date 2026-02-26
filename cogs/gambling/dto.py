"""DTOs for gambling use-cases."""

from dataclasses import dataclass
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

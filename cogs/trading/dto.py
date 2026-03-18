"""DTOs for trading use-cases."""

from dataclasses import dataclass, field
from enum import Enum


class TradeState(Enum):
    """States for the trade state machine."""

    EDITING = "editing"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TradeOffer:
    """What one side of a trade is giving."""

    stars: int = 0
    items: list[str] = field(default_factory=list)  # up to 3 item_keys


@dataclass(slots=True)
class TradeResult:
    """Result of a trade action."""

    success: bool
    message: str

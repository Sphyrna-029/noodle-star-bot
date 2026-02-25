"""DTOs for trading use-cases."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class TradeState(Enum):
    """States for the trade state machine."""

    PENDING = "pending"
    COUNTDOWN = "countdown"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TradeOffer:
    """What one side of a trade is giving."""

    stars: int = 0
    items: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class TradeSession:
    """Represents an active trade between two users."""

    proposer_id: int
    proposer_name: str
    opponent_id: int
    opponent_name: str
    proposer_offer: TradeOffer
    opponent_offer: TradeOffer
    state: TradeState = TradeState.PENDING
    channel_id: int = 0
    task: Optional[asyncio.Task] = field(default=None, repr=False)


@dataclass(slots=True)
class TradeResult:
    """Result of a trade action."""

    success: bool
    message: str
    session: Optional[TradeSession] = None

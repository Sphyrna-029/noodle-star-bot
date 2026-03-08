"""DTOs for the treasure chest lock-picking event."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ChestState(Enum):
    """High-level state of the treasure chest."""

    IDLE = "idle"          # no active chest
    AVAILABLE = "available"  # chest spawned, waiting for a picker
    LOCKED = "locked"      # chest is currently being picked by a user
    OPENED = "opened"      # chest was opened (transient)
    EXPIRED = "expired"    # chest expired without being opened


@dataclass(slots=True)
class TreasureChest:
    """Represents an active treasure chest in a channel."""

    channel_id: int
    state: ChestState
    reward: int
    spawned_at: datetime
    pin_count: int = 3
    item_drop_chance: float = 0.0
    rare_item_drop_chance: float = 0.0
    expires_at: Optional[datetime] = None
    owner_id: Optional[int] = None
    combo: tuple[int, ...] = field(default_factory=tuple)
    guess_history: list[tuple[tuple[int, ...], int, int]] = field(default_factory=list)
    attempts_left: int = 0
    owner_expires_at: Optional[datetime] = None
    task: Optional[asyncio.Task] = field(default=None, repr=False)


@dataclass(slots=True)
class SpawnResult:
    """Result of spawning a chest."""

    success: bool
    message: str
    chest: Optional[TreasureChest] = None


@dataclass(slots=True)
class StartPickResult:
    """Result of starting a lock-picking session."""

    success: bool
    message: str
    chest: Optional[TreasureChest] = None


@dataclass(slots=True)
class PickResult:
    """Result of a pick attempt."""

    success: bool
    message: str
    opened: bool = False
    exact: int = 0
    misplaced: int = 0
    attempts_left: int = 0
    reward: int = 0
    new_balance: int = 0
    found_items: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StatusResult:
    """Result for checking chest status."""

    success: bool
    message: str
    chest: Optional[TreasureChest] = None

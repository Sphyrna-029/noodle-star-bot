"""DTOs for mining use-cases."""

from dataclasses import dataclass, field
from typing import List, Mapping, Optional


@dataclass(slots=True)
class MineResult:
    """Result of a mining operation."""

    success: bool
    message: str
    mineral_name: str = ""
    mineral_emoji: str = ""
    stars_earned: int = 0
    new_balance: int = 0
    disaster: Optional[str] = None
    disaster_protected: bool = False
    disaster_header: str = ""
    disaster_protected_msg: str = ""
    disaster_unprotected_msg: str = ""
    stars_lost: int = 0
    bank_lost: int = 0
    items_destroyed: bool = False
    extra_messages: List[str] = field(default_factory=list)
    level_name: str = ""
    level_emoji: str = ""
    found_items: List[str] = field(default_factory=list)


@dataclass(slots=True)
class UnlockResult:
    """Result of unlocking a mine level."""

    success: bool
    message: str
    level: int = 0
    cost: int = 0


@dataclass(slots=True)
class LevelInfo:
    """Info about a user's mine levels."""

    unlocked_level: int
    active_level: int
    levels: Mapping[int, Mapping[str, object]]

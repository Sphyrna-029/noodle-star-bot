"""DTOs for fishing use-cases."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Mapping, Optional


class FishingState(Enum):
    """States for the fishing state machine."""

    IDLE = "idle"
    WAITING = "waiting"
    BITING = "biting"


@dataclass(slots=True)
class FishingSession:
    """Represents an active fishing session for a user."""

    user_id: int
    channel_id: int
    state: FishingState
    bait_type: str
    cast_at: datetime
    bite_at: datetime
    expires_at: datetime
    active_level: int = 1
    jig_active: bool = False
    task: Optional[asyncio.Task] = field(default=None, repr=False)


@dataclass(slots=True)
class CastResult:
    success: bool
    message: str
    bite_wait_seconds: int = 0
    inventory_full: bool = False


@dataclass(slots=True)
class PullResult:
    success: bool
    message: str
    catch_name: str = ""
    catch_emoji: str = ""
    catch_rarity: str = ""
    stars_earned: int = 0
    new_balance: int = 0
    ambush_mob_key: str = ""
    ambush_mob_name: str = ""
    ambush_mob_emoji: str = ""
    ambush_activity: str = ""
    ambush_level: int = 0
    item_sell_value: int = 0
    bag_count: int = 0
    bag_capacity: int = 50
    inventory_full: bool = False
    level_name: str = ""
    level_emoji: str = ""
    found_items: List[str] = field(default_factory=list)
    extra_messages: List[str] = field(default_factory=list)


@dataclass(slots=True)
class FishingStatus:
    is_fishing: bool
    state: Optional[FishingState] = None
    bait_type: Optional[str] = None
    time_until_bite: Optional[int] = None
    time_until_expires: Optional[int] = None
    cooldown_remaining: Optional[int] = None
    equipped_bait: Optional[str] = None


@dataclass(slots=True)
class EquipResult:
    success: bool
    message: str


@dataclass(slots=True)
class FishLevelInfo:
    unlocked_level: int
    active_level: int
    levels: Mapping[int, Mapping[str, object]]

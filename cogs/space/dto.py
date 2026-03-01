"""DTOs for space mining use-cases."""

from dataclasses import dataclass, field
from typing import List, Mapping, Optional


@dataclass(slots=True)
class LaunchResult:
    """Result of launching into space."""

    success: bool
    message: str


@dataclass(slots=True)
class SpaceMineResult:
    """Result of a space mining operation."""

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
    planet_name: str = ""
    planet_emoji: str = ""


@dataclass(slots=True)
class PlanetUnlockResult:
    """Result of unlocking a planet."""

    success: bool
    message: str
    planet: int = 0
    cost: int = 0


@dataclass(slots=True)
class PlanetInfo:
    """Info about a user's space planets."""

    unlocked_planet: int
    active_planet: int
    planets: Mapping[int, Mapping[str, object]]

"""DTOs for space mining use-cases."""

from dataclasses import dataclass, field
from typing import List, Mapping


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
    ambush_mob_key: str = ""
    ambush_mob_name: str = ""
    ambush_mob_emoji: str = ""
    ambush_activity: str = ""
    ambush_level: int = 0
    extra_messages: List[str] = field(default_factory=list)
    planet_name: str = ""
    planet_emoji: str = ""
    item_sell_value: int = 0
    bag_count: int = 0
    bag_capacity: int = 50


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

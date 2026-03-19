"""Location definitions for the world map."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Location:
    key: str
    name: str
    emoji: str
    description: str


LOCATIONS: Final[dict[str, Location]] = {
    "noodle_town": Location(
        key="noodle_town",
        name="Noodle Town",
        emoji="🏘️",
        description="Banking, store, trading, and gambling.",
    ),
    "crystal_cave": Location(
        key="crystal_cave",
        name="Crystal Cave",
        emoji="⛏️",
        description="Mine for minerals and stars.",
    ),
    "starfish_bay": Location(
        key="starfish_bay",
        name="Starfish Bay",
        emoji="🎣",
        description="Cast your line and catch fish.",
    ),
    "fusilli_farms": Location(
        key="fusilli_farms",
        name="Fusilli Farms",
        emoji="🌾",
        description="Plant, tend, and harvest crops.",
    ),
    "starport_ziti": Location(
        key="starport_ziti",
        name="Starport Ziti",
        emoji="🚀",
        description="Launch into space and mine planets.",
    ),
    "noodle_colosseum": Location(
        key="noodle_colosseum",
        name="Noodle Colosseum",
        emoji="🏟️",
        description="Fight mobs in 5 dungeon levels for star rewards.",
    ),
    "aetherdepths": Location(
        key="aetherdepths",
        name="The Aetherdepths",
        emoji="🕳️",
        description="A 5-level dungeon beneath the earth. Requires Combat Level 5.",
    ),
}

DEFAULT_LOCATION: Final[str] = "noodle_town"
TRAVEL_COOLDOWN_SECONDS: Final[int] = 60

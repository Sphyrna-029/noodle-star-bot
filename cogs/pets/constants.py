"""Constants and catalog for the pet system."""

from dataclasses import dataclass
from pathlib import Path


MAX_NEED = 100
MIN_NEED = 0

HUNGER_DECAY_PER_HOUR = 3
CLEANLINESS_DECAY_PER_HOUR = 2
HAPPINESS_DECAY_PER_HOUR = 2

FEED_AMOUNT = 35
CLEAN_AMOUNT = 35
PLAY_AMOUNT = 35


@dataclass(frozen=True, slots=True)
class PetCatalogEntry:
    """Defines a purchasable pet."""

    key: str
    display_name: str
    emoji: str
    price: int
    description: str


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PET_EXPRESSION_DIR = PROJECT_ROOT / "assets" / "pets" / "expressions"


PET_CATALOG: dict[str, PetCatalogEntry] = {
    "ant": PetCatalogEntry(
        key="ant",
        display_name="Cosmic Ant",
        emoji="🐜",
        price=350,
        description="Small but relentless, always exploring.",
    ),
    "cat": PetCatalogEntry(
        key="cat",
        display_name="Nebula Cat",
        emoji="🐈",
        price=650,
        description="Quiet, dramatic, and very clean when pampered.",
    ),
    "dog": PetCatalogEntry(
        key="dog",
        display_name="Orbit Pup",
        emoji="🐕",
        price=700,
        description="Loyal and playful with boundless energy.",
    ),
    "frog": PetCatalogEntry(
        key="frog",
        display_name="Comet Frog",
        emoji="🐸",
        price=500,
        description="Chill little hopper who loves snack time.",
    ),
    "horse": PetCatalogEntry(
        key="horse",
        display_name="Starlight Steed",
        emoji="🐴",
        price=900,
        description="A sturdy companion with heroic vibes.",
    ),
    "dragon": PetCatalogEntry(
        key="dragon",
        display_name="Pocket Dragon",
        emoji="🐉",
        price=1400,
        description="Tiny fire-breather with a huge appetite.",
    ),
}


PET_ALIASES: dict[str, str] = {
    "ant": "ant",
    "cosmic ant": "ant",
    "cat": "cat",
    "nebula cat": "cat",
    "dog": "dog",
    "orbit pup": "dog",
    "frog": "frog",
    "comet frog": "frog",
    "horse": "horse",
    "starlight steed": "horse",
    "dragon": "dragon",
    "pocket dragon": "dragon",
}


def get_pet_by_alias(query: str) -> PetCatalogEntry | None:
    """Resolve a pet by key or alias."""
    key = PET_ALIASES.get(query.strip().lower())
    if key is None:
        return None
    return PET_CATALOG.get(key)

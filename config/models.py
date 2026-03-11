from dataclasses import dataclass
from datetime import timedelta

__all__ = [
    "Mineral", "MineHazard", "ShopItem", "BaitTier", "Catch", "CatchBucket", "Crop",
    "CombatItem", "Mob", "CraftRecipe",
]


@dataclass(frozen=True, slots=True)
class Mineral:
    name: str
    emoji: str
    stars: int
    weight: int


@dataclass(frozen=True, slots=True)
class MineHazard:
    name: str
    emoji: str
    header: str
    wallet_loss_pct: float
    bank_loss_pct: float
    protection_item: str  # "helmet" or "sword"
    protected_msg: str
    unprotected_msg: str


@dataclass(frozen=True, slots=True)
class ShopItem:
    price: int
    db_column: str
    consumable: bool
    emoji: str
    display_name: str
    description: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BaitTier:
    emoji: str
    display_name: str
    bite_wait_min: timedelta
    bite_wait_max: timedelta
    pull_window: timedelta
    rare_boost: float


@dataclass(frozen=True, slots=True)
class Catch:
    name: str
    emoji: str
    stars: int
    weight: int


@dataclass(frozen=True, slots=True)
class CatchBucket:
    weight: int
    catches: tuple[Catch, ...]


@dataclass(frozen=True, slots=True)
class Crop:
    """Definition of a crop type for farming."""
    name: str
    emoji: str
    seed_cost: int
    sell_price: int
    growth_hours: int
    golden_mushroom_yield: int = 0


@dataclass(frozen=True, slots=True)
class CombatItem:
    """A weapon, shield, or armor piece for the combat system."""
    key: str
    name: str
    emoji: str
    slot: str          # "weapon", "shield", or "armor"
    tier: int          # 1-5
    attack: int        # bonus attack power
    defense: int       # bonus defense power
    hp_bonus: int      # bonus max HP
    stamina_cost: int  # stamina used per attack with this weapon (weapons only)
    description: str


@dataclass(frozen=True, slots=True)
class Mob:
    """An enemy mob in the Noodle Colosseum dungeons."""
    key: str
    name: str
    emoji: str
    level: int         # dungeon level 1-5
    hp: int
    attack: int
    defense: int
    stamina: int       # mob's total stamina pool
    star_reward: int
    is_boss: bool


@dataclass(frozen=True, slots=True)
class CraftRecipe:
    """A crafting recipe for combat items or consumables."""
    result_key: str
    result_name: str
    result_emoji: str
    ingredients: tuple[tuple[str, int], ...]  # ((item_key, count), ...)
    description: str

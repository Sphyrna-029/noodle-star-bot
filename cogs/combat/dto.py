"""Data transfer objects for the combat system."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class HealthStatus:
    current_hp: int
    max_hp: int
    current_stamina: int
    max_stamina: int


@dataclass(slots=True)
class EatResult:
    success: bool
    message: str
    hp_restored: int = 0
    current_hp: int = 0
    max_hp: int = 0


@dataclass(slots=True)
class DrinkResult:
    success: bool
    message: str
    stamina_restored: int = 0
    current_stamina: int = 0
    max_stamina: int = 0


@dataclass(slots=True)
class EquipResult:
    success: bool
    message: str
    slot: str = ""
    item_name: str = ""


@dataclass(slots=True)
class GearResult:
    success: bool
    message: str
    weapon: Optional[str] = None
    shield: Optional[str] = None
    armor: Optional[str] = None
    total_attack: int = 0
    total_defense: int = 0
    total_hp_bonus: int = 0


@dataclass(slots=True)
class BattleTurn:
    """One turn of combat."""
    turn_number: int
    actor: str  # "player" or mob name
    action: str  # "attack" or "defend"
    damage_dealt: int = 0
    damage_blocked: int = 0
    actor_hp: int = 0
    target_hp: int = 0
    actor_stamina: int = 0
    message: str = ""


@dataclass(slots=True)
class BattleState:
    """Mutable state during a fight."""
    mob_key: str
    mob_name: str
    mob_emoji: str
    dungeon_level: int
    # Player state
    player_hp: int
    player_max_hp: int
    player_stamina: int
    player_max_stamina: int
    player_attack: int
    player_defense: int
    # Mob state
    mob_hp: int
    mob_max_hp: int
    mob_attack: int
    mob_defense: int
    mob_stamina: int
    mob_max_stamina: int
    # Battle tracking
    turn: int = 0
    turns: list[BattleTurn] = field(default_factory=list)
    finished: bool = False
    player_won: bool = False


@dataclass(slots=True)
class BattleResult:
    success: bool
    message: str
    won: bool = False
    mob_name: str = ""
    mob_emoji: str = ""
    stars_earned: int = 0
    stars_lost: int = 0
    items_lost: list[str] = field(default_factory=list)
    equipment_lost: list[str] = field(default_factory=list)
    bank_loss: int = 0
    combat_level_up: bool = False
    new_combat_level: int = 0
    turns: list[BattleTurn] = field(default_factory=list)


@dataclass(slots=True)
class CraftResult:
    success: bool
    message: str
    item_name: str = ""
    item_emoji: str = ""


@dataclass(slots=True)
class RecipeInfo:
    name: str
    emoji: str
    ingredients: list[tuple[str, int]]
    description: str
    can_craft: bool = False


@dataclass(slots=True)
class DungeonUnlockResult:
    success: bool
    message: str
    level: int = 0
    cost: int = 0

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
class AmbushContext:
    """Metadata for an ambush fight (non-dungeon combat)."""
    activity: str               # "mining", "fishing", "space", "alien"
    activity_level: int         # 1-5 (0 for alien)
    penalty: dict               # DEATH_PENALTIES-format dict
    flee_lockout_turns: int     # turns before flee is available


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
    # Ambush context (None = dungeon fight)
    ambush: Optional[AmbushContext] = None


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


@dataclass
class CoopPlayer:
    """One player in a coop battle."""
    user_id: int
    username: str
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int
    attack: int
    defense: int
    alive: bool = True
    action: str | None = None       # "attack", "defend", "flee", "consume"
    consume_item: str | None = None  # item_key if action == "consume"
    consume_type: str | None = None  # "hp" or "stamina"
    defending: bool = False


@dataclass
class CoopBattleState:
    """Mutable state during a coop fight."""
    mob_key: str
    mob_name: str
    mob_emoji: str
    dungeon_level: int
    players: list[CoopPlayer]
    mob_hp: int
    mob_max_hp: int
    mob_attack: int
    mob_defense: int
    mob_stamina: int
    mob_max_stamina: int
    round: int = 0
    turns: list[BattleTurn] = field(default_factory=list)
    finished: bool = False
    open_for_join: bool = False
    ambush: Optional[AmbushContext] = None
    original_user_id: int = 0


@dataclass(slots=True)
class DungeonUnlockResult:
    success: bool
    message: str
    level: int = 0
    cost: int = 0

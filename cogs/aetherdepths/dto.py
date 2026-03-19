"""Data transfer objects for the Aetherdepths dungeon system."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class AetherState:
    """In-dungeon session state for a player."""
    user_id: int
    level: int
    kills_this_run: int = 0
    is_elite: bool = False
    hp_penalty: int = 0  # temporary HP reduction from hazards
    fights_with_curse: int = 0  # remaining fights with Warden's Curse


@dataclass(slots=True)
class PvPBattleState:
    """Mutable state during a PvP dungeon fight."""
    attacker_id: int
    attacker_name: str
    defender_id: int
    defender_name: str
    aether_level: int
    # Attacker stats
    atk_hp: int
    atk_max_hp: int
    atk_stamina: int
    atk_max_stamina: int
    atk_attack: int
    atk_defense: int
    # Defender stats
    def_hp: int
    def_max_hp: int
    def_stamina: int
    def_max_stamina: int
    def_attack: int
    def_defense: int
    # Tracking
    turn: int = 0
    active_player: int = 0  # 0 = attacker's turn, 1 = defender's turn
    finished: bool = False
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    atk_defending: bool = False
    def_defending: bool = False
    turns: list = field(default_factory=list)


@dataclass(slots=True)
class PvPBattleResult:
    """Result of a PvP encounter."""
    success: bool
    message: str
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    stars_transferred: int = 0
    items_transferred: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HazardResult:
    """Result of a floor hazard roll."""
    triggered: bool
    hazard_name: str = ""
    hazard_emoji: str = ""
    description: str = ""
    stars_lost: int = 0
    items_lost: list[str] = field(default_factory=list)
    hp_loss: int = 0
    stamina_halved: bool = False
    max_hp_reduction: int = 0
    trigger_fight: bool = False


@dataclass(slots=True)
class BlazeGoblinOffer:
    """A Blaze Goblin encounter offer."""
    level: int
    stock: list[tuple[str, int]]  # (item_key, price)


@dataclass(slots=True)
class DailyModifier:
    """Active daily modifier."""
    key: str
    name: str
    emoji: str
    description: str
    active: bool = False

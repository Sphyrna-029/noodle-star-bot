from datetime import timedelta
from typing import Final

from config.models import MineHazard, Mineral

__all__ = [
    "MINING_BASE_COOLDOWN",
    "MINING_POTATO_COOLDOWN",
    "MINING_DISASTER_CHANCE",
    "MINING_COLLAPSE_LOSS_PERCENT",
    "MINING_GOBLIN_LOSS_PERCENT",
    "MINERALS_NORMAL",
    "MINERALS_GOLD_PICKAXE",
    "MINERAL_TABLES",
    "MINE_LEVELS",
]

MINING_BASE_COOLDOWN: Final[timedelta] = timedelta(minutes=30)
MINING_POTATO_COOLDOWN: Final[timedelta] = timedelta(minutes=5)

MINING_DISASTER_CHANCE: Final[float] = 0.10
MINING_COLLAPSE_LOSS_PERCENT: Final[float] = 0.50
MINING_GOBLIN_LOSS_PERCENT: Final[float] = 0.75

# ---------------------------------------------------------------------------
# Minerals per level (normal and gold pickaxe variants)
# ---------------------------------------------------------------------------

MINERALS_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Stone", "🪨", 5, 40),
    Mineral("Coal", "⚫", 10, 30),
    Mineral("Iron", "⚙️", 20, 15),
    Mineral("Gold", "🟡", 40, 10),
    Mineral("Diamond", "💎", 100, 5),
)

MINERALS_GOLD_PICKAXE: Final[tuple[Mineral, ...]] = (
    Mineral("Stone", "🪨", 5, 30),
    Mineral("Coal", "⚫", 10, 25),
    Mineral("Iron", "⚙️", 20, 20),
    Mineral("Gold", "🟡", 40, 15),
    Mineral("Diamond", "💎", 100, 10),
)

# Level 2 - Caverns
_L2_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Sandstone", "🧱", 8, 40),
    Mineral("Copper", "🟤", 15, 30),
    Mineral("Silver", "⬜", 30, 15),
    Mineral("Emerald", "💚", 60, 10),
    Mineral("Ruby", "❤️", 150, 5),
)
_L2_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Sandstone", "🧱", 8, 30),
    Mineral("Copper", "🟤", 15, 25),
    Mineral("Silver", "⬜", 30, 20),
    Mineral("Emerald", "💚", 60, 15),
    Mineral("Ruby", "❤️", 150, 10),
)

# Level 3 - Deep Tunnels
_L3_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Slate", "🪨", 12, 40),
    Mineral("Tin", "🪙", 25, 30),
    Mineral("Platinum", "🔘", 50, 15),
    Mineral("Sapphire", "💙", 90, 10),
    Mineral("Amethyst", "💜", 225, 5),
)
_L3_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Slate", "🪨", 12, 30),
    Mineral("Tin", "🪙", 25, 25),
    Mineral("Platinum", "🔘", 50, 20),
    Mineral("Sapphire", "💙", 90, 15),
    Mineral("Amethyst", "💜", 225, 10),
)

# Level 4 - Molten Core
_L4_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Obsidian", "🖤", 20, 40),
    Mineral("Titanium", "⚪", 40, 30),
    Mineral("Mithril", "🔵", 80, 15),
    Mineral("Opal", "🌈", 140, 10),
    Mineral("Star Fragment", "🌟", 350, 5),
)
_L4_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Obsidian", "🖤", 20, 30),
    Mineral("Titanium", "⚪", 40, 25),
    Mineral("Mithril", "🔵", 80, 20),
    Mineral("Opal", "🌈", 140, 15),
    Mineral("Star Fragment", "🌟", 350, 10),
)

# Level 5 - Abyss
_L5_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Darkite", "🌑", 30, 40),
    Mineral("Adamantium", "⛓️", 60, 30),
    Mineral("Dragonstone", "🐉", 120, 15),
    Mineral("Void Crystal", "🔮", 200, 10),
    Mineral("Noodle Gem", "🍜", 500, 5),
)
_L5_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Darkite", "🌑", 30, 30),
    Mineral("Adamantium", "⛓️", 60, 25),
    Mineral("Dragonstone", "🐉", 120, 20),
    Mineral("Void Crystal", "🔮", 200, 15),
    Mineral("Noodle Gem", "🍜", 500, 10),
)

# ---------------------------------------------------------------------------
# Hazards
# ---------------------------------------------------------------------------

HAZARD_COLLAPSE = MineHazard(
    name="collapse",
    emoji="💥",
    header="💥 **MINE COLLAPSE!** 💥",
    wallet_loss_pct=0.50,
    bank_loss_pct=0.0,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet protected you from the collapse!\n"
        "*Your helmet was destroyed in the process.*"
    ),
    unprotected_msg=(
        "You were caught in the collapse and lost **{stars_lost}** stars! 😱\n"
        "💀 **All your items were destroyed!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

HAZARD_GOBLIN = MineHazard(
    name="goblin",
    emoji="👹",
    header="👹 **GOBLIN ATTACK!** 👹",
    wallet_loss_pct=0.75,
    bank_loss_pct=0.0,
    protection_item="sword",
    protected_msg=(
        "⚔️ You fought off the goblin with your sword!\n"
        "*Your sword broke in the battle.*"
    ),
    unprotected_msg=(
        "The goblin stole **{stars_lost}** stars from you! 😱\n"
        "💀 **The goblin destroyed all your items!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

HAZARD_FLOOD = MineHazard(
    name="flood",
    emoji="🌊",
    header="🌊 **UNDERGROUND FLOOD!** 🌊",
    wallet_loss_pct=0.60,
    bank_loss_pct=0.0,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet let you swim to safety!\n"
        "*Your helmet was swept away by the current.*"
    ),
    unprotected_msg=(
        "The flood swept away **{stars_lost}** stars! 😱\n"
        "💀 **All your items were washed away!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

HAZARD_CAVE_TROLL = MineHazard(
    name="cave_troll",
    emoji="🧌",
    header="🧌 **CAVE TROLL!** 🧌",
    wallet_loss_pct=0.80,
    bank_loss_pct=0.0,
    protection_item="sword",
    protected_msg=(
        "⚔️ You slayed the cave troll with your sword!\n"
        "*Your sword shattered from the impact.*"
    ),
    unprotected_msg=(
        "The cave troll crushed you and took **{stars_lost}** stars! 😱\n"
        "💀 **The troll smashed all your items!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

HAZARD_LAVA_FLOW = MineHazard(
    name="lava_flow",
    emoji="🌋",
    header="🌋 **LAVA FLOW!** 🌋",
    wallet_loss_pct=0.85,
    bank_loss_pct=0.10,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet shielded you from the lava!\n"
        "*Your helmet melted in the heat.*"
    ),
    unprotected_msg=(
        "The lava burned away **{stars_lost}** stars and **{bank_lost}** from your bank! 😱\n"
        "💀 **All your items were incinerated!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

HAZARD_SHADOW_WRAITH = MineHazard(
    name="shadow_wraith",
    emoji="👻",
    header="👻 **SHADOW WRAITH!** 👻",
    wallet_loss_pct=0.90,
    bank_loss_pct=0.25,
    protection_item="sword",
    protected_msg=(
        "⚔️ You banished the shadow wraith with your sword!\n"
        "*Your sword dissolved into darkness.*"
    ),
    unprotected_msg=(
        "The wraith drained **{stars_lost}** stars and **{bank_lost}** from your bank! 😱\n"
        "💀 **All your items were consumed by shadow!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------

# Mineral tables by level
MINERAL_TABLES: Final[dict[int, dict[str, tuple[Mineral, ...]]]] = {
    1: {"normal": MINERALS_NORMAL, "gold": MINERALS_GOLD_PICKAXE},
    2: {"normal": _L2_NORMAL, "gold": _L2_GOLD},
    3: {"normal": _L3_NORMAL, "gold": _L3_GOLD},
    4: {"normal": _L4_NORMAL, "gold": _L4_GOLD},
    5: {"normal": _L5_NORMAL, "gold": _L5_GOLD},
}

MINE_LEVELS: Final[dict[int, dict]] = {
    1: {
        "name": "Surface Mine",
        "emoji": "⛏️",
        "cost": 0,
        "disaster_chance": 0.10,
        "hazards": (HAZARD_COLLAPSE, HAZARD_GOBLIN),
    },
    2: {
        "name": "Caverns",
        "emoji": "🕳️",
        "cost": 2000,
        "disaster_chance": 0.12,
        "hazards": (HAZARD_COLLAPSE, HAZARD_GOBLIN, HAZARD_FLOOD),
    },
    3: {
        "name": "Deep Tunnels",
        "emoji": "🪨",
        "cost": 3000,
        "disaster_chance": 0.14,
        "hazards": (HAZARD_COLLAPSE, HAZARD_GOBLIN, HAZARD_FLOOD, HAZARD_CAVE_TROLL),
    },
    4: {
        "name": "Molten Core",
        "emoji": "🌋",
        "cost": 4000,
        "disaster_chance": 0.16,
        "hazards": (HAZARD_COLLAPSE, HAZARD_GOBLIN, HAZARD_FLOOD, HAZARD_CAVE_TROLL, HAZARD_LAVA_FLOW),
    },
    5: {
        "name": "The Abyss",
        "emoji": "🌑",
        "cost": 5000,
        "disaster_chance": 0.18,
        "hazards": (HAZARD_COLLAPSE, HAZARD_GOBLIN, HAZARD_FLOOD, HAZARD_CAVE_TROLL, HAZARD_LAVA_FLOW, HAZARD_SHADOW_WRAITH),
    },
}

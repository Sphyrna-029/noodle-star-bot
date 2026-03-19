from typing import Final

from config.models import MineHazard, Mineral

__all__ = [
    "SPACE_MINERAL_TABLES",
    "SPACE_PLANETS",
    "SPACE_STAMINA_COST",
    "ROCKET_SHIP_COST",
    "SPACE_ABDUCTION_CHANCE",
]

ROCKET_SHIP_COST: Final[int] = 10000

# Stamina cost per space mine attempt, scaling by planet
SPACE_STAMINA_COST: Final[dict[int, int]] = {
    1: 44,
    2: 50,
    3: 56,
    4: 64,
    5: 70,
}

# Per-planet abduction chance (replaces base 0.05% for space players)
SPACE_ABDUCTION_CHANCE: Final[dict[int, float]] = {
    1: 0.0005,   # Moon:    0.05%
    2: 0.0025,   # Mars:    0.25%
    3: 0.005,    # Saturn:  0.50%
    4: 0.0075,   # Uranus:  0.75%
    5: 0.01,     # Pluto:   1.00%
}

# ---------------------------------------------------------------------------
# Space minerals per planet (normal and gold pickaxe variants)
# ---------------------------------------------------------------------------

# Planet 1 - Moon (Tier 6)
_MOON_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Moon Dust", "🌕", 90, 40),
    Mineral("Helium-3", "🫧", 180, 30),
    Mineral("Lunar Quartz", "🤍", 360, 15),
    Mineral("Selenite", "🌙", 600, 10),
    Mineral("Cosmic Pearl", "🦪", 1500, 5),
)
_MOON_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Moon Dust", "🌕", 90, 30),
    Mineral("Helium-3", "🫧", 180, 25),
    Mineral("Lunar Quartz", "🤍", 360, 20),
    Mineral("Selenite", "🌙", 600, 15),
    Mineral("Cosmic Pearl", "🦪", 1500, 10),
)

# Planet 2 - Mars (Tier 7)
_MARS_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Red Sand", "🔴", 130, 40),
    Mineral("Martian Iron", "🧲", 260, 30),
    Mineral("Phobos Shard", "💫", 520, 15),
    Mineral("Olympus Ruby", "🌋", 860, 10),
    Mineral("Stardust Crystal", "✴️", 2150, 5),
)
_MARS_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Red Sand", "🔴", 130, 30),
    Mineral("Martian Iron", "🧲", 260, 25),
    Mineral("Phobos Shard", "💫", 520, 20),
    Mineral("Olympus Ruby", "🌋", 860, 15),
    Mineral("Stardust Crystal", "✴️", 2150, 10),
)

# Planet 3 - Saturn (Tier 8)
_SATURN_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Ring Fragment", "🪐", 180, 40),
    Mineral("Titan Ore", "🟠", 360, 30),
    Mineral("Ammonia Ice", "🧊", 720, 15),
    Mineral("Saturn Sapphire", "💍", 1200, 10),
    Mineral("Nova Core", "💥", 3000, 5),
)
_SATURN_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Ring Fragment", "🪐", 180, 30),
    Mineral("Titan Ore", "🟠", 360, 25),
    Mineral("Ammonia Ice", "🧊", 720, 20),
    Mineral("Saturn Sapphire", "💍", 1200, 15),
    Mineral("Nova Core", "💥", 3000, 10),
)

# Planet 4 - Uranus (Tier 9)
_URANUS_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Ice Rock", "❄️", 250, 40),
    Mineral("Methane Crystal", "🟢", 500, 30),
    Mineral("Miranda Stone", "🌀", 1000, 15),
    Mineral("Uranian Diamond", "💠", 1660, 10),
    Mineral("Nebula Shard", "🌌", 4150, 5),
)
_URANUS_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Ice Rock", "❄️", 250, 30),
    Mineral("Methane Crystal", "🟢", 500, 25),
    Mineral("Miranda Stone", "🌀", 1000, 20),
    Mineral("Uranian Diamond", "💠", 1660, 15),
    Mineral("Nebula Shard", "🌌", 4150, 10),
)

# Planet 5 - Pluto (Tier 10)
_PLUTO_NORMAL: Final[tuple[Mineral, ...]] = (
    Mineral("Frozen Nitrogen", "🥶", 350, 40),
    Mineral("Charon Basalt", "🗿", 700, 30),
    Mineral("Dark Matter", "⚛️", 1400, 15),
    Mineral("Plutonium Core", "☢️", 2300, 10),
    Mineral("Eternity Gem", "👑", 5750, 5),
)
_PLUTO_GOLD: Final[tuple[Mineral, ...]] = (
    Mineral("Frozen Nitrogen", "🥶", 350, 30),
    Mineral("Charon Basalt", "🗿", 700, 25),
    Mineral("Dark Matter", "⚛️", 1400, 20),
    Mineral("Plutonium Core", "☢️", 2300, 15),
    Mineral("Eternity Gem", "👑", 5750, 10),
)

# ---------------------------------------------------------------------------
# Mineral tables by planet number
# ---------------------------------------------------------------------------

SPACE_MINERAL_TABLES: Final[dict[int, dict[str, tuple[Mineral, ...]]]] = {
    1: {"normal": _MOON_NORMAL, "gold": _MOON_GOLD},
    2: {"normal": _MARS_NORMAL, "gold": _MARS_GOLD},
    3: {"normal": _SATURN_NORMAL, "gold": _SATURN_GOLD},
    4: {"normal": _URANUS_NORMAL, "gold": _URANUS_GOLD},
    5: {"normal": _PLUTO_NORMAL, "gold": _PLUTO_GOLD},
}

# ---------------------------------------------------------------------------
# Space hazards
# ---------------------------------------------------------------------------

HAZARD_METEOR_STRIKE = MineHazard(
    name="meteor_strike",
    emoji="☄️",
    header="☄️ **METEOR STRIKE!** ☄️",
    wallet_loss_pct=0.50,
    bank_loss_pct=0.0,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet shielded you from the meteor impact!\n"
        "*Your helmet was shattered by the blast.*"
    ),
    unprotected_msg=(
        "A meteor slammed into your position and destroyed **{stars_lost}** stars! 😱\n"
        "💀 **All your items were obliterated!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

HAZARD_SPACE_PIRATE = MineHazard(
    name="space_pirate",
    emoji="🏴‍☠️",
    header="🏴‍☠️ **SPACE PIRATE RAID!** 🏴‍☠️",
    wallet_loss_pct=0.75,
    bank_loss_pct=0.0,
    protection_item="sword",
    protected_msg=(
        "⚔️ You fought off the space pirate with your sword!\n"
        "*Your sword was damaged beyond repair.*"
    ),
    unprotected_msg=(
        "The space pirate plundered **{stars_lost}** stars from you! 😱\n"
        "💀 **The pirate looted all your items!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

HAZARD_SOLAR_FLARE = MineHazard(
    name="solar_flare",
    emoji="☀️",
    header="☀️ **SOLAR FLARE!** ☀️",
    wallet_loss_pct=0.85,
    bank_loss_pct=0.10,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet's visor blocked the solar radiation!\n"
        "*Your helmet was fried by the intense heat.*"
    ),
    unprotected_msg=(
        "The solar flare scorched **{stars_lost}** stars and **{bank_lost}** from your bank! 😱\n"
        "💀 **All your items were melted by radiation!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

HAZARD_BLACK_HOLE_RIFT = MineHazard(
    name="black_hole_rift",
    emoji="🕳️",
    header="🕳️ **BLACK HOLE RIFT!** 🕳️",
    wallet_loss_pct=0.85,
    bank_loss_pct=0.15,
    protection_item="sword",
    protected_msg=(
        "⚔️ You used your sword to anchor yourself against the rift!\n"
        "*Your sword was consumed by the singularity.*"
    ),
    unprotected_msg=(
        "The black hole rift sucked away **{stars_lost}** stars and **{bank_lost}** from your bank! 😱\n"
        "💀 **All your items were pulled into the void!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

HAZARD_VOID_ENTITY = MineHazard(
    name="void_entity",
    emoji="👁️",
    header="👁️ **VOID ENTITY!** 👁️",
    wallet_loss_pct=0.90,
    bank_loss_pct=0.30,
    protection_item="sword",
    protected_msg=(
        "⚔️ You banished the void entity with your sword!\n"
        "*Your sword was consumed by the darkness between stars.*"
    ),
    unprotected_msg=(
        "The void entity devoured **{stars_lost}** stars and **{bank_lost}** from your bank! 😱\n"
        "💀 **All your items were erased from existence!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

# ---------------------------------------------------------------------------
# Planet definitions
# ---------------------------------------------------------------------------

SPACE_PLANETS: Final[dict[int, dict]] = {
    1: {
        "name": "The Moon",
        "emoji": "🌕",
        "cost": 0,
        "disaster_chance": 0.12,
        "protection_fail_chance": 0.25,
        "helmet_fail_msg": (
            "🪖🌕 Your helmet's visor cracked from the lunar temperature swing — "
            "Earth helmets weren't designed for space! *(-1 helmet)*"
        ),
        "sword_fail_msg": (
            "⚔️🌕 Your sword floated away in the low gravity mid-swing — "
            "fighting in space is harder than it looks! *(-1 sword)*"
        ),
        "hazards": (HAZARD_METEOR_STRIKE, HAZARD_SPACE_PIRATE),
    },
    2: {
        "name": "Mars",
        "emoji": "🔴",
        "cost": 5000,
        "disaster_chance": 0.14,
        "protection_fail_chance": 0.30,
        "helmet_fail_msg": (
            "🪖🔴 Your helmet's seal broke in the Martian dust storm — "
            "the red planet chews through cheap gear! *(-1 helmet)*"
        ),
        "sword_fail_msg": (
            "⚔️🔴 Your sword was sandblasted to pieces by the Martian winds — "
            "it's like swinging through a blender out here! *(-1 sword)*"
        ),
        "hazards": (HAZARD_METEOR_STRIKE, HAZARD_SPACE_PIRATE),
    },
    3: {
        "name": "Saturn",
        "emoji": "🪐",
        "cost": 10000,
        "disaster_chance": 0.16,
        "protection_fail_chance": 0.35,
        "helmet_fail_msg": (
            "🪖🪐 Your helmet was ripped apart by Saturn's gravitational tides — "
            "the rings aren't just pretty, they're deadly! *(-1 helmet)*"
        ),
        "sword_fail_msg": (
            "⚔️🪐 Your sword was wrenched from your grip by Saturn's magnetic field — "
            "the planet itself fights back! *(-1 sword)*"
        ),
        "hazards": (HAZARD_METEOR_STRIKE, HAZARD_SPACE_PIRATE, HAZARD_SOLAR_FLARE, HAZARD_BLACK_HOLE_RIFT),
    },
    4: {
        "name": "Uranus",
        "emoji": "💠",
        "cost": 15000,
        "disaster_chance": 0.18,
        "protection_fail_chance": 0.40,
        "helmet_fail_msg": (
            "🪖💠 Your helmet froze solid and shattered like glass — "
            "Uranus is cold enough to kill your gear before it kills you! *(-1 helmet)*"
        ),
        "sword_fail_msg": (
            "⚔️💠 Your sword became so brittle in the extreme cold that it snapped on contact — "
            "Uranus doesn't play fair! *(-1 sword)*"
        ),
        "hazards": (HAZARD_METEOR_STRIKE, HAZARD_SPACE_PIRATE, HAZARD_SOLAR_FLARE, HAZARD_BLACK_HOLE_RIFT),
    },
    5: {
        "name": "Pluto",
        "emoji": "🥶",
        "cost": 20000,
        "disaster_chance": 0.22,
        "protection_fail_chance": 0.50,
        "helmet_fail_msg": (
            "🪖🥶 Your helmet disintegrated in the void — "
            "at the edge of the solar system, matter itself gives up! *(-1 helmet)*"
        ),
        "sword_fail_msg": (
            "⚔️🥶 Your sword phased right through the threat like it wasn't even there — "
            "at the edge of reality, steel means nothing! *(-1 sword)*"
        ),
        "hazards": (HAZARD_METEOR_STRIKE, HAZARD_SPACE_PIRATE, HAZARD_SOLAR_FLARE, HAZARD_BLACK_HOLE_RIFT, HAZARD_VOID_ENTITY),
    },
}

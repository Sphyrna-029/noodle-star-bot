from datetime import timedelta
from typing import Final

from config.models import BaitTier, Catch, CatchBucket, MineHazard

__all__ = [
    "FISHING_COOLDOWN",
    "FISHING_BAIT_TIERS",
    "FISHING_CATCH_TABLE",
    "CATCH_TABLES",
    "FISH_LEVELS",
]

FISHING_COOLDOWN: Final[timedelta] = timedelta(seconds=120)

FISHING_BAIT_TIERS: Final[dict[str, BaitTier]] = {
    "worm": BaitTier(
        emoji="🪱",
        display_name="Worm",
        bite_wait_min=timedelta(seconds=15),
        bite_wait_max=timedelta(seconds=60),
        pull_window=timedelta(seconds=60),
        rare_boost=0.4924,
    ),
    "herring": BaitTier(
        emoji="🐟",
        display_name="Herring",
        bite_wait_min=timedelta(seconds=90),
        bite_wait_max=timedelta(seconds=180),
        pull_window=timedelta(seconds=35),
        rare_boost=2.009,
    ),
    "sturgeon": BaitTier(
        emoji="🐋",
        display_name="Sturgeon",
        bite_wait_min=timedelta(minutes=5),
        bite_wait_max=timedelta(minutes=8),
        pull_window=timedelta(seconds=20),
        rare_boost=9.964,
    ),
}

# ---------------------------------------------------------------------------
# Level 1 — Calm Pond (existing catch table, unchanged)
# ---------------------------------------------------------------------------

FISHING_CATCH_TABLE: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Old Boot", "🥾", 0, 15),
            Catch("Seaweed", "🌿", 0, 15),
            Catch("Tin Can", "🥫", 0, 10),
            Catch("Small Fish", "🐟", 8, 25),
            Catch("Crab", "🦀", 12, 20),
            Catch("Shrimp", "🦐", 15, 15),
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("Salmon", "🐠", 40, 30),
            Catch("Tuna", "🐟", 65, 25),
            Catch("Lobster", "🦞", 90, 20),
            Catch("Octopus", "🐙", 130, 15),
            Catch("Treasure Chest", "📦", 200, 10),
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Golden Fish", "✨", 500, 40),
            Catch("Giant Squid", "🦑", 800, 30),
            Catch("Ancient Artifact", "🏺", 1200, 20),
            Catch("Mermaid's Pearl", "🔮", 2000, 10),
        ),
    ),
}

_L1_CATCHES = FISHING_CATCH_TABLE

# ---------------------------------------------------------------------------
# Level 2 — River Rapids
# ---------------------------------------------------------------------------

_L2_CATCHES: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Driftwood", "🪵", 0, 15),
            Catch("River Stone", "🪨", 0, 15),
            Catch("Crawdad", "🦐", 5, 10),
            Catch("Trout", "🐟", 12, 25),
            Catch("Catfish", "🐈", 18, 20),
            Catch("Bass", "🐠", 25, 15),
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("River Salmon", "🐠", 60, 30),
            Catch("Sturgeon", "🐋", 100, 25),
            Catch("Snapping Turtle", "🐢", 150, 20),
            Catch("Giant Catfish", "🐟", 200, 15),
            Catch("River Chest", "📦", 300, 10),
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Platinum Trout", "✨", 750, 40),
            Catch("River Dragon", "🐉", 1200, 30),
            Catch("Lost Crown", "👑", 2000, 20),
            Catch("River Spirit Gem", "💎", 3000, 10),
        ),
    ),
}

# ---------------------------------------------------------------------------
# Level 3 — Coral Reef
# ---------------------------------------------------------------------------

_L3_CATCHES: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Sea Sponge", "🧽", 0, 15),
            Catch("Starfish", "⭐", 5, 15),
            Catch("Clownfish", "🐠", 10, 10),
            Catch("Parrotfish", "🦜", 20, 25),
            Catch("Sea Urchin", "🟣", 30, 20),
            Catch("Moray Eel", "🐍", 40, 15),
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("Reef Shark", "🦈", 80, 30),
            Catch("Giant Clam", "🐚", 150, 25),
            Catch("Manta Ray", "🦅", 250, 20),
            Catch("Sea Turtle", "🐢", 350, 15),
            Catch("Sunken Treasure", "💰", 450, 10),
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Golden Seahorse", "✨", 1000, 40),
            Catch("Coral Golem", "🪸", 2000, 30),
            Catch("Neptune's Trident", "🔱", 3500, 20),
            Catch("Pearl of the Deep", "🔮", 5000, 10),
        ),
    ),
}

# ---------------------------------------------------------------------------
# Level 4 — Shipwreck Depths
# ---------------------------------------------------------------------------

_L4_CATCHES: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Barnacle Cluster", "🪨", 0, 15),
            Catch("Rusty Anchor", "⚓", 5, 15),
            Catch("Anglerfish", "🐡", 15, 10),
            Catch("Barracuda", "🐟", 30, 25),
            Catch("Swordfish", "⚔️", 45, 20),
            Catch("Electric Eel", "⚡", 60, 15),
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("Hammerhead Shark", "🦈", 120, 30),
            Catch("Giant Octopus", "🐙", 250, 25),
            Catch("Sunken Cannon", "💣", 400, 20),
            Catch("Ghost Ship Wheel", "☠️", 500, 15),
            Catch("Pirate's Hoard", "💰", 650, 10),
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Phantom Captain", "👻", 1500, 40),
            Catch("Diamond Anchor", "💎", 3000, 30),
            Catch("Cursed Gold", "🏴‍☠️", 5500, 20),
            Catch("Davy Jones' Chest", "📦", 8000, 10),
        ),
    ),
}

# ---------------------------------------------------------------------------
# Level 5 — The Abyss Trench
# ---------------------------------------------------------------------------

_L5_CATCHES: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Void Coral", "🖤", 0, 15),
            Catch("Bioluminescent Jelly", "🪼", 10, 15),
            Catch("Abyssal Crab", "🦀", 20, 10),
            Catch("Vampire Squid", "🦑", 40, 25),
            Catch("Gulper Eel", "🐍", 60, 20),
            Catch("Dragonfish", "🐉", 90, 15),
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("Colossal Squid", "🦑", 180, 30),
            Catch("Megalodon Tooth", "🦷", 350, 25),
            Catch("Abyssal Pearl", "⚪", 550, 20),
            Catch("Deep Sea Crown", "👑", 750, 15),
            Catch("Trench Treasure", "💰", 1000, 10),
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Leviathan Scale", "🐲", 2500, 40),
            Catch("Poseidon's Eye", "🔮", 5000, 30),
            Catch("World Serpent Fang", "🐍", 8000, 20),
            Catch("Heart of the Abyss", "💜", 12000, 10),
        ),
    ),
}

# ---------------------------------------------------------------------------
# Fishing Hazards (reuses MineHazard dataclass)
# ---------------------------------------------------------------------------

FISH_HAZARD_RIPTIDE = MineHazard(
    name="riptide",
    emoji="🌊",
    header="🌊 **RIPTIDE!** 🌊",
    wallet_loss_pct=0.40,
    bank_loss_pct=0.0,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet kept you afloat in the riptide!\n"
        "*Your helmet was swept away by the current.*"
    ),
    unprotected_msg=(
        "The riptide swept away **{stars_lost}** stars! 😱\n"
        "💀 **All your items were washed away!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

FISH_HAZARD_SHARK = MineHazard(
    name="shark_attack",
    emoji="🦈",
    header="🦈 **SHARK ATTACK!** 🦈",
    wallet_loss_pct=0.55,
    bank_loss_pct=0.0,
    protection_item="sword",
    protected_msg=(
        "⚔️ You fought off the shark with your sword!\n"
        "*Your sword was lost in the struggle.*"
    ),
    unprotected_msg=(
        "The shark bit away **{stars_lost}** stars! 😱\n"
        "💀 **The shark destroyed all your items!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

FISH_HAZARD_WHIRLPOOL = MineHazard(
    name="whirlpool",
    emoji="🌀",
    header="🌀 **WHIRLPOOL!** 🌀",
    wallet_loss_pct=0.60,
    bank_loss_pct=0.0,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet protected you from the whirlpool!\n"
        "*Your helmet was sucked into the vortex.*"
    ),
    unprotected_msg=(
        "The whirlpool dragged away **{stars_lost}** stars! 😱\n"
        "💀 **All your items were lost in the vortex!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

FISH_HAZARD_KRAKEN = MineHazard(
    name="kraken",
    emoji="🦑",
    header="🦑 **KRAKEN!** 🦑",
    wallet_loss_pct=0.75,
    bank_loss_pct=0.0,
    protection_item="sword",
    protected_msg=(
        "⚔️ You slashed the kraken's tentacle with your sword!\n"
        "*Your sword shattered from the impact.*"
    ),
    unprotected_msg=(
        "The kraken crushed you and took **{stars_lost}** stars! 😱\n"
        "💀 **The kraken destroyed all your items!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

FISH_HAZARD_SIREN = MineHazard(
    name="siren",
    emoji="🧜",
    header="🧜 **SIREN'S CALL!** 🧜",
    wallet_loss_pct=0.80,
    bank_loss_pct=0.10,
    protection_item="helmet",
    protected_msg=(
        "🪖 Your helmet blocked the siren's song!\n"
        "*Your helmet cracked from the sonic waves.*"
    ),
    unprotected_msg=(
        "The siren lured away **{stars_lost}** stars and **{bank_lost}** from your bank! 😱\n"
        "💀 **All your items were enchanted away!**\n"
        "💡 *Buy a helmet from the !store to protect yourself!*"
    ),
)

FISH_HAZARD_LEVIATHAN = MineHazard(
    name="leviathan",
    emoji="🐲",
    header="🐲 **LEVIATHAN!** 🐲",
    wallet_loss_pct=0.85,
    bank_loss_pct=0.20,
    protection_item="sword",
    protected_msg=(
        "⚔️ You drove back the leviathan with your sword!\n"
        "*Your sword dissolved in the beast's acid.*"
    ),
    unprotected_msg=(
        "The leviathan devoured **{stars_lost}** stars and **{bank_lost}** from your bank! 😱\n"
        "💀 **All your items were consumed!**\n"
        "💡 *Buy a sword from the !store to protect yourself!*"
    ),
)

# ---------------------------------------------------------------------------
# Catch tables by level
# ---------------------------------------------------------------------------

CATCH_TABLES: Final[dict[int, dict[str, CatchBucket]]] = {
    1: _L1_CATCHES,
    2: _L2_CATCHES,
    3: _L3_CATCHES,
    4: _L4_CATCHES,
    5: _L5_CATCHES,
}

# ---------------------------------------------------------------------------
# Fish Level definitions
# ---------------------------------------------------------------------------

FISH_LEVELS: Final[dict[int, dict]] = {
    1: {
        "name": "Calm Pond",
        "emoji": "🎣",
        "disaster_chance": 0.0,
        "hazards": (),
    },
    2: {
        "name": "River Rapids",
        "emoji": "🏞️",
        "disaster_chance": 0.08,
        "hazards": (FISH_HAZARD_RIPTIDE, FISH_HAZARD_SHARK),
    },
    3: {
        "name": "Coral Reef",
        "emoji": "🪸",
        "disaster_chance": 0.10,
        "hazards": (FISH_HAZARD_RIPTIDE, FISH_HAZARD_SHARK, FISH_HAZARD_WHIRLPOOL),
    },
    4: {
        "name": "Shipwreck Depths",
        "emoji": "🚢",
        "disaster_chance": 0.12,
        "hazards": (
            FISH_HAZARD_RIPTIDE,
            FISH_HAZARD_SHARK,
            FISH_HAZARD_WHIRLPOOL,
            FISH_HAZARD_KRAKEN,
        ),
    },
    5: {
        "name": "The Abyss Trench",
        "emoji": "🌊",
        "disaster_chance": 0.14,
        "hazards": (
            FISH_HAZARD_RIPTIDE,
            FISH_HAZARD_SHARK,
            FISH_HAZARD_WHIRLPOOL,
            FISH_HAZARD_KRAKEN,
            FISH_HAZARD_SIREN,
            FISH_HAZARD_LEVIATHAN,
        ),
    },
}

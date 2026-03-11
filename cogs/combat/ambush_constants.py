"""Ambush mob definitions for mining, fishing, and space mining encounters."""

from typing import Final

from config.models import Mob

# ---------------------------------------------------------------------------
# Flee lockout — turns before Flee button becomes available
# ---------------------------------------------------------------------------

AMBUSH_FLEE_LOCKOUT: Final[dict[int, int]] = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
}

# ---------------------------------------------------------------------------
# Mining ambush mobs (themed to underground hazards)
# ---------------------------------------------------------------------------

MINING_AMBUSH_MOBS: Final[dict[int, list[Mob]]] = {
    1: [
        Mob("rock_critter", "Rock Critter", "🪨", level=1, hp=20, attack=4, defense=1, stamina=30, star_reward=0, is_boss=False),
        Mob("tunnel_rat", "Tunnel Rat", "🐀", level=1, hp=25, attack=5, defense=2, stamina=40, star_reward=0, is_boss=False),
    ],
    2: [
        Mob("cave_bat", "Cave Bat", "🦇", level=2, hp=35, attack=8, defense=3, stamina=50, star_reward=0, is_boss=False),
        Mob("mine_goblin", "Mine Goblin", "👹", level=2, hp=45, attack=10, defense=4, stamina=60, star_reward=0, is_boss=False),
    ],
    3: [
        Mob("crystal_golem", "Crystal Golem", "💎", level=3, hp=70, attack=16, defense=8, stamina=80, star_reward=0, is_boss=False),
        Mob("cave_troll", "Cave Troll", "🧌", level=3, hp=90, attack=20, defense=10, stamina=90, star_reward=0, is_boss=False),
    ],
    4: [
        Mob("magma_elemental", "Magma Elemental", "🔥", level=4, hp=130, attack=26, defense=14, stamina=110, star_reward=0, is_boss=False),
        Mob("lava_worm", "Lava Worm", "🌋", level=4, hp=150, attack=30, defense=16, stamina=120, star_reward=0, is_boss=False),
    ],
    5: [
        Mob("shadow_crawler", "Shadow Crawler", "🕷️", level=5, hp=180, attack=34, defense=20, stamina=130, star_reward=0, is_boss=False),
        Mob("abyss_wraith", "Abyss Wraith", "👻", level=5, hp=220, attack=38, defense=22, stamina=140, star_reward=0, is_boss=False),
    ],
}

# ---------------------------------------------------------------------------
# Fishing ambush mobs (themed to sea creatures)
# Level 1 has 0% disaster chance so no mobs needed
# ---------------------------------------------------------------------------

FISHING_AMBUSH_MOBS: Final[dict[int, list[Mob]]] = {
    2: [
        Mob("snapping_eel", "Snapping Eel", "🐍", level=2, hp=30, attack=7, defense=2, stamina=40, star_reward=0, is_boss=False),
        Mob("river_serpent", "River Serpent", "🌊", level=2, hp=40, attack=9, defense=3, stamina=50, star_reward=0, is_boss=False),
    ],
    3: [
        Mob("reef_guardian", "Reef Guardian", "🐚", level=3, hp=60, attack=14, defense=6, stamina=70, star_reward=0, is_boss=False),
        Mob("whirlpool_spirit", "Whirlpool Spirit", "🌀", level=3, hp=75, attack=18, defense=8, stamina=80, star_reward=0, is_boss=False),
    ],
    4: [
        Mob("ghost_captain", "Ghost Captain", "👻", level=4, hp=110, attack=24, defense=12, stamina=100, star_reward=0, is_boss=False),
        Mob("kraken_spawn", "Kraken Spawn", "🦑", level=4, hp=140, attack=28, defense=14, stamina=110, star_reward=0, is_boss=False),
    ],
    5: [
        Mob("siren", "Siren", "🧜", level=5, hp=170, attack=32, defense=18, stamina=120, star_reward=0, is_boss=False),
        Mob("leviathan", "Leviathan", "🐲", level=5, hp=230, attack=40, defense=22, stamina=140, star_reward=0, is_boss=False),
    ],
}

# ---------------------------------------------------------------------------
# Space ambush mobs (themed to space hazards)
# ---------------------------------------------------------------------------

SPACE_AMBUSH_MOBS: Final[dict[int, list[Mob]]] = {
    1: [
        Mob("lunar_drone", "Lunar Drone", "🤖", level=1, hp=100, attack=22, defense=12, stamina=100, star_reward=0, is_boss=False),
        Mob("moon_stalker", "Moon Stalker", "🌕", level=1, hp=120, attack=26, defense=14, stamina=110, star_reward=0, is_boss=False),
    ],
    2: [
        Mob("mars_raider", "Mars Raider", "👽", level=2, hp=140, attack=28, defense=16, stamina=120, star_reward=0, is_boss=False),
        Mob("dust_devil", "Dust Devil", "🌪️", level=2, hp=160, attack=32, defense=18, stamina=130, star_reward=0, is_boss=False),
    ],
    3: [
        Mob("ring_wraith", "Ring Wraith", "💫", level=3, hp=200, attack=36, defense=22, stamina=140, star_reward=0, is_boss=False),
        Mob("solar_sentinel", "Solar Sentinel", "☀️", level=3, hp=220, attack=38, defense=24, stamina=150, star_reward=0, is_boss=False),
    ],
    4: [
        Mob("void_stalker", "Void Stalker", "🔮", level=4, hp=260, attack=42, defense=28, stamina=160, star_reward=0, is_boss=False),
        Mob("cosmic_dread", "Cosmic Dread", "👁️", level=4, hp=300, attack=46, defense=30, stamina=170, star_reward=0, is_boss=False),
    ],
    5: [
        Mob("dark_matter_beast", "Dark Matter Beast", "⚛️", level=5, hp=350, attack=50, defense=34, stamina=180, star_reward=0, is_boss=False),
        Mob("void_sovereign", "Void Sovereign", "🌌", level=5, hp=420, attack=56, defense=38, stamina=190, star_reward=0, is_boss=False),
    ],
}

# ---------------------------------------------------------------------------
# Alien abduction mob (special encounter)
# ---------------------------------------------------------------------------

ALIEN_MOB: Final[Mob] = Mob(
    key="alien_raider", name="Alien Raider", emoji="👽",
    level=0, hp=150, attack=25, defense=15, stamina=120,
    star_reward=0, is_boss=False,
)
ALIEN_ATK_BONUS: Final[int] = 75

# ---------------------------------------------------------------------------
# Ambush defeat penalties (derived from original hazard worst-cases)
# Same format as DEATH_PENALTIES in cogs/combat/constants.py
# ---------------------------------------------------------------------------

AMBUSH_DEFEAT_PENALTIES: Final[dict[str, dict[int, dict]]] = {
    "mining": {
        1: {
            "wallet_loss_pct": 0.75, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 75% wallet + all items",
        },
        2: {
            "wallet_loss_pct": 0.75, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 75% wallet + all items",
        },
        3: {
            "wallet_loss_pct": 0.80, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 80% wallet + all items",
        },
        4: {
            "wallet_loss_pct": 0.85, "bank_loss_pct": 0.10,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 85% wallet + 10% bank + all items",
        },
        5: {
            "wallet_loss_pct": 0.90, "bank_loss_pct": 0.25,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 90% wallet + 25% bank + all items",
        },
    },
    "fishing": {
        2: {
            "wallet_loss_pct": 0.55, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 55% wallet + all items",
        },
        3: {
            "wallet_loss_pct": 0.60, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 60% wallet + all items",
        },
        4: {
            "wallet_loss_pct": 0.75, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 75% wallet + all items",
        },
        5: {
            "wallet_loss_pct": 0.85, "bank_loss_pct": 0.20,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 85% wallet + 20% bank + all items",
        },
    },
    "space": {
        1: {
            "wallet_loss_pct": 0.75, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 75% wallet + all items",
        },
        2: {
            "wallet_loss_pct": 0.75, "bank_loss_pct": 0.0,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 75% wallet + all items",
        },
        3: {
            "wallet_loss_pct": 0.85, "bank_loss_pct": 0.15,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 85% wallet + 15% bank + all items",
        },
        4: {
            "wallet_loss_pct": 0.85, "bank_loss_pct": 0.15,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 85% wallet + 15% bank + all items",
        },
        5: {
            "wallet_loss_pct": 0.90, "bank_loss_pct": 0.30,
            "lose_all_items": True, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 90% wallet + 30% bank + all items",
        },
    },
    "alien": {
        0: {
            "wallet_loss_pct": 1.0, "bank_loss_pct": 0.0,
            "lose_all_items": False, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose all wallet stars",
        },
    },
}

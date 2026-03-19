"""Ambush mob definitions for mining, fishing, and space mining encounters."""

from typing import Final

from config.models import Mob

# Drop tuple: (item_key, category, sell_value, chance)
_Drop = tuple[str, str, int, float]

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
        Mob("lunar_drone", "Lunar Drone", "🤖", level=1, hp=400, attack=48, defense=28, stamina=190, star_reward=0, is_boss=False),
        Mob("moon_stalker", "Moon Stalker", "🌕", level=1, hp=480, attack=54, defense=35, stamina=210, star_reward=0, is_boss=False),
    ],
    2: [
        Mob("mars_raider", "Mars Raider", "👽", level=2, hp=560, attack=68, defense=40, stamina=230, star_reward=0, is_boss=False),
        Mob("dust_devil", "Dust Devil", "🌪️", level=2, hp=640, attack=78, defense=48, stamina=245, star_reward=0, is_boss=False),
    ],
    3: [
        Mob("ring_wraith", "Ring Wraith", "💫", level=3, hp=720, attack=88, defense=48, stamina=260, star_reward=0, is_boss=False),
        Mob("solar_sentinel", "Solar Sentinel", "☀️", level=3, hp=800, attack=98, defense=55, stamina=275, star_reward=0, is_boss=False),
    ],
    4: [
        Mob("void_stalker", "Void Stalker", "🔮", level=4, hp=880, attack=112, defense=58, stamina=280, star_reward=0, is_boss=False),
        Mob("cosmic_dread", "Cosmic Dread", "👁️", level=4, hp=980, attack=122, defense=68, stamina=295, star_reward=0, is_boss=False),
    ],
    5: [
        Mob("dark_matter_beast", "Dark Matter Beast", "⚛️", level=5, hp=1250, attack=128, defense=82, stamina=320, star_reward=0, is_boss=False),
        Mob("void_sovereign", "Void Sovereign", "🌌", level=5, hp=1450, attack=138, defense=92, stamina=340, star_reward=0, is_boss=False),
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
            "wallet_loss_pct": 0.50, "bank_loss_pct": 0.0,
            "lose_all_items": False, "lose_random_items_pct": 0.0,
            "lose_random_equipment": 0, "lose_all_equipment": False,
            "description": "Lose 50% wallet",
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

# ---------------------------------------------------------------------------
# Ambush mob bonus drops — per-mob rare resource rewards for winning
#
# Mining/Fishing: rare resources from the same activity level.
# Space: rare resources + rare effect items.
# Weaker mobs → 10-15% chance, stronger mobs → 25-35% chance.
# ---------------------------------------------------------------------------

AMBUSH_MOB_BONUS_DROPS: Final[dict[str, list[_Drop]]] = {
    # ── Mining mobs ────────────────────────────────────────────
    # L1 — rare: gold, diamond
    "rock_critter":     [("gold", "mineral", 40, 0.20), ("diamond", "mineral", 100, 0.20)],
    "tunnel_rat":       [("gold", "mineral", 40, 0.40), ("diamond", "mineral", 100, 0.30)],
    # L2 — rare: emerald, ruby
    "cave_bat":         [("emerald", "mineral", 60, 0.20), ("ruby", "mineral", 150, 0.20)],
    "mine_goblin":      [("emerald", "mineral", 60, 0.40), ("ruby", "mineral", 150, 0.30)],
    # L3 — rare: sapphire, amethyst
    "crystal_golem":    [("sapphire", "mineral", 90, 0.24), ("amethyst", "mineral", 225, 0.20)],
    "cave_troll":       [("sapphire", "mineral", 90, 0.50), ("amethyst", "mineral", 225, 0.30)],
    # L4 — rare: opal, star fragment
    "magma_elemental":  [("opal", "mineral", 140, 0.24), ("star_fragment", "mineral", 350, 0.20)],
    "lava_worm":        [("opal", "mineral", 140, 0.50), ("star_fragment", "mineral", 350, 0.30)],
    # L5 — rare: void crystal, noodle gem
    "shadow_crawler":   [("void_crystal", "mineral", 200, 0.30), ("noodle_gem", "mineral", 500, 0.20)],
    "abyss_wraith":     [("void_crystal", "mineral", 200, 0.60), ("noodle_gem", "mineral", 500, 0.30)],

    # ── Fishing mobs ───────────────────────────────────────────
    # L2 — rare: river salmon, sturgeon; legendary: platinum trout
    "snapping_eel":     [("river_salmon", "fish", 225, 0.24), ("sturgeon", "fish", 375, 0.20)],
    "river_serpent":    [("sturgeon", "fish", 375, 0.40), ("platinum_trout", "fish", 2805, 0.20)],
    # L3 — rare: sea turtle, sunken treasure; legendary: golden seahorse
    "reef_guardian":    [("sea_turtle", "fish", 1280, 0.24), ("sunken_treasure", "fish", 1650, 0.20)],
    "whirlpool_spirit": [("sunken_treasure", "fish", 1650, 0.40), ("golden_seahorse", "fish", 3665, 0.20)],
    # L4 — rare: pirate's hoard; legendary: phantom captain, diamond anchor
    "ghost_captain":    [("pirates_hoard", "fish", 2255, 0.30), ("phantom_captain", "fish", 5210, 0.20)],
    "kraken_spawn":     [("pirates_hoard", "fish", 2255, 0.50), ("diamond_anchor", "fish", 10420, 0.20)],
    # L5 — rare: trench treasure; legendary: leviathan scale, poseidon's eye
    "siren":            [("trench_treasure", "fish", 3715, 0.30), ("leviathan_scale", "fish", 9280, 0.20)],
    "leviathan":        [("trench_treasure", "fish", 3715, 0.60), ("poseidons_eye", "fish", 18565, 0.20)],

    # ── Space mobs (rare resources + rare effect items) ────────
    # P1 — rare ores + effect items
    "lunar_drone":      [("cosmic_pearl", "ore", 750, 0.20), ("rune_fragment", "equipment", 0, 0.20)],
    "moon_stalker":     [("cosmic_pearl", "ore", 750, 0.40), ("rune_fragment", "equipment", 0, 0.30)],
    # P2
    "mars_raider":      [("stardust_crystal", "ore", 1075, 0.20), ("fossilized_noodle", "equipment", 0, 0.20)],
    "dust_devil":       [("stardust_crystal", "ore", 1075, 0.40), ("fossilized_noodle", "equipment", 0, 0.30)],
    # P3
    "ring_wraith":      [("nova_core", "ore", 1500, 0.24), ("star_magnet", "equipment", 0, 0.20)],
    "solar_sentinel":   [("nova_core", "ore", 1500, 0.50), ("star_magnet", "equipment", 0, 0.30)],
    # P4
    "void_stalker":     [("nebula_shard", "ore", 2075, 0.24), ("lucky_charm", "equipment", 0, 0.20)],
    "cosmic_dread":     [("nebula_shard", "ore", 2075, 0.50), ("lucky_charm", "equipment", 0, 0.30)],
    # P5
    "dark_matter_beast": [("eternity_gem", "ore", 2875, 0.30), ("bucktail_jig", "equipment", 0, 0.20)],
    "void_sovereign":    [("eternity_gem", "ore", 2875, 0.70), ("ray_gun", "equipment", 0, 0.20)],
}

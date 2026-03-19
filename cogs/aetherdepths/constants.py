"""Aetherdepths dungeon constants — levels, mobs, drops, hazards, modifiers."""

from typing import Final

from config.models import Mob

# ---------------------------------------------------------------------------
# Dungeon levels — 5 floors
# ---------------------------------------------------------------------------

AETHER_LEVELS: Final[dict[int, dict]] = {
    1: {"name": "The Hollow", "emoji": "🕳️"},
    2: {"name": "The Sunken Forge", "emoji": "🔨"},
    3: {"name": "The Crystal Abyss", "emoji": "🔮"},
    4: {"name": "The Warden's Sanctum", "emoji": "🏛️"},
    5: {"name": "The Core", "emoji": "🌋"},
}

# ---------------------------------------------------------------------------
# Unlock costs — all require combat_level >= 5
# ---------------------------------------------------------------------------

AETHER_UNLOCK: Final[dict[int, dict]] = {
    1: {"cost": 15_000, "required_combat_level": 5},
    2: {"cost": 25_000, "required_combat_level": 5},
    3: {"cost": 40_000, "required_combat_level": 5},
    4: {"cost": 60_000, "required_combat_level": 5},
    5: {"cost": 85_000, "required_combat_level": 5},
}

# ---------------------------------------------------------------------------
# Mobs — 15 total: 2 regular + 1 boss per level
# ---------------------------------------------------------------------------

AETHER_MOBS: Final[dict[str, Mob]] = {
    # ── Level 1: The Hollow ──────────────────────────────────
    "hollow_wraith": Mob(
        key="hollow_wraith", name="Hollow Wraith", emoji="👻",
        level=1, hp=420, attack=55, defense=30, stamina=200,
        star_reward=1500, is_boss=False,
    ),
    "stone_sentinel": Mob(
        key="stone_sentinel", name="Stone Sentinel", emoji="🗿",
        level=1, hp=500, attack=48, defense=40, stamina=225,
        star_reward=1800, is_boss=False,
    ),
    "hollow_king": Mob(
        key="hollow_king", name="The Hollow King", emoji="👑",
        level=1, hp=800, attack=65, defense=45, stamina=275,
        star_reward=4500, is_boss=True,
    ),

    # ── Level 2: The Sunken Forge ────────────────────────────
    "forge_golem": Mob(
        key="forge_golem", name="Forge Golem", emoji="🤖",
        level=2, hp=650, attack=70, defense=50, stamina=250,
        star_reward=2500, is_boss=False,
    ),
    "molten_serpent": Mob(
        key="molten_serpent", name="Molten Serpent", emoji="🐍",
        level=2, hp=580, attack=80, defense=38, stamina=230,
        star_reward=2800, is_boss=False,
    ),
    "forge_master": Mob(
        key="forge_master", name="The Forge Master", emoji="🔥",
        level=2, hp=1100, attack=88, defense=55, stamina=325,
        star_reward=7000, is_boss=True,
    ),

    # ── Level 3: The Crystal Abyss ───────────────────────────
    "crystal_spider": Mob(
        key="crystal_spider", name="Crystal Spider", emoji="🕷️",
        level=3, hp=800, attack=92, defense=55, stamina=275,
        star_reward=3500, is_boss=False,
    ),
    "prism_elemental": Mob(
        key="prism_elemental", name="Prism Elemental", emoji="💎",
        level=3, hp=750, attack=100, defense=48, stamina=260,
        star_reward=4000, is_boss=False,
    ),
    "crystal_queen": Mob(
        key="crystal_queen", name="The Crystal Queen", emoji="👸",
        level=3, hp=1400, attack=110, defense=65, stamina=375,
        star_reward=10000, is_boss=True,
    ),

    # ── Level 4: The Warden's Sanctum ────────────────────────
    "sanctum_knight": Mob(
        key="sanctum_knight", name="Sanctum Knight", emoji="⚔️",
        level=4, hp=1000, attack=115, defense=72, stamina=300,
        star_reward=5000, is_boss=False,
    ),
    "temporal_shade": Mob(
        key="temporal_shade", name="Temporal Shade", emoji="⏳",
        level=4, hp=900, attack=125, defense=58, stamina=280,
        star_reward=5500, is_boss=False,
    ),
    "the_warden": Mob(
        key="the_warden", name="The Warden", emoji="🏛️",
        level=4, hp=1800, attack=135, defense=80, stamina=425,
        star_reward=14000, is_boss=True,
    ),

    # ── Level 5: The Core ────────────────────────────────────
    "core_devourer": Mob(
        key="core_devourer", name="Core Devourer", emoji="🌑",
        level=5, hp=1300, attack=140, defense=85, stamina=325,
        star_reward=7000, is_boss=False,
    ),
    "magma_titan": Mob(
        key="magma_titan", name="Magma Titan", emoji="🌋",
        level=5, hp=1500, attack=130, defense=95, stamina=350,
        star_reward=8000, is_boss=False,
    ),
    "world_heart": Mob(
        key="world_heart", name="The World Heart", emoji="💀",
        level=5, hp=2500, attack=160, defense=100, stamina=500,
        star_reward=20000, is_boss=True,
    ),
}

# Lookup: level -> list of mobs at that level
AETHER_MOBS_BY_LEVEL: Final[dict[int, list[Mob]]] = {}
for _mob in AETHER_MOBS.values():
    AETHER_MOBS_BY_LEVEL.setdefault(_mob.level, []).append(_mob)

# ---------------------------------------------------------------------------
# Death penalties — mirrors DEATH_PENALTIES format
# ---------------------------------------------------------------------------

AETHER_DEATH_PENALTIES: Final[dict[int, dict]] = {
    1: {
        "wallet_loss_pct": 0.50,
        "bank_loss_pct": 0.0,
        "lose_all_items": False,
        "lose_random_items_pct": 0.0,
        "lose_random_equipment": 0,
        "lose_all_equipment": False,
        "description": "Lose 50% of wallet",
    },
    2: {
        "wallet_loss_pct": 0.75,
        "bank_loss_pct": 0.0,
        "lose_all_items": False,
        "lose_random_items_pct": 0.50,
        "lose_random_equipment": 0,
        "lose_all_equipment": False,
        "description": "Lose 75% wallet + 50% random items",
    },
    3: {
        "wallet_loss_pct": 1.0,
        "bank_loss_pct": 0.0,
        "lose_all_items": True,
        "lose_random_items_pct": 0.0,
        "lose_random_equipment": 1,
        "lose_all_equipment": False,
        "description": "Lose 100% wallet + all items + 1 random equipment",
    },
    4: {
        "wallet_loss_pct": 1.0,
        "bank_loss_pct": 0.05,
        "lose_all_items": True,
        "lose_random_items_pct": 0.0,
        "lose_random_equipment": 2,
        "lose_all_equipment": False,
        "description": "Lose 100% wallet + all items + 2 equipment + 5% bank",
    },
    5: {
        "wallet_loss_pct": 1.0,
        "bank_loss_pct": 0.10,
        "lose_all_items": True,
        "lose_random_items_pct": 0.0,
        "lose_random_equipment": 0,
        "lose_all_equipment": True,
        "description": "Lose everything + all equipment + 10% bank",
    },
}

# ---------------------------------------------------------------------------
# Drop tables — per-level loot (item_key, category, sell_value, chance)
# ---------------------------------------------------------------------------

_Drop = tuple[str, str, int, float]

AETHER_DROPS: Final[dict[int, list[_Drop]]] = {
    1: [
        ("health_potion", "consumable", 150, 0.30),
        ("golden_mushroom", "consumable", 75, 0.20),
        ("hollow_stone", "mineral", 900, 0.35),
        ("primordial_dust", "mineral", 1500, 0.20),
        ("coal", "mineral", 50, 0.25),
        ("iron", "mineral", 100, 0.20),
    ],
    2: [
        ("health_potion", "consumable", 150, 0.35),
        ("golden_mushroom", "consumable", 75, 0.25),
        ("forge_cinder", "mineral", 1300, 0.30),
        ("molten_slag", "mineral", 2200, 0.18),
        ("silver", "mineral", 150, 0.20),
        ("emerald", "mineral", 275, 0.12),
    ],
    3: [
        ("health_potion", "consumable", 150, 0.40),
        ("golden_mushroom", "consumable", 75, 0.30),
        ("voidcell", "mineral", 2000, 0.25),
        ("crystal_marrow", "mineral", 3000, 0.15),
        ("platinum", "mineral", 225, 0.18),
        ("sapphire", "mineral", 400, 0.10),
    ],
    4: [
        ("health_potion", "consumable", 150, 0.45),
        ("golden_mushroom", "consumable", 75, 0.35),
        ("warden_seal", "mineral", 2600, 0.22),
        ("temporal_fragment", "mineral", 4000, 0.12),
        ("mithril", "mineral", 350, 0.15),
        ("opal", "mineral", 625, 0.08),
    ],
    5: [
        ("health_potion", "consumable", 150, 0.50),
        ("golden_mushroom", "consumable", 75, 0.40),
        ("core_ember", "mineral", 3500, 0.20),
        ("world_essence", "mineral", 5500, 0.10),
        ("dragonstone", "mineral", 525, 0.12),
        ("void_crystal", "mineral", 900, 0.08),
    ],
}

# Boss bonus drops — in addition to level drops
AETHER_BOSS_BONUS_DROPS: Final[list[_Drop]] = [
    ("health_potion", "consumable", 50, 0.60),
    ("golden_mushroom", "consumable", 25, 0.50),
    ("star_magnet", "equipment", 0, 0.06),
    ("lucky_charm", "equipment", 0, 0.05),
    ("heart_of_leviathan", "equipment", 0, 0.03),
]

# ---------------------------------------------------------------------------
# Aether materials — 15 dungeon-exclusive crafting materials
# ---------------------------------------------------------------------------

AETHER_MATERIALS: Final[dict[str, dict]] = {
    # Level 1
    "hollow_stone": {"name": "Hollow Stone", "emoji": "🪨", "sell": 900, "level": 1},
    "primordial_dust": {"name": "Primordial Dust", "emoji": "✨", "sell": 1500, "level": 1},
    "aether_shard": {"name": "Aether Shard", "emoji": "💠", "sell": 2500, "level": 1},
    # Level 2
    "forge_cinder": {"name": "Forge Cinder", "emoji": "🔥", "sell": 1300, "level": 2},
    "molten_slag": {"name": "Molten Slag", "emoji": "🟠", "sell": 2200, "level": 2},
    "infernal_core": {"name": "Infernal Core", "emoji": "🔴", "sell": 3750, "level": 2},
    # Level 3
    "voidcell": {"name": "Voidcell", "emoji": "🟣", "sell": 2000, "level": 3},
    "crystal_marrow": {"name": "Crystal Marrow", "emoji": "💎", "sell": 3000, "level": 3},
    "prismatic_lens": {"name": "Prismatic Lens", "emoji": "🌈", "sell": 5000, "level": 3},
    # Level 4
    "warden_seal": {"name": "Warden Seal", "emoji": "🏛️", "sell": 2600, "level": 4},
    "temporal_fragment": {"name": "Temporal Fragment", "emoji": "⏳", "sell": 4000, "level": 4},
    "chrono_crystal": {"name": "Chrono Crystal", "emoji": "⌛", "sell": 6500, "level": 4},
    # Level 5
    "core_ember": {"name": "Core Ember", "emoji": "🌋", "sell": 3500, "level": 5},
    "world_essence": {"name": "World Essence", "emoji": "🌍", "sell": 5500, "level": 5},
    "heart_of_the_world": {"name": "Heart of the World", "emoji": "❤️‍🔥", "sell": 10000, "level": 5},
}

# Key materials — rare drops used in T6-T10 crafting recipes
# These are the 3rd material per level (aether_shard, infernal_core, etc.)
AETHER_KEY_MATERIALS: Final[set[str]] = {
    "aether_shard", "infernal_core", "prismatic_lens", "chrono_crystal", "heart_of_the_world",
}

# Key material drop chance (added to boss kills and elite bonus)
KEY_MATERIAL_DROPS: Final[dict[int, list[_Drop]]] = {
    1: [("aether_shard", "mineral", 2500, 0.08)],
    2: [("infernal_core", "mineral", 3750, 0.06)],
    3: [("prismatic_lens", "mineral", 5000, 0.05)],
    4: [("chrono_crystal", "mineral", 6500, 0.04)],
    5: [("heart_of_the_world", "mineral", 10000, 0.03)],
}

# ---------------------------------------------------------------------------
# Floor hazards — per-level hazard pools
# ---------------------------------------------------------------------------

AETHER_HAZARDS: Final[dict[int, list[dict]]] = {
    1: [
        {
            "key": "aether_surge", "name": "Aether Surge", "emoji": "⚡",
            "wallet_loss_pct": 0.15, "lose_items": 0,
            "description": "A surge of aether energy rips through you! Lost **{loss}** stars.",
        },
        {
            "key": "crumbling_floor", "name": "Crumbling Floor", "emoji": "🕳️",
            "wallet_loss_pct": 0.0, "lose_items": 1,
            "description": "The floor crumbles! You drop **{count}** item(s) into the abyss.",
        },
    ],
    2: [
        {
            "key": "forge_blast", "name": "Forge Blast", "emoji": "💥",
            "wallet_loss_pct": 0.25, "lose_items": 0,
            "description": "A forge blast scorches you! Lost **{loss}** stars.",
        },
        {
            "key": "molten_splash", "name": "Molten Splash", "emoji": "🔥",
            "wallet_loss_pct": 0.0, "lose_items": 0, "hp_loss": 15,
            "description": "Molten metal splashes you! You'll start the next fight with **-15 HP**.",
        },
    ],
    3: [
        {
            "key": "crystal_shatter", "name": "Crystal Shatter", "emoji": "💎",
            "wallet_loss_pct": 0.0, "lose_items": 2,
            "description": "Crystals shatter around you! You drop **{count}** item(s).",
        },
        {
            "key": "void_whisper", "name": "Void Whisper", "emoji": "🌀",
            "wallet_loss_pct": 0.0, "lose_items": 0, "halve_stamina": True,
            "description": "A void whisper drains your energy! Stamina **halved**.",
        },
    ],
    4: [
        {
            "key": "temporal_rift", "name": "Temporal Rift", "emoji": "⏳",
            "wallet_loss_pct": 0.30, "lose_items": 1,
            "description": "A temporal rift tears at you! Lost **{loss}** stars and **{count}** item(s).",
        },
        {
            "key": "wardens_curse", "name": "Warden's Curse", "emoji": "🏛️",
            "wallet_loss_pct": 0.0, "lose_items": 0, "max_hp_reduction": 20,
            "description": "The Warden curses you! **Max HP reduced by 20** for 3 fights.",
        },
    ],
    5: [
        {
            "key": "core_eruption", "name": "Core Eruption", "emoji": "🌋",
            "wallet_loss_pct": 0.40, "lose_lowest_items": True,
            "description": "The Core erupts! Lost **{loss}** stars and all your cheapest items.",
        },
        {
            "key": "seismic_collapse", "name": "Seismic Collapse", "emoji": "💀",
            "wallet_loss_pct": 0.0, "lose_items": 0, "trigger_fight": True,
            "description": "Seismic collapse! Another enemy emerges immediately!",
        },
    ],
}

# Base hazard chance per level (15-25%, scaling)
HAZARD_BASE_CHANCE: Final[dict[int, float]] = {
    1: 0.15, 2: 0.17, 3: 0.20, 4: 0.22, 5: 0.25,
}

# ---------------------------------------------------------------------------
# Daily modifiers
# ---------------------------------------------------------------------------

AETHER_DAILY_MODIFIERS: Final[list[dict]] = [
    {
        "key": "fortified_foes",
        "name": "Fortified Foes",
        "emoji": "💪",
        "description": "Mobs have +30% HP. Material drop rates doubled.",
        "mob_hp_mult": 1.30,
        "drop_mult": 2.0,
    },
    {
        "key": "key_surge",
        "name": "Key Surge",
        "emoji": "🔑",
        "description": "Key material drop rates doubled. Death penalty one level harsher.",
        "key_drop_mult": 2.0,
        "harsher_penalty": True,
    },
    {
        "key": "calm_depths",
        "name": "Calm Depths",
        "emoji": "😌",
        "description": "No hazards today. No PvP allowed.",
        "no_hazards": True,
        "no_pvp": True,
    },
    {
        "key": "goblin_market",
        "name": "Goblin Market",
        "emoji": "🧌",
        "description": "Blaze Goblin appears 3x more often!",
        "goblin_mult": 3.0,
    },
]

DAILY_MODIFIER_CHANCE: Final[float] = 0.20

# ---------------------------------------------------------------------------
# Elite mobs
# ---------------------------------------------------------------------------

ELITE_CHANCE: Final[float] = 0.05
ELITE_STAT_BONUS: Final[float] = 0.50
ELITE_KEY_MATERIAL_CHANCE: Final[float] = 0.15  # additive to normal drops

# ---------------------------------------------------------------------------
# PvP
# ---------------------------------------------------------------------------

PVP_KILL_REWARD_PCT: Final[float] = 0.25
PVP_COOLDOWN_SECONDS: Final[int] = 300  # 5 minutes

# ---------------------------------------------------------------------------
# Blaze Goblin
# ---------------------------------------------------------------------------

BLAZE_GOBLIN_CHANCE: Final[float] = 0.05
BLAZE_GOBLIN_INTERVAL: Final[int] = 5  # minutes
BLAZE_GOBLIN_COOLDOWN: Final[int] = 1800  # 30 minutes between encounters
BLAZE_GOBLIN_TIMEOUT: Final[int] = 60  # seconds before view expires
BLAZE_GOBLIN_SELL_RATE: Final[float] = 0.70  # 70% of normal sell value
BLAZE_GOBLIN_BUY_MARKUP: Final[float] = 1.50  # 150% of normal price
BLAZE_GOBLIN_MAX_STASH: Final[int] = 5

BLAZE_GOBLIN_STOCK: Final[dict[int, list[tuple[str, int]]]] = {
    1: [("health_potion", 225), ("golden_mushroom", 120)],
    2: [("health_potion", 225), ("golden_mushroom", 120), ("stamina_tonic", 360)],
    3: [("health_potion", 225), ("golden_mushroom", 120), ("stamina_tonic", 360)],
    4: [("health_potion", 225), ("golden_mushroom", 120), ("stamina_tonic", 360), ("minor_stamina_brew", 180), ("jackhammer", 25000)],
    5: [("health_potion", 225), ("golden_mushroom", 120), ("stamina_tonic", 360), ("minor_stamina_brew", 180), ("void_energy_flask", 600), ("jackhammer", 25000)],
}

# ---------------------------------------------------------------------------
# Gate / progression
# ---------------------------------------------------------------------------

WINS_PER_AETHER_LEVEL: Final[int] = 5

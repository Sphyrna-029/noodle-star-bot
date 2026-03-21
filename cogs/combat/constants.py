"""Combat system constants — items, mobs, recipes, fish roles, death penalties."""

from typing import Final

from config.models import CombatItem, CraftRecipe, Mob

# ---------------------------------------------------------------------------
# Base stats
# ---------------------------------------------------------------------------
BASE_HP: Final[int] = 100
BASE_STAMINA: Final[int] = 100
STAMINA_PER_ATTACK: Final[int] = 8
STAMINA_PER_DEFEND: Final[int] = 3
STAMINA_PER_CONSUME: Final[int] = 3
MOB_STAMINA_PER_ATTACK: Final[int] = 6
HP_REGEN_PER_MINUTE: Final[int] = 4
STAMINA_REGEN_PER_MINUTE: Final[int] = 8
DAMAGE_FLOOR: Final[float] = 0.20  # minimum damage multiplier at 0 stamina


def calc_defend_stamina_cost(player_defense: int, incoming_attack: int) -> int:
    """Calculate stamina cost for defending based on defense-to-attack ratio.

    At 2x defense, 50% reduction. At 3x+, 66% cap (minimum 1 stamina).
    Below 2x, no reduction (full STAMINA_PER_DEFEND cost).
    """
    if incoming_attack <= 0:
        reduction = 0.66
    else:
        ratio = player_defense / incoming_attack
        if ratio < 2.0:
            return STAMINA_PER_DEFEND
        elif ratio >= 3.0:
            reduction = 0.66
        else:
            # Linear from 50% to 66% between 2x and 3x
            reduction = 0.50 + (ratio - 2.0) * 0.16
    return max(1, round(STAMINA_PER_DEFEND * (1 - reduction)))

# ---------------------------------------------------------------------------
# Combat items — 26 total across 5 tiers
# Tier 1: Store-bought (4 items)
# Tier 2: Crafted (5 items)
# Tier 3: Crafted (5 items) + 2 drop-only (golden_axe, mithril_shield)
# Tier 4: Crafted (6 items)
# Tier 5: Crafted (4 items)
# ---------------------------------------------------------------------------

COMBAT_ITEMS: Final[dict[str, CombatItem]] = {
    # ── Tier 1: Store-bought starters ──────────────────────────
    "wooden_sword": CombatItem(
        key="wooden_sword", name="Wooden Sword", emoji="🗡️",
        slot="weapon", tier=1, attack=8, defense=0, hp_bonus=0,
        stamina_cost=8, description="A basic wooden sword. Gets the job done.",
    ),
    "wooden_shield": CombatItem(
        key="wooden_shield", name="Wooden Shield", emoji="🛡️",
        slot="shield", tier=1, attack=0, defense=6, hp_bonus=0,
        stamina_cost=0, description="A simple wooden shield for blocking.",
    ),
    "leather_vest": CombatItem(
        key="leather_vest", name="Leather Vest", emoji="🦺",
        slot="armor", tier=1, attack=0, defense=4, hp_bonus=15,
        stamina_cost=0, description="Light leather armor. Better than nothing.",
    ),
    "iron_dagger": CombatItem(
        key="iron_dagger", name="Iron Dagger", emoji="🔪",
        slot="weapon", tier=1, attack=6, defense=0, hp_bonus=0,
        stamina_cost=6, description="A quick iron dagger. Low damage, low stamina cost.",
    ),

    # ── Tier 2: Crafted ───────────────────────────────────────
    "iron_sword": CombatItem(
        key="iron_sword", name="Iron Sword", emoji="⚔️",
        slot="weapon", tier=2, attack=14, defense=0, hp_bonus=0,
        stamina_cost=8, description="A sturdy iron blade forged from mined iron.",
    ),
    "iron_shield": CombatItem(
        key="iron_shield", name="Iron Shield", emoji="🛡️",
        slot="shield", tier=2, attack=0, defense=10, hp_bonus=5,
        stamina_cost=0, description="An iron-reinforced shield.",
    ),
    "chainmail": CombatItem(
        key="chainmail", name="Chainmail Armor", emoji="⛓️",
        slot="armor", tier=2, attack=0, defense=8, hp_bonus=25,
        stamina_cost=0, description="Linked iron rings provide solid protection.",
    ),
    "silver_rapier": CombatItem(
        key="silver_rapier", name="Silver Rapier", emoji="🤺",
        slot="weapon", tier=2, attack=12, defense=2, hp_bonus=0,
        stamina_cost=7, description="An elegant silver blade with a parrying guard.",
    ),
    "studded_buckler": CombatItem(
        key="studded_buckler", name="Studded Buckler", emoji="🔰",
        slot="shield", tier=2, attack=2, defense=12, hp_bonus=0,
        stamina_cost=0, description="A small shield with iron studs for bashing.",
    ),

    # ── Tier 3: Crafted ───────────────────────────────────────
    "platinum_blade": CombatItem(
        key="platinum_blade", name="Platinum Blade", emoji="✨",
        slot="weapon", tier=3, attack=22, defense=0, hp_bonus=0,
        stamina_cost=9, description="A gleaming platinum sword of remarkable sharpness.",
    ),
    "emerald_aegis": CombatItem(
        key="emerald_aegis", name="Emerald Aegis", emoji="💚",
        slot="shield", tier=3, attack=0, defense=18, hp_bonus=10,
        stamina_cost=0, description="A crystalline shield infused with emerald power.",
    ),
    "mithril_plate": CombatItem(
        key="mithril_plate", name="Mithril Plate", emoji="🔵",
        slot="armor", tier=3, attack=0, defense=14, hp_bonus=40,
        stamina_cost=0, description="Lightweight yet incredibly strong mithril armor.",
    ),
    "sapphire_lance": CombatItem(
        key="sapphire_lance", name="Sapphire Lance", emoji="💙",
        slot="weapon", tier=3, attack=18, defense=4, hp_bonus=0,
        stamina_cost=8, description="A long lance tipped with a sapphire crystal.",
    ),
    "ruby_guardian": CombatItem(
        key="ruby_guardian", name="Ruby Guardian", emoji="❤️",
        slot="shield", tier=3, attack=4, defense=16, hp_bonus=15,
        stamina_cost=0, description="A ruby-encrusted shield that pulses with warmth.",
    ),
    "golden_axe": CombatItem(
        key="golden_axe", name="Golden Axe", emoji="🪓",
        slot="weapon", tier=3, attack=20, defense=2, hp_bonus=0,
        stamina_cost=9, description="A legendary golden axe found in the wild. Devastating cleave.",
    ),
    "mithril_shield": CombatItem(
        key="mithril_shield", name="Mithril Shield", emoji="🛡️",
        slot="shield", tier=3, attack=0, defense=20, hp_bonus=10,
        stamina_cost=0, description="A rare mithril shield found in the wild. Nearly unbreakable.",
    ),

    # ── Tier 4: Crafted ───────────────────────────────────────
    "star_fragment_blade": CombatItem(
        key="star_fragment_blade", name="Star Fragment Blade", emoji="🌟",
        slot="weapon", tier=4, attack=32, defense=0, hp_bonus=0,
        stamina_cost=10, description="A blade forged from a fallen star fragment.",
    ),
    "opal_fortress": CombatItem(
        key="opal_fortress", name="Opal Fortress", emoji="🌈",
        slot="shield", tier=4, attack=0, defense=26, hp_bonus=20,
        stamina_cost=0, description="An iridescent shield that shimmers with opal light.",
    ),
    "adamantium_mail": CombatItem(
        key="adamantium_mail", name="Adamantium Mail", emoji="⛓️",
        slot="armor", tier=4, attack=0, defense=22, hp_bonus=60,
        stamina_cost=0, description="Nearly indestructible armor woven from adamantium.",
    ),
    "dragonstone_axe": CombatItem(
        key="dragonstone_axe", name="Dragonstone Axe", emoji="🪓",
        slot="weapon", tier=4, attack=28, defense=6, hp_bonus=0,
        stamina_cost=9, description="A massive axe with a dragonstone core.",
    ),
    "void_crystal_ward": CombatItem(
        key="void_crystal_ward", name="Void Crystal Ward", emoji="🔮",
        slot="shield", tier=4, attack=6, defense=24, hp_bonus=10,
        stamina_cost=0, description="A shield that absorbs energy from the void.",
    ),
    "titanium_cuirass": CombatItem(
        key="titanium_cuirass", name="Titanium Cuirass", emoji="⚪",
        slot="armor", tier=4, attack=4, defense=20, hp_bonus=50,
        stamina_cost=0, description="Precision-forged titanium body armor.",
    ),

    # ── Tier 5: Crafted (endgame) ─────────────────────────────
    "noodle_gem_katana": CombatItem(
        key="noodle_gem_katana", name="Noodle Gem Katana", emoji="🍜",
        slot="weapon", tier=5, attack=45, defense=5, hp_bonus=0,
        stamina_cost=10, description="The legendary katana made from a Noodle Gem. Unmatched power.",
    ),
    "eternity_bulwark": CombatItem(
        key="eternity_bulwark", name="Eternity Bulwark", emoji="👑",
        slot="shield", tier=5, attack=0, defense=35, hp_bonus=30,
        stamina_cost=0, description="A shield said to endure until the end of time.",
    ),
    "darkite_warplate": CombatItem(
        key="darkite_warplate", name="Darkite Warplate", emoji="🌑",
        slot="armor", tier=5, attack=8, defense=30, hp_bonus=80,
        stamina_cost=0, description="Impossibly dark armor that seems to consume light itself.",
    ),
    "void_reaper": CombatItem(
        key="void_reaper", name="Void Reaper", emoji="⚛️",
        slot="weapon", tier=5, attack=40, defense=0, hp_bonus=0,
        stamina_cost=8, description="A scythe forged from pure Dark Matter. Terrifyingly efficient.",
    ),

    # ── Tier 6: Space-tier (Aetherdepths + Moon) ──────────────
    "spiker": CombatItem(
        key="spiker", name="Spiker", emoji="📌",
        slot="weapon", tier=6, attack=58, defense=0, hp_bonus=0,
        stamina_cost=11, description="A crude but devastating weapon that fires superheated metal spikes.",
    ),
    "plasma_pistol": CombatItem(
        key="plasma_pistol", name="Plasma Pistol", emoji="🔫",
        slot="weapon", tier=6, attack=52, defense=6, hp_bonus=0,
        stamina_cost=10, description="A compact sidearm that fires bolts of superheated plasma.",
    ),
    "lunar_barrier": CombatItem(
        key="lunar_barrier", name="Lunar Barrier", emoji="🌙",
        slot="shield", tier=6, attack=0, defense=46, hp_bonus=25,
        stamina_cost=0, description="An energy barrier that bends moonlight into a protective shell.",
    ),
    "lunar_exosuit": CombatItem(
        key="lunar_exosuit", name="Lunar Exosuit", emoji="🌑",
        slot="armor", tier=6, attack=0, defense=40, hp_bonus=100,
        stamina_cost=0, description="A pressurized exosuit built for lunar combat operations.",
    ),

    # ── Tier 7: Mars-tier ────────────────────────────────────
    "plasma_rifle": CombatItem(
        key="plasma_rifle", name="Plasma Rifle", emoji="🔴",
        slot="weapon", tier=7, attack=75, defense=0, hp_bonus=0,
        stamina_cost=12, description="A fully automatic plasma weapon that overheats with sustained fire.",
    ),
    "plasma_repeater": CombatItem(
        key="plasma_repeater", name="Plasma Repeater", emoji="🟣",
        slot="weapon", tier=7, attack=68, defense=8, hp_bonus=0,
        stamina_cost=11, description="A rapid-fire plasma weapon with a built-in cooling vent.",
    ),
    "thermal_deflector": CombatItem(
        key="thermal_deflector", name="Thermal Deflector", emoji="🌋",
        slot="shield", tier=7, attack=0, defense=60, hp_bonus=30,
        stamina_cost=0, description="A heat-resistant energy shield that absorbs thermal attacks.",
    ),
    "crimson_exoplate": CombatItem(
        key="crimson_exoplate", name="Crimson Exoplate", emoji="🧲",
        slot="armor", tier=7, attack=0, defense=52, hp_bonus=120,
        stamina_cost=0, description="Heavy crimson armor plating forged from Martian alloys.",
    ),

    # ── Tier 8: Saturn-tier ──────────────────────────────────
    "needler": CombatItem(
        key="needler", name="Needler", emoji="💜",
        slot="weapon", tier=8, attack=95, defense=0, hp_bonus=0,
        stamina_cost=13, description="Fires crystalline needles that track targets and detonate.",
    ),
    "fuel_rod_cannon": CombatItem(
        key="fuel_rod_cannon", name="Fuel Rod Cannon", emoji="☢️",
        slot="weapon", tier=8, attack=88, defense=10, hp_bonus=0,
        stamina_cost=12, description="A heavy weapon that launches explosive fuel rod projectiles.",
    ),
    "particle_shield": CombatItem(
        key="particle_shield", name="Particle Shield", emoji="🪐",
        slot="shield", tier=8, attack=0, defense=75, hp_bonus=40,
        stamina_cost=0, description="A shield woven from accelerated particles and ring debris.",
    ),
    "prismatic_suit": CombatItem(
        key="prismatic_suit", name="Prismatic Suit", emoji="💎",
        slot="armor", tier=8, attack=0, defense=65, hp_bonus=145,
        stamina_cost=0, description="Light-bending armor that refracts incoming energy attacks.",
    ),

    # ── Tier 9: Uranus-tier ──────────────────────────────────
    "energy_sword": CombatItem(
        key="energy_sword", name="Energy Sword", emoji="⚡",
        slot="weapon", tier=9, attack=115, defense=0, hp_bonus=0,
        stamina_cost=14, description="A blade of pure plasma contained by magnetic fields. Lethal in close quarters.",
    ),
    "beam_rifle": CombatItem(
        key="beam_rifle", name="Beam Rifle", emoji="🔦",
        slot="weapon", tier=9, attack=108, defense=12, hp_bonus=0,
        stamina_cost=13, description="A long-range particle beam weapon of devastating precision.",
    ),
    "hardlight_shield": CombatItem(
        key="hardlight_shield", name="Hardlight Shield", emoji="🛡️",
        slot="shield", tier=9, attack=0, defense=90, hp_bonus=50,
        stamina_cost=0, description="A shield of solidified light particles, nearly impervious.",
    ),
    "cryo_armor": CombatItem(
        key="cryo_armor", name="Cryo Armor", emoji="❄️",
        slot="armor", tier=9, attack=0, defense=78, hp_bonus=170,
        stamina_cost=0, description="Supercooled armor that flash-freezes projectiles on impact.",
    ),

    # ── Tier 10: Pluto-tier (endgame) ────────────────────────
    "gravity_hammer": CombatItem(
        key="gravity_hammer", name="Gravity Hammer", emoji="🔨",
        slot="weapon", tier=10, attack=135, defense=0, hp_bonus=0,
        stamina_cost=15, description="A massive hammer that manipulates gravity to crush all opposition.",
    ),
    "prophets_bane": CombatItem(
        key="prophets_bane", name="Prophet's Bane", emoji="🗡️",
        slot="weapon", tier=10, attack=128, defense=15, hp_bonus=0,
        stamina_cost=14, description="A legendary energy blade. Those it marks do not survive.",
    ),
    "void_shield": CombatItem(
        key="void_shield", name="Void Shield", emoji="🌑",
        slot="shield", tier=10, attack=0, defense=106, hp_bonus=60,
        stamina_cost=0, description="A shield that opens micro-rifts in space to absorb attacks.",
    ),
    "siege_plate": CombatItem(
        key="siege_plate", name="Siege Plate", emoji="🪐",
        slot="armor", tier=10, attack=0, defense=90, hp_bonus=200,
        stamina_cost=0, description="The ultimate armor. Forged from planetary cores for total war.",
    ),
}

# ---------------------------------------------------------------------------
# Mobs — 24 total: 5 per level (L1-4), 4 at L5, 1 boss per level
# ---------------------------------------------------------------------------

MOBS: Final[dict[str, Mob]] = {
    # ── Level 1: Training Grounds ──────────────────────────────
    "slime": Mob(
        key="slime", name="Slime", emoji="🟢",
        level=1, hp=38, attack=6, defense=3, stamina=50,
        star_reward=30, is_boss=False,
    ),
    "rat": Mob(
        key="rat", name="Giant Rat", emoji="🐀",
        level=1, hp=44, attack=9, defense=4, stamina=60,
        star_reward=35, is_boss=False,
    ),
    "bat": Mob(
        key="bat", name="Cave Bat", emoji="🦇",
        level=1, hp=32, attack=10, defense=2, stamina=38,
        star_reward=32, is_boss=False,
    ),
    "mushroom_fiend": Mob(
        key="mushroom_fiend", name="Mushroom Fiend", emoji="🍄",
        level=1, hp=50, attack=8, defense=5, stamina=75,
        star_reward=40, is_boss=False,
    ),
    "goblin_chief": Mob(
        key="goblin_chief", name="Goblin Chief", emoji="👺",
        level=1, hp=100, attack=15, defense=8, stamina=100,
        star_reward=130, is_boss=True,
    ),

    # ── Level 2: Dark Corridors ────────────────────────────────
    "skeleton": Mob(
        key="skeleton", name="Skeleton Warrior", emoji="💀",
        level=2, hp=75, attack=18, defense=10, stamina=88,
        star_reward=80, is_boss=False,
    ),
    "spider": Mob(
        key="spider", name="Giant Spider", emoji="🕷️",
        level=2, hp=62, attack=20, defense=6, stamina=75,
        star_reward=70, is_boss=False,
    ),
    "zombie": Mob(
        key="zombie", name="Armored Zombie", emoji="🧟",
        level=2, hp=94, attack=15, defense=15, stamina=100,
        star_reward=85, is_boss=False,
    ),
    "ghost": Mob(
        key="ghost", name="Phantom", emoji="👻",
        level=2, hp=56, attack=22, defense=4, stamina=62,
        star_reward=95, is_boss=False,
    ),
    "troll_warlord": Mob(
        key="troll_warlord", name="Troll Warlord", emoji="🧌",
        level=2, hp=188, attack=28, defense=18, stamina=138,
        star_reward=260, is_boss=True,
    ),

    # ── Level 3: Cursed Halls ──────────────────────────────────
    "dark_knight": Mob(
        key="dark_knight", name="Dark Knight", emoji="🖤",
        level=3, hp=150, attack=30, defense=22, stamina=125,
        star_reward=425, is_boss=False,
    ),
    "fire_elemental": Mob(
        key="fire_elemental", name="Fire Elemental", emoji="🔥",
        level=3, hp=112, attack=38, defense=12, stamina=112,
        star_reward=475, is_boss=False,
    ),
    "gargoyle": Mob(
        key="gargoyle", name="Stone Gargoyle", emoji="🗿",
        level=3, hp=175, attack=25, defense=32, stamina=150,
        star_reward=500, is_boss=False,
    ),
    "wraith": Mob(
        key="wraith", name="Soul Wraith", emoji="😈",
        level=3, hp=125, attack=35, defense=15, stamina=100,
        star_reward=450, is_boss=False,
    ),
    "lich": Mob(
        key="lich", name="The Lich", emoji="☠️",
        level=3, hp=312, attack=40, defense=25, stamina=175,
        star_reward=1200, is_boss=True,
    ),

    # ── Level 4: Infernal Depths ───────────────────────────────
    "demon": Mob(
        key="demon", name="Infernal Demon", emoji="👿",
        level=4, hp=250, attack=45, defense=28, stamina=162,
        star_reward=800, is_boss=False,
    ),
    "golem": Mob(
        key="golem", name="Iron Golem", emoji="🤖",
        level=4, hp=350, attack=35, defense=44, stamina=200,
        star_reward=900, is_boss=False,
    ),
    "hydra": Mob(
        key="hydra", name="Lesser Hydra", emoji="🐍",
        level=4, hp=275, attack=48, defense=22, stamina=150,
        star_reward=950, is_boss=False,
    ),
    "shadow_dragon": Mob(
        key="shadow_dragon", name="Shadow Drake", emoji="🐲",
        level=4, hp=300, attack=42, defense=35, stamina=175,
        star_reward=1000, is_boss=False,
    ),
    "balrog": Mob(
        key="balrog", name="The Balrog", emoji="😤",
        level=4, hp=500, attack=52, defense=38, stamina=225,
        star_reward=2500, is_boss=True,
    ),

    # ── Level 5: The Void ──────────────────────────────────────
    "void_sentinel": Mob(
        key="void_sentinel", name="Void Sentinel", emoji="🌌",
        level=5, hp=438, attack=56, defense=44, stamina=212,
        star_reward=1500, is_boss=False,
    ),
    "cosmic_horror": Mob(
        key="cosmic_horror", name="Cosmic Horror", emoji="👁️",
        level=5, hp=375, attack=62, defense=32, stamina=188,
        star_reward=1800, is_boss=False,
    ),
    "noodle_titan": Mob(
        key="noodle_titan", name="Noodle Titan", emoji="🍝",
        level=5, hp=500, attack=52, defense=50, stamina=225,
        star_reward=2000, is_boss=False,
    ),
    "the_void_king": Mob(
        key="the_void_king", name="The Void King", emoji="💀",
        level=5, hp=750, attack=68, defense=50, stamina=250,
        star_reward=5000, is_boss=True,
    ),
}

# Lookup: level -> list of mobs at that level
MOBS_BY_LEVEL: Final[dict[int, list[Mob]]] = {}
for _mob in MOBS.values():
    MOBS_BY_LEVEL.setdefault(_mob.level, []).append(_mob)

# ---------------------------------------------------------------------------
# Dungeon level info
# ---------------------------------------------------------------------------

DUNGEON_LEVELS: Final[dict[int, dict]] = {
    1: {"name": "Training Grounds", "emoji": "🏋️", "unlock_cost": 0},
    2: {"name": "Dark Corridors", "emoji": "🕯️", "unlock_cost": 500},
    3: {"name": "Cursed Halls", "emoji": "🏚️", "unlock_cost": 2000},
    4: {"name": "Infernal Depths", "emoji": "🔥", "unlock_cost": 5000},
    5: {"name": "The Void", "emoji": "🌌", "unlock_cost": 10000},
}

# ---------------------------------------------------------------------------
# Death penalties by dungeon level
# ---------------------------------------------------------------------------

DEATH_PENALTIES: Final[dict[int, dict]] = {
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
        "wallet_loss_pct": 1.0,
        "bank_loss_pct": 0.0,
        "lose_all_items": False,
        "lose_random_items_pct": 0.50,
        "lose_random_equipment": 0,
        "lose_all_equipment": False,
        "description": "Lose 100% wallet + 50% of random items",
    },
    3: {
        "wallet_loss_pct": 1.0,
        "bank_loss_pct": 0.0,
        "lose_all_items": True,
        "lose_random_items_pct": 0.0,
        "lose_random_equipment": 0,
        "lose_all_equipment": False,
        "description": "Lose 100% wallet + all items",
    },
    4: {
        "wallet_loss_pct": 1.0,
        "bank_loss_pct": 0.0,
        "lose_all_items": True,
        "lose_random_items_pct": 0.0,
        "lose_random_equipment": 2,
        "lose_all_equipment": False,
        "description": "Lose 100% wallet + all items + 2 random equipment",
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
# HP recovery — fish, crops, and potions that restore HP via !consume
# ---------------------------------------------------------------------------

CROP_HEAL_VALUES: Final[dict[str, int]] = {
    "wheat": 8,       # sell 40
    "carrot": 18,     # sell 90
    "corn": 35,       # sell 200
    "tomato": 55,     # sell 440
    "melon": 80,      # sell 960 — also restores stamina (see STAMINA_RECOVERY)
}

FISH_HEAL_VALUES: Final[dict[str, int]] = {
    # Level 1 fish — sell value → HP (diminishing-returns curve)
    "small_fish": 8,       # sell 30
    "crab": 14,            # sell 50
    "shrimp": 16,          # sell 60
    "salmon": 34,          # sell 160
    "tuna": 44,            # sell 260
    "lobster": 52,         # sell 360
    "octopus": 62,         # sell 520 — also restores stamina
    # Level 2 fish
    "trout": 12,           # sell 45
    "catfish": 18,         # sell 65
    "bass": 22,            # sell 95
    "river_salmon": 40,    # sell 225
    "sturgeon": 55,        # sell 375
    "snapping_turtle": 65, # sell 560 — also restores stamina
    "giant_catfish": 75,   # sell 750 — also restores stamina
    # Level 3 fish
    "clownfish": 10,       # sell 35
    "parrotfish": 20,      # sell 75
    "sea_urchin": 26,      # sell 110
    "moray_eel": 30,       # sell 145
    "reef_shark": 48,      # sell 295
    # Level 4 fish
    "anglerfish": 14,      # sell 50
    "barracuda": 24,       # sell 105
    "swordfish": 32,       # sell 155
    # Level 5 fish
    "abyssal_crab": 20,    # sell 75
}

# ---------------------------------------------------------------------------
# Stamina recovery — fish and potions that restore stamina via !consume
# ---------------------------------------------------------------------------

STAMINA_RECOVERY: Final[dict[str, int]] = {
    # Farming consumables
    "raw_potato": 6,
    "stamina_elixir": 18,
    "golden_mushroom": 40,
    # Junk fish that restore stamina (keys match stored inventory format)
    "seaweed": 10,
    "driftwood": 8,
    "starfish": 12,
    "rusty_anchor": 16,
    "sea_sponge": 10,
    "void_coral": 20,
    "bioluminescent_jelly": 24,
    "barnacle_cluster": 12,
    "old_boot": 6,
    # Crafted potions
    "minor_stamina_brew": 50,
    "stamina_tonic": 80,
    "void_energy_flask": 100,
    # High-value dual-restore food (also restores HP — see FISH/CROP heal values)
    "octopus": 15,
    "snapping_turtle": 20,
    "giant_catfish": 30,
    "melon": 40,
}

# ---------------------------------------------------------------------------
# Crafting materials from fish — maps fish name to crafting material key
# 19 fish are crafting ingredients
# ---------------------------------------------------------------------------

FISH_CRAFT_MATERIALS: Final[dict[str, str]] = {
    # These fish are used as-is in crafting recipes
    "Golden Fish": "golden_fish",
    "Giant Squid": "giant_squid",
    "Mermaid's Pearl": "mermaids_pearl",
    "Platinum Trout": "platinum_trout",
    "River Dragon": "river_dragon",
    "Lost Crown": "lost_crown",
    "Golden Seahorse": "golden_seahorse",
    "Coral Golem": "coral_golem",
    "Neptune's Trident": "neptunes_trident",
    "Phantom Captain": "phantom_captain",
    "Diamond Anchor": "diamond_anchor",
    "Leviathan Scale": "leviathan_scale",
    "Poseidon's Eye": "poseidons_eye",
    "World Serpent Fang": "world_serpent_fang",
    "Heart of the Abyss": "heart_of_the_abyss",
    "Ancient Artifact": "ancient_artifact",
    "River Spirit Gem": "river_spirit_gem",
    "Pearl of the Deep": "pearl_of_the_deep",
    "Davy Jones' Chest": "davy_jones_chest",
}

# ---------------------------------------------------------------------------
# Crafting recipes
# ---------------------------------------------------------------------------

CRAFT_RECIPES: Final[dict[str, CraftRecipe]] = {
    # ── Tier 2 weapons/shields/armor ──────────────────────────
    "iron_sword": CraftRecipe(
        result_key="iron_sword", result_name="Iron Sword", result_emoji="⚔️",
        ingredients=(("iron", 3), ("coal", 2)),
        description="Forge an iron sword from mined iron and coal.",
    ),
    "iron_shield": CraftRecipe(
        result_key="iron_shield", result_name="Iron Shield", result_emoji="🛡️",
        ingredients=(("iron", 4), ("stone", 2)),
        description="Hammer iron over stone to form a sturdy shield.",
    ),
    "chainmail": CraftRecipe(
        result_key="chainmail", result_name="Chainmail Armor", result_emoji="⛓️",
        ingredients=(("iron", 5), ("copper", 3)),
        description="Link iron rings with copper fasteners.",
    ),
    "silver_rapier": CraftRecipe(
        result_key="silver_rapier", result_name="Silver Rapier", result_emoji="🤺",
        ingredients=(("silver", 3), ("gold", 1)),
        description="A silver blade with a gold-plated guard.",
    ),
    "studded_buckler": CraftRecipe(
        result_key="studded_buckler", result_name="Studded Buckler", result_emoji="🔰",
        ingredients=(("iron", 3), ("copper", 2), ("stone", 1)),
        description="A compact shield reinforced with iron studs.",
    ),

    # ── Tier 3 ────────────────────────────────────────────────
    "platinum_blade": CraftRecipe(
        result_key="platinum_blade", result_name="Platinum Blade", result_emoji="✨",
        ingredients=(("platinum", 4), ("silver", 2), ("golden_fish", 1)),
        description="A gleaming platinum sword tempered with golden fish oil.",
    ),
    "emerald_aegis": CraftRecipe(
        result_key="emerald_aegis", result_name="Emerald Aegis", result_emoji="💚",
        ingredients=(("emerald", 3), ("mithril", 2)),
        description="An emerald-infused shield reinforced with mithril.",
    ),
    "mithril_plate": CraftRecipe(
        result_key="mithril_plate", result_name="Mithril Plate", result_emoji="🔵",
        ingredients=(("mithril", 5), ("titanium", 2)),
        description="Lightweight mithril armor plating.",
    ),
    "sapphire_lance": CraftRecipe(
        result_key="sapphire_lance", result_name="Sapphire Lance", result_emoji="💙",
        ingredients=(("sapphire", 3), ("platinum", 2), ("river_dragon", 1)),
        description="A lance tipped with sapphire, imbued with river dragon essence.",
    ),
    "ruby_guardian": CraftRecipe(
        result_key="ruby_guardian", result_name="Ruby Guardian", result_emoji="❤️",
        ingredients=(("ruby", 3), ("emerald", 1), ("mermaids_pearl", 1)),
        description="A ruby shield enchanted with mermaid's pearl magic.",
    ),

    # ── Tier 4 ────────────────────────────────────────────────
    "star_fragment_blade": CraftRecipe(
        result_key="star_fragment_blade", result_name="Star Fragment Blade", result_emoji="🌟",
        ingredients=(("star_fragment", 3), ("amethyst", 2), ("neptunes_trident", 1)),
        description="A blade forged from star fragments and Neptune's power.",
    ),
    "opal_fortress": CraftRecipe(
        result_key="opal_fortress", result_name="Opal Fortress", result_emoji="🌈",
        ingredients=(("opal", 4), ("dragonstone", 2)),
        description="A fortress-like shield of shimmering opal.",
    ),
    "adamantium_mail": CraftRecipe(
        result_key="adamantium_mail", result_name="Adamantium Mail", result_emoji="⛓️",
        ingredients=(("adamantium", 5), ("titanium", 3), ("diamond_anchor", 1)),
        description="Nearly indestructible mail forged from adamantium.",
    ),
    "dragonstone_axe": CraftRecipe(
        result_key="dragonstone_axe", result_name="Dragonstone Axe", result_emoji="🪓",
        ingredients=(("dragonstone", 4), ("obsidian", 3), ("leviathan_scale", 1)),
        description="A massive axe with a dragonstone edge and leviathan handle.",
    ),
    "void_crystal_ward": CraftRecipe(
        result_key="void_crystal_ward", result_name="Void Crystal Ward", result_emoji="🔮",
        ingredients=(("void_crystal", 3), ("darkite", 2), ("poseidons_eye", 1)),
        description="A shield infused with void energy and deep sea power.",
    ),
    "titanium_cuirass": CraftRecipe(
        result_key="titanium_cuirass", result_name="Titanium Cuirass", result_emoji="⚪",
        ingredients=(("titanium", 5), ("mithril", 2), ("phantom_captain", 1)),
        description="Precision body armor haunted by a phantom captain's spirit.",
    ),

    # ── Tier 5 ────────────────────────────────────────────────
    "noodle_gem_katana": CraftRecipe(
        result_key="noodle_gem_katana", result_name="Noodle Gem Katana", result_emoji="🍜",
        ingredients=(("noodle_gem", 2), ("star_fragment", 3), ("world_serpent_fang", 1)),
        description="The ultimate weapon — a katana of pure Noodle Gem.",
    ),
    "eternity_bulwark": CraftRecipe(
        result_key="eternity_bulwark", result_name="Eternity Bulwark", result_emoji="👑",
        ingredients=(("eternity_gem", 2), ("void_crystal", 3), ("heart_of_the_abyss", 1)),
        description="A shield forged from eternity, bound with abyssal power.",
    ),
    "darkite_warplate": CraftRecipe(
        result_key="darkite_warplate", result_name="Darkite Warplate", result_emoji="🌑",
        ingredients=(("darkite", 5), ("adamantium", 3), ("pearl_of_the_deep", 1)),
        description="Armor so dark it seems to consume light itself.",
    ),
    "void_reaper": CraftRecipe(
        result_key="void_reaper", result_name="Void Reaper", result_emoji="⚛️",
        ingredients=(("dark_matter", 3), ("noodle_gem", 1), ("davy_jones_chest", 1)),
        description="A terrifying scythe forged from Dark Matter and cursed treasure.",
    ),

    # ── Tier 6: Aetherdepths L1 + Moon ores ────────────────────
    "spiker": CraftRecipe(
        result_key="spiker", result_name="Spiker", result_emoji="📌",
        ingredients=(("hollow_stone", 3), ("aether_shard", 1), ("lunar_quartz", 2)),
        description="A superheated spike launcher forged from hollow stone and lunar quartz.",
    ),
    "plasma_pistol": CraftRecipe(
        result_key="plasma_pistol", result_name="Plasma Pistol", result_emoji="🔫",
        ingredients=(("primordial_dust", 3), ("aether_shard", 1), ("helium_3", 2)),
        description="A compact plasma sidearm powered by helium-3 cells.",
    ),
    "lunar_barrier": CraftRecipe(
        result_key="lunar_barrier", result_name="Lunar Barrier", result_emoji="🌙",
        ingredients=(("hollow_stone", 4), ("aether_shard", 1), ("selenite", 2)),
        description="An energy barrier that bends moonlight into a protective shell.",
    ),
    "lunar_exosuit": CraftRecipe(
        result_key="lunar_exosuit", result_name="Lunar Exosuit", result_emoji="🌑",
        ingredients=(("primordial_dust", 4), ("aether_shard", 1), ("moon_dust", 3)),
        description="A pressurized exosuit built for lunar combat operations.",
    ),

    # ── Tier 7: Aetherdepths L2 + Mars ores ──────────────────
    "plasma_rifle": CraftRecipe(
        result_key="plasma_rifle", result_name="Plasma Rifle", result_emoji="🔴",
        ingredients=(("forge_cinder", 3), ("infernal_core", 1), ("olympus_ruby", 2)),
        description="A fully automatic plasma weapon powered by Olympus ruby cores.",
    ),
    "plasma_repeater": CraftRecipe(
        result_key="plasma_repeater", result_name="Plasma Repeater", result_emoji="🟣",
        ingredients=(("molten_slag", 3), ("infernal_core", 1), ("martian_iron", 2)),
        description="A rapid-fire plasma weapon with Martian iron cooling vents.",
    ),
    "thermal_deflector": CraftRecipe(
        result_key="thermal_deflector", result_name="Thermal Deflector", result_emoji="🌋",
        ingredients=(("forge_cinder", 4), ("infernal_core", 1), ("phobos_shard", 2)),
        description="A heat-resistant energy shield forged from Phobos shards.",
    ),
    "crimson_exoplate": CraftRecipe(
        result_key="crimson_exoplate", result_name="Crimson Exoplate", result_emoji="🧲",
        ingredients=(("molten_slag", 4), ("infernal_core", 1), ("red_sand", 3)),
        description="Heavy crimson armor plating forged from Martian alloys.",
    ),

    # ── Tier 8: Aetherdepths L3 + Saturn ores ────────────────
    "needler": CraftRecipe(
        result_key="needler", result_name="Needler", result_emoji="💜",
        ingredients=(("crystal_marrow", 3), ("prismatic_lens", 1), ("saturn_sapphire", 2)),
        description="Fires crystalline needles that track targets and detonate.",
    ),
    "fuel_rod_cannon": CraftRecipe(
        result_key="fuel_rod_cannon", result_name="Fuel Rod Cannon", result_emoji="☢️",
        ingredients=(("voidcell", 3), ("prismatic_lens", 1), ("titan_ore", 2)),
        description="A heavy weapon that launches explosive fuel rod projectiles.",
    ),
    "particle_shield": CraftRecipe(
        result_key="particle_shield", result_name="Particle Shield", result_emoji="🪐",
        ingredients=(("crystal_marrow", 4), ("prismatic_lens", 1), ("ring_fragment", 2)),
        description="A shield woven from accelerated particles and ring debris.",
    ),
    "prismatic_suit": CraftRecipe(
        result_key="prismatic_suit", result_name="Prismatic Suit", result_emoji="💎",
        ingredients=(("voidcell", 4), ("prismatic_lens", 1), ("ammonia_ice", 3)),
        description="Light-bending armor that refracts incoming energy attacks.",
    ),

    # ── Tier 9: Aetherdepths L4 + Uranus ores ────────────────
    "energy_sword": CraftRecipe(
        result_key="energy_sword", result_name="Energy Sword", result_emoji="⚡",
        ingredients=(("temporal_fragment", 3), ("chrono_crystal", 1), ("uranian_diamond", 2)),
        description="A blade of pure plasma contained by magnetic fields.",
    ),
    "beam_rifle": CraftRecipe(
        result_key="beam_rifle", result_name="Beam Rifle", result_emoji="🔦",
        ingredients=(("warden_seal", 3), ("chrono_crystal", 1), ("miranda_stone", 2)),
        description="A long-range particle beam weapon of devastating precision.",
    ),
    "hardlight_shield": CraftRecipe(
        result_key="hardlight_shield", result_name="Hardlight Shield", result_emoji="🛡️",
        ingredients=(("temporal_fragment", 4), ("chrono_crystal", 1), ("methane_crystal", 2)),
        description="A shield of solidified light particles, nearly impervious.",
    ),
    "cryo_armor": CraftRecipe(
        result_key="cryo_armor", result_name="Cryo Armor", result_emoji="❄️",
        ingredients=(("warden_seal", 4), ("chrono_crystal", 1), ("ice_rock", 3)),
        description="Supercooled armor that flash-freezes projectiles on impact.",
    ),

    # ── Tier 10: Aetherdepths L5 + Pluto ores ────────────────
    "gravity_hammer": CraftRecipe(
        result_key="gravity_hammer", result_name="Gravity Hammer", result_emoji="🔨",
        ingredients=(("world_essence", 3), ("heart_of_the_world", 1), ("plutonium_core", 2)),
        description="A massive hammer that manipulates gravity to crush all opposition.",
    ),
    "prophets_bane": CraftRecipe(
        result_key="prophets_bane", result_name="Prophet's Bane", result_emoji="🗡️",
        ingredients=(("core_ember", 3), ("heart_of_the_world", 1), ("dark_matter", 2)),
        description="A legendary energy blade. Those it marks do not survive.",
    ),
    "void_shield": CraftRecipe(
        result_key="void_shield", result_name="Void Shield", result_emoji="🌑",
        ingredients=(("world_essence", 4), ("heart_of_the_world", 1), ("eternity_gem", 2)),
        description="A shield that opens micro-rifts in space to absorb attacks.",
    ),
    "siege_plate": CraftRecipe(
        result_key="siege_plate", result_name="Siege Plate", result_emoji="🪐",
        ingredients=(("core_ember", 4), ("heart_of_the_world", 1), ("frozen_nitrogen", 3)),
        description="The ultimate armor. Forged from planetary cores for total war.",
    ),

    # ── Stamina potions ───────────────────────────────────────
    "minor_stamina_brew": CraftRecipe(
        result_key="minor_stamina_brew", result_name="Minor Stamina Brew", result_emoji="🧪",
        ingredients=(("seaweed", 1), ("coal", 1)),
        description="A simple brew that restores 50 stamina.",
    ),
    "stamina_tonic": CraftRecipe(
        result_key="stamina_tonic", result_name="Stamina Tonic", result_emoji="🧴",
        ingredients=(("bioluminescent_jelly", 1),),
        description="A potent tonic that restores 80 stamina.",
    ),
    "void_energy_flask": CraftRecipe(
        result_key="void_energy_flask", result_name="Void Energy Flask", result_emoji="⚗️",
        ingredients=(("void_coral", 1), ("coral_golem", 1)),
        description="Pure concentrated void energy. Full stamina restoration.",
    ),
}

# ---------------------------------------------------------------------------
# T1 combat items available in shop (defined here for reference;
# actual ShopItem entries go in cogs/shop/constants.py)
# ---------------------------------------------------------------------------

STORE_COMBAT_ITEMS: Final[dict[str, int]] = {
    "wooden_sword": 200,
    "wooden_shield": 150,
    "leather_vest": 250,
    "iron_dagger": 175,
}

# ---------------------------------------------------------------------------
# Combat level unlock requirements
# ---------------------------------------------------------------------------

COMBAT_LEVEL_UNLOCK: Final[dict[int, dict]] = {
    1: {"required_combat_level": 0, "cost": 0},
    2: {"required_combat_level": 1, "cost": 500},
    3: {"required_combat_level": 2, "cost": 2000},
    4: {"required_combat_level": 3, "cost": 5000},
    5: {"required_combat_level": 4, "cost": 10000},
}

# How many wins at current level to gain a combat level
WINS_PER_COMBAT_LEVEL: Final[int] = 5

# ---------------------------------------------------------------------------
# Coop Fighting
# ---------------------------------------------------------------------------
COOP_MAX_PLAYERS: Final[int] = 4
COOP_JOIN_TIMEOUT: Final[int] = 60       # seconds to wait for joiners
COOP_ROUND_TIMEOUT: Final[int] = 120     # seconds per round before auto-resolve
COOP_REWARD_MULTIPLIER: Final[dict[int, float]] = {
    1: 1.0,    # solo (not used, just for reference)
    2: 0.70,   # 70% each
    3: 0.50,   # 50% each
    4: 0.40,   # 40% each
}
COOP_MOB_DAMAGE_FALLOFF: Final[list[float]] = [1.0, 0.50, 0.25, 0.125]

# ---------------------------------------------------------------------------
# Mob Drop Pools — loot tables for defeated mobs
# Each entry: (item_key, category, sell_value, drop_chance)
#   drop_chance is 0.0-1.0 probability; multiple items can drop per kill.
#   "equipment" category items use update_user_inventory instead of add_item.
# ---------------------------------------------------------------------------

# Type alias for readability
_Drop = tuple[str, str, int, float]  # (item_key, category, sell_value, chance)

# -- Dungeon mob drops by level -------------------------------------------

DUNGEON_DROPS: Final[dict[int, list[_Drop]]] = {
    1: [
        # Consumables
        ("raw_potato", "consumable", 10, 0.35),
        ("raw_potato", "consumable", 10, 0.20),
        ("health_potion", "consumable", 150, 0.15),
        ("stamina_elixir", "consumable", 25, 0.17),
        # Minerals — L1 resources at higher rates
        ("coal", "mineral", 50, 0.30),
        ("iron", "mineral", 100, 0.25),
        ("gold", "mineral", 200, 0.15),
        ("diamond", "mineral", 500, 0.08),
        # Rare effect item
        ("rune_fragment", "equipment", 0, 0.01),
    ],
    2: [
        ("health_potion", "consumable", 150, 0.20),
        ("golden_mushroom", "consumable", 75, 0.15),
        ("stamina_elixir", "consumable", 25, 0.15),
        ("bank_insurance", "consumable", 0, 0.04),
        # Minerals — L2 resources
        ("copper", "mineral", 75, 0.25),
        ("silver", "mineral", 150, 0.25),
        ("emerald", "mineral", 300, 0.15),
        ("ruby", "mineral", 750, 0.08),
        # Fish
        ("salmon", "fish", 800, 0.12),
        ("tuna", "fish", 1300, 0.08),
        # Rare effect item
        ("rune_fragment", "equipment", 0, 0.02),
    ],
    3: [
        ("health_potion", "consumable", 150, 0.25),
        ("golden_mushroom", "consumable", 75, 0.20),
        ("stamina_elixir", "consumable", 25, 0.15),
        # Minerals — L3 resources
        ("platinum", "mineral", 250, 0.22),
        ("sapphire", "mineral", 450, 0.15),
        ("amethyst", "mineral", 1125, 0.08),
        # Rare fish
        ("reef_shark", "fish", 1475, 0.10),
        ("giant_clam", "fish", 2750, 0.06),
        ("golden_seahorse", "fish", 18325, 0.03),
        # Stamina material
        ("seaweed", "fish", 0, 0.15),
        # Effect items
        ("bank_insurance", "consumable", 0, 0.04),
        ("rune_fragment", "equipment", 0, 0.02),
    ],
    4: [
        ("health_potion", "consumable", 150, 0.30),
        ("golden_mushroom", "consumable", 75, 0.25),
        ("stamina_elixir", "consumable", 25, 0.17),
        # Minerals — L4 resources
        ("mithril", "mineral", 400, 0.20),
        ("opal", "mineral", 700, 0.12),
        ("star_fragment", "mineral", 1750, 0.06),
        # Rare fish
        ("hammerhead_shark", "fish", 2075, 0.10),
        ("pirates_hoard", "fish", 11275, 0.05),
        ("phantom_captain", "fish", 26050, 0.03),
        # Stamina material
        ("bioluminescent_jelly", "fish", 0, 0.12),
        # Effect items
        ("bank_insurance", "consumable", 0, 0.05),
        ("fossilized_noodle", "equipment", 0, 0.02),
        ("star_magnet", "equipment", 0, 0.01),
    ],
    5: [
        ("health_potion", "consumable", 150, 0.35),
        ("golden_mushroom", "consumable", 75, 0.28),
        ("stamina_elixir", "consumable", 25, 0.20),
        # Minerals — L5 resources
        ("dragonstone", "mineral", 600, 0.18),
        ("void_crystal", "mineral", 1000, 0.10),
        ("noodle_gem", "mineral", 2500, 0.05),
        # Legendary fish
        ("megalodon_tooth", "fish", 6500, 0.08),
        ("trench_treasure", "fish", 18575, 0.05),
        ("leviathan_scale", "fish", 46400, 0.03),
        ("poseidons_eye", "fish", 92825, 0.02),
        # Space ores
        ("dark_matter", "ore", 3500, 0.06),
        ("plutonium_core", "ore", 5750, 0.04),
        ("void_coral", "fish", 0, 0.12),
        # Effect items
        ("bank_insurance", "consumable", 0, 0.06),
        ("fossilized_noodle", "equipment", 0, 0.02),
        ("star_magnet", "equipment", 0, 0.02),
        ("lucky_charm", "equipment", 0, 0.01),
    ],
}

# Boss bonus drops — rolled IN ADDITION to the level drops above
BOSS_BONUS_DROPS: Final[list[_Drop]] = [
    ("health_potion", "consumable", 50, 0.42),
    ("golden_mushroom", "consumable", 25, 0.38),
    ("stamina_elixir", "consumable", 25, 0.35),
    ("bank_insurance", "consumable", 0, 0.10),
    # Drop-only combat gear (very rare)
    ("golden_axe", "equipment", 0, 0.03),
    ("mithril_shield", "equipment", 0, 0.03),
    # Rare effect items
    ("star_magnet", "equipment", 0, 0.05),
    ("lucky_charm", "equipment", 0, 0.04),
    ("rune_fragment", "equipment", 0, 0.04),
    ("fossilized_noodle", "equipment", 0, 0.03),
    ("heart_of_leviathan", "equipment", 0, 0.01),
]

# -- Mining ambush drops (themed to underground resources) ----------------

MINING_AMBUSH_DROPS: Final[dict[int, list[_Drop]]] = {
    1: [
        ("stone", "mineral", 15, 0.30),
        ("coal", "mineral", 30, 0.25),
        ("iron", "mineral", 60, 0.10),
        ("raw_potato", "consumable", 6, 0.15),
        ("stamina_elixir", "consumable", 25, 0.15),
        ("health_potion", "consumable", 150, 0.05),
    ],
    2: [
        ("copper", "mineral", 45, 0.25),
        ("silver", "mineral", 90, 0.15),
        ("emerald", "mineral", 180, 0.05),
        ("raw_potato", "consumable", 6, 0.15),
        ("health_potion", "consumable", 150, 0.08),
        ("stamina_elixir", "consumable", 25, 0.15),
        ("golden_mushroom", "consumable", 75, 0.06),
    ],
    3: [
        ("tin", "mineral", 75, 0.20),
        ("platinum", "mineral", 150, 0.15),
        ("sapphire", "mineral", 270, 0.06),
        ("health_potion", "consumable", 150, 0.12),
        ("golden_mushroom", "consumable", 75, 0.08),
        ("stamina_elixir", "consumable", 25, 0.17),
        ("rune_fragment", "equipment", 0, 0.02),
    ],
    4: [
        ("titanium", "mineral", 120, 0.18),
        ("mithril", "mineral", 240, 0.12),
        ("opal", "mineral", 420, 0.05),
        ("star_fragment", "mineral", 1050, 0.02),
        ("health_potion", "consumable", 150, 0.15),
        ("stamina_elixir", "consumable", 25, 0.17),
        ("golden_mushroom", "consumable", 75, 0.07),
        ("rune_fragment", "equipment", 0, 0.02),
    ],
    5: [
        ("adamantium", "mineral", 180, 0.15),
        ("dragonstone", "mineral", 360, 0.10),
        ("void_crystal", "mineral", 600, 0.04),
        ("noodle_gem", "mineral", 1500, 0.01),
        ("health_potion", "consumable", 150, 0.18),
        ("golden_mushroom", "consumable", 75, 0.12),
        ("stamina_elixir", "consumable", 25, 0.20),
        ("bank_insurance", "consumable", 0, 0.04),
        ("fossilized_noodle", "equipment", 0, 0.01),
    ],
}

# -- Fishing ambush drops (themed to sea creatures/fish) ------------------

FISHING_AMBUSH_DROPS: Final[dict[int, list[_Drop]]] = {
    2: [
        ("trout", "fish", 60, 0.25),
        ("catfish", "fish", 75, 0.20),
        ("bass", "fish", 90, 0.12),
        ("seaweed", "fish", 50, 0.15),
        ("health_potion", "consumable", 150, 0.08),
        ("stamina_elixir", "consumable", 25, 0.15),
        ("golden_mushroom", "consumable", 75, 0.07),
    ],
    3: [
        ("clownfish", "fish", 50, 0.20),
        ("parrotfish", "fish", 90, 0.15),
        ("moray_eel", "fish", 110, 0.10),
        ("reef_shark", "fish", 350, 0.05),
        ("sea_sponge", "fish", 50, 0.15),
        ("golden_seahorse", "fish", 1800, 0.03),
        ("health_potion", "consumable", 150, 0.07),
        ("stamina_elixir", "consumable", 25, 0.15),
        ("bucktail_jig", "equipment", 0, 0.01),
    ],
    4: [
        ("barracuda", "fish", 250, 0.18),
        ("swordfish", "fish", 350, 0.12),
        ("hammerhead_shark", "fish", 500, 0.08),
        ("barnacle_cluster", "fish", 120, 0.15),
        ("health_potion", "consumable", 150, 0.12),
        ("phantom_captain", "fish", 2600, 0.03),
        ("stamina_elixir", "consumable", 25, 0.17),
        ("golden_mushroom", "consumable", 75, 0.09),
        ("bank_insurance", "consumable", 0, 0.04),
    ],
    5: [
        ("vampire_squid", "fish", 375, 0.15),
        ("dragonfish", "fish", 840, 0.10),
        ("megalodon_tooth", "fish", 1625, 0.06),
        ("void_coral", "fish", 200, 0.12),
        ("bioluminescent_jelly", "fish", 240, 0.10),
        ("leviathan_scale", "fish", 4640, 0.02),
        ("health_potion", "consumable", 150, 0.15),
        ("stamina_elixir", "consumable", 25, 0.20),
        ("golden_mushroom", "consumable", 75, 0.10),
        ("bucktail_jig", "equipment", 0, 0.02),
        ("star_magnet", "equipment", 0, 0.01),
    ],
}

# -- Space ambush drops (themed to space ores) ----------------------------

SPACE_AMBUSH_DROPS: Final[dict[int, list[_Drop]]] = {
    1: [
        ("moon_dust", "ore", 90, 0.30),
        ("helium_3", "ore", 180, 0.20),
        ("lunar_quartz", "ore", 360, 0.10),
        ("raw_potato", "consumable", 6, 0.15),
        ("stamina_elixir", "consumable", 25, 0.15),
        ("health_potion", "consumable", 150, 0.05),
    ],
    2: [
        ("red_sand", "ore", 130, 0.25),
        ("martian_iron", "ore", 260, 0.18),
        ("phobos_shard", "ore", 520, 0.08),
        ("health_potion", "consumable", 150, 0.10),
        ("stamina_elixir", "consumable", 25, 0.15),
        ("golden_mushroom", "consumable", 75, 0.06),
    ],
    3: [
        ("ring_fragment", "ore", 180, 0.22),
        ("titan_ore", "ore", 360, 0.15),
        ("ammonia_ice", "ore", 720, 0.08),
        ("saturn_sapphire", "ore", 1200, 0.04),
        ("health_potion", "consumable", 150, 0.12),
        ("stamina_elixir", "consumable", 25, 0.17),
        ("golden_mushroom", "consumable", 75, 0.07),
        ("rune_fragment", "equipment", 0, 0.02),
    ],
    4: [
        ("ice_rock", "ore", 250, 0.20),
        ("methane_crystal", "ore", 500, 0.14),
        ("miranda_stone", "ore", 1000, 0.08),
        ("uranian_diamond", "ore", 1660, 0.03),
        ("health_potion", "consumable", 150, 0.15),
        ("golden_mushroom", "consumable", 75, 0.10),
        ("stamina_elixir", "consumable", 25, 0.20),
        ("bank_insurance", "consumable", 0, 0.04),
        ("fossilized_noodle", "equipment", 0, 0.02),
    ],
    5: [
        ("frozen_nitrogen", "ore", 350, 0.18),
        ("charon_basalt", "ore", 700, 0.12),
        ("dark_matter", "ore", 1400, 0.06),
        ("plutonium_core", "ore", 2300, 0.03),
        ("eternity_gem", "ore", 5750, 0.01),
        ("health_potion", "consumable", 150, 0.18),
        ("golden_mushroom", "consumable", 75, 0.12),
        ("stamina_elixir", "consumable", 25, 0.23),
        ("bank_insurance", "consumable", 0, 0.05),
        ("star_magnet", "equipment", 0, 0.02),
        ("lucky_charm", "equipment", 0, 0.01),
    ],
}

# -- Alien ambush drops ---------------------------------------------------

ALIEN_AMBUSH_DROPS: Final[list[_Drop]] = [
    ("health_potion", "consumable", 50, 0.17),
    ("golden_mushroom", "consumable", 25, 0.12),
    ("star_fragment", "mineral", 350, 0.04),
    ("void_crystal", "mineral", 200, 0.03),
    ("dark_matter", "ore", 0, 0.03),
    ("star_magnet", "equipment", 0, 0.02),
]

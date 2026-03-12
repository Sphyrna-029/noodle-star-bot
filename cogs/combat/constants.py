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
HP_REGEN_PER_MINUTE: Final[int] = 1
STAMINA_REGEN_PER_MINUTE: Final[int] = 2
DAMAGE_FLOOR: Final[float] = 0.20  # minimum damage multiplier at 0 stamina

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
}

# ---------------------------------------------------------------------------
# Mobs — 24 total: 5 per level (L1-4), 4 at L5, 1 boss per level
# ---------------------------------------------------------------------------

MOBS: Final[dict[str, Mob]] = {
    # ── Level 1: Training Grounds ──────────────────────────────
    "slime": Mob(
        key="slime", name="Slime", emoji="🟢",
        level=1, hp=30, attack=5, defense=2, stamina=40,
        star_reward=15, is_boss=False,
    ),
    "rat": Mob(
        key="rat", name="Giant Rat", emoji="🐀",
        level=1, hp=35, attack=7, defense=3, stamina=50,
        star_reward=20, is_boss=False,
    ),
    "bat": Mob(
        key="bat", name="Cave Bat", emoji="🦇",
        level=1, hp=25, attack=8, defense=1, stamina=30,
        star_reward=18, is_boss=False,
    ),
    "mushroom_fiend": Mob(
        key="mushroom_fiend", name="Mushroom Fiend", emoji="🍄",
        level=1, hp=40, attack=6, defense=4, stamina=60,
        star_reward=25, is_boss=False,
    ),
    "goblin_chief": Mob(
        key="goblin_chief", name="Goblin Chief", emoji="👺",
        level=1, hp=80, attack=12, defense=6, stamina=80,
        star_reward=75, is_boss=True,
    ),

    # ── Level 2: Dark Corridors ────────────────────────────────
    "skeleton": Mob(
        key="skeleton", name="Skeleton Warrior", emoji="💀",
        level=2, hp=60, attack=14, defense=8, stamina=70,
        star_reward=45, is_boss=False,
    ),
    "spider": Mob(
        key="spider", name="Giant Spider", emoji="🕷️",
        level=2, hp=50, attack=16, defense=5, stamina=60,
        star_reward=40, is_boss=False,
    ),
    "zombie": Mob(
        key="zombie", name="Armored Zombie", emoji="🧟",
        level=2, hp=75, attack=12, defense=12, stamina=80,
        star_reward=50, is_boss=False,
    ),
    "ghost": Mob(
        key="ghost", name="Phantom", emoji="👻",
        level=2, hp=45, attack=18, defense=3, stamina=50,
        star_reward=55, is_boss=False,
    ),
    "troll_warlord": Mob(
        key="troll_warlord", name="Troll Warlord", emoji="🧌",
        level=2, hp=150, attack=22, defense=14, stamina=110,
        star_reward=150, is_boss=True,
    ),

    # ── Level 3: Cursed Halls ──────────────────────────────────
    "dark_knight": Mob(
        key="dark_knight", name="Dark Knight", emoji="🖤",
        level=3, hp=120, attack=24, defense=18, stamina=100,
        star_reward=100, is_boss=False,
    ),
    "fire_elemental": Mob(
        key="fire_elemental", name="Fire Elemental", emoji="🔥",
        level=3, hp=90, attack=30, defense=10, stamina=90,
        star_reward=110, is_boss=False,
    ),
    "gargoyle": Mob(
        key="gargoyle", name="Stone Gargoyle", emoji="🗿",
        level=3, hp=140, attack=20, defense=25, stamina=120,
        star_reward=120, is_boss=False,
    ),
    "wraith": Mob(
        key="wraith", name="Soul Wraith", emoji="😈",
        level=3, hp=100, attack=28, defense=12, stamina=80,
        star_reward=115, is_boss=False,
    ),
    "lich": Mob(
        key="lich", name="The Lich", emoji="☠️",
        level=3, hp=250, attack=32, defense=20, stamina=140,
        star_reward=300, is_boss=True,
    ),

    # ── Level 4: Infernal Depths ───────────────────────────────
    "demon": Mob(
        key="demon", name="Infernal Demon", emoji="👿",
        level=4, hp=200, attack=36, defense=22, stamina=130,
        star_reward=200, is_boss=False,
    ),
    "golem": Mob(
        key="golem", name="Iron Golem", emoji="🤖",
        level=4, hp=280, attack=28, defense=35, stamina=160,
        star_reward=220, is_boss=False,
    ),
    "hydra": Mob(
        key="hydra", name="Lesser Hydra", emoji="🐍",
        level=4, hp=220, attack=38, defense=18, stamina=120,
        star_reward=230, is_boss=False,
    ),
    "shadow_dragon": Mob(
        key="shadow_dragon", name="Shadow Drake", emoji="🐲",
        level=4, hp=240, attack=34, defense=28, stamina=140,
        star_reward=250, is_boss=False,
    ),
    "balrog": Mob(
        key="balrog", name="The Balrog", emoji="😤",
        level=4, hp=400, attack=42, defense=30, stamina=180,
        star_reward=500, is_boss=True,
    ),

    # ── Level 5: The Void ──────────────────────────────────────
    "void_sentinel": Mob(
        key="void_sentinel", name="Void Sentinel", emoji="🌌",
        level=5, hp=350, attack=45, defense=35, stamina=170,
        star_reward=400, is_boss=False,
    ),
    "cosmic_horror": Mob(
        key="cosmic_horror", name="Cosmic Horror", emoji="👁️",
        level=5, hp=300, attack=50, defense=25, stamina=150,
        star_reward=450, is_boss=False,
    ),
    "noodle_titan": Mob(
        key="noodle_titan", name="Noodle Titan", emoji="🍝",
        level=5, hp=400, attack=42, defense=40, stamina=180,
        star_reward=500, is_boss=False,
    ),
    "the_void_king": Mob(
        key="the_void_king", name="The Void King", emoji="💀",
        level=5, hp=600, attack=55, defense=40, stamina=200,
        star_reward=1000, is_boss=True,
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
    "wheat": 5,
    "carrot": 10,
    "corn": 15,
    "tomato": 20,
    "melon": 30,
}

FISH_HEAL_VALUES: Final[dict[str, int]] = {
    # Level 1 fish (keys match stored inventory format)
    "small_fish": 8,
    "crab": 10,
    "shrimp": 12,
    "salmon": 20,
    "tuna": 25,
    "lobster": 30,
    "octopus": 35,
    # Level 2 fish
    "trout": 12,
    "catfish": 15,
    "bass": 18,
    "river_salmon": 25,
    "sturgeon": 30,
    "snapping_turtle": 35,
    "giant_catfish": 40,
    # Level 3 fish
    "clownfish": 10,
    "parrotfish": 18,
    "sea_urchin": 20,
    "moray_eel": 22,
    "reef_shark": 35,
    # Level 4 fish
    "anglerfish": 15,
    "barracuda": 25,
    "swordfish": 30,
    # Level 5 fish
    "abyssal_crab": 20,
}

# ---------------------------------------------------------------------------
# Stamina recovery — fish and potions that restore stamina via !consume
# ---------------------------------------------------------------------------

STAMINA_RECOVERY: Final[dict[str, int]] = {
    # Farming consumables
    "raw_potato": 6,
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
    "minor_stamina_brew": 30,
    "stamina_tonic": 50,
    "void_energy_flask": 80,
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

    # ── Stamina potions ───────────────────────────────────────
    "minor_stamina_brew": CraftRecipe(
        result_key="minor_stamina_brew", result_name="Minor Stamina Brew", result_emoji="🧪",
        ingredients=(("seaweed", 3), ("coal", 1)),
        description="A simple brew that restores a little stamina.",
    ),
    "stamina_tonic": CraftRecipe(
        result_key="stamina_tonic", result_name="Stamina Tonic", result_emoji="🧴",
        ingredients=(("bioluminescent_jelly", 2), ("tin", 1), ("golden_seahorse", 1)),
        description="A potent tonic that restores a good deal of stamina.",
    ),
    "void_energy_flask": CraftRecipe(
        result_key="void_energy_flask", result_name="Void Energy Flask", result_emoji="⚗️",
        ingredients=(("void_coral", 3), ("dark_matter", 1), ("coral_golem", 1)),
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
        # Consumables — common
        ("raw_potato", "consumable", 2, 0.30),
        ("health_potion", "consumable", 50, 0.10),
        # Minerals — level 1 resources
        ("coal", "mineral", 10, 0.25),
        ("iron", "mineral", 20, 0.15),
        ("gold", "mineral", 40, 0.05),
    ],
    2: [
        ("raw_potato", "consumable", 2, 0.25),
        ("health_potion", "consumable", 50, 0.15),
        ("golden_mushroom", "consumable", 25, 0.10),
        # Minerals — level 2
        ("copper", "mineral", 15, 0.20),
        ("silver", "mineral", 30, 0.15),
        ("emerald", "mineral", 60, 0.06),
        # Fish consumables
        ("salmon", "fish", 20, 0.10),
    ],
    3: [
        ("health_potion", "consumable", 50, 0.20),
        ("golden_mushroom", "consumable", 25, 0.15),
        # Minerals — level 3
        ("tin", "mineral", 25, 0.18),
        ("platinum", "mineral", 50, 0.12),
        ("sapphire", "mineral", 90, 0.06),
        ("amethyst", "mineral", 225, 0.02),
        # Crafting fish
        ("golden_fish", "fish", 0, 0.04),
        ("river_dragon", "fish", 0, 0.03),
        # Stamina potion material
        ("seaweed", "fish", 10, 0.12),
    ],
    4: [
        ("health_potion", "consumable", 50, 0.25),
        ("golden_mushroom", "consumable", 25, 0.20),
        # Minerals — level 4
        ("titanium", "mineral", 40, 0.15),
        ("mithril", "mineral", 80, 0.10),
        ("opal", "mineral", 140, 0.06),
        ("star_fragment", "mineral", 350, 0.02),
        # Crafting fish
        ("neptunes_trident", "fish", 0, 0.03),
        ("phantom_captain", "fish", 0, 0.03),
        ("diamond_anchor", "fish", 0, 0.02),
        # Stamina materials
        ("bioluminescent_jelly", "fish", 24, 0.08),
    ],
    5: [
        ("health_potion", "consumable", 50, 0.30),
        ("golden_mushroom", "consumable", 25, 0.25),
        # Minerals — level 5
        ("adamantium", "mineral", 60, 0.12),
        ("dragonstone", "mineral", 120, 0.08),
        ("void_crystal", "mineral", 200, 0.04),
        ("noodle_gem", "mineral", 500, 0.01),
        # Crafting fish — endgame
        ("leviathan_scale", "fish", 0, 0.03),
        ("poseidons_eye", "fish", 0, 0.02),
        ("world_serpent_fang", "fish", 0, 0.02),
        ("heart_of_the_abyss", "fish", 0, 0.01),
        # Space ores
        ("dark_matter", "ore", 0, 0.03),
        ("void_coral", "fish", 20, 0.10),
    ],
}

# Boss bonus drops — rolled IN ADDITION to the level drops above
BOSS_BONUS_DROPS: Final[list[_Drop]] = [
    ("health_potion", "consumable", 50, 0.50),
    ("golden_mushroom", "consumable", 25, 0.40),
    # Drop-only combat gear (very rare)
    ("golden_axe", "equipment", 0, 0.03),
    ("mithril_shield", "equipment", 0, 0.03),
    # Rare effect items
    ("star_magnet", "equipment", 0, 0.05),
    ("lucky_charm", "equipment", 0, 0.04),
]

# -- Mining ambush drops (themed to underground resources) ----------------

MINING_AMBUSH_DROPS: Final[dict[int, list[_Drop]]] = {
    1: [
        ("stone", "mineral", 5, 0.30),
        ("coal", "mineral", 10, 0.25),
        ("iron", "mineral", 20, 0.10),
        ("raw_potato", "consumable", 2, 0.15),
    ],
    2: [
        ("copper", "mineral", 15, 0.25),
        ("silver", "mineral", 30, 0.15),
        ("emerald", "mineral", 60, 0.05),
        ("raw_potato", "consumable", 2, 0.15),
        ("health_potion", "consumable", 50, 0.08),
    ],
    3: [
        ("tin", "mineral", 25, 0.20),
        ("platinum", "mineral", 50, 0.15),
        ("sapphire", "mineral", 90, 0.06),
        ("health_potion", "consumable", 50, 0.12),
        ("golden_mushroom", "consumable", 25, 0.08),
    ],
    4: [
        ("titanium", "mineral", 40, 0.18),
        ("mithril", "mineral", 80, 0.12),
        ("opal", "mineral", 140, 0.05),
        ("star_fragment", "mineral", 350, 0.02),
        ("health_potion", "consumable", 50, 0.15),
    ],
    5: [
        ("adamantium", "mineral", 60, 0.15),
        ("dragonstone", "mineral", 120, 0.10),
        ("void_crystal", "mineral", 200, 0.04),
        ("noodle_gem", "mineral", 500, 0.01),
        ("health_potion", "consumable", 50, 0.18),
        ("golden_mushroom", "consumable", 25, 0.12),
    ],
}

# -- Fishing ambush drops (themed to sea creatures/fish) ------------------

FISHING_AMBUSH_DROPS: Final[dict[int, list[_Drop]]] = {
    2: [
        ("trout", "fish", 12, 0.25),
        ("catfish", "fish", 15, 0.20),
        ("bass", "fish", 18, 0.12),
        ("seaweed", "fish", 10, 0.15),
        ("health_potion", "consumable", 50, 0.08),
    ],
    3: [
        ("clownfish", "fish", 10, 0.20),
        ("parrotfish", "fish", 18, 0.15),
        ("moray_eel", "fish", 22, 0.10),
        ("reef_shark", "fish", 35, 0.05),
        ("sea_sponge", "fish", 10, 0.15),
        ("golden_seahorse", "fish", 0, 0.03),
    ],
    4: [
        ("barracuda", "fish", 25, 0.18),
        ("swordfish", "fish", 30, 0.12),
        ("hammerhead_shark", "fish", 0, 0.08),
        ("barnacle_cluster", "fish", 12, 0.15),
        ("health_potion", "consumable", 50, 0.12),
        ("phantom_captain", "fish", 0, 0.03),
    ],
    5: [
        ("vampire_squid", "fish", 0, 0.15),
        ("dragonfish", "fish", 0, 0.10),
        ("megalodon_tooth", "fish", 0, 0.06),
        ("void_coral", "fish", 20, 0.12),
        ("bioluminescent_jelly", "fish", 24, 0.10),
        ("leviathan_scale", "fish", 0, 0.02),
        ("health_potion", "consumable", 50, 0.15),
    ],
}

# -- Space ambush drops (themed to space ores) ----------------------------

SPACE_AMBUSH_DROPS: Final[dict[int, list[_Drop]]] = {
    1: [
        ("moon_dust", "ore", 0, 0.30),
        ("helium_3", "ore", 0, 0.20),
        ("lunar_quartz", "ore", 0, 0.10),
        ("raw_potato", "consumable", 2, 0.15),
    ],
    2: [
        ("red_sand", "ore", 0, 0.25),
        ("martian_iron", "ore", 0, 0.18),
        ("phobos_shard", "ore", 0, 0.08),
        ("health_potion", "consumable", 50, 0.10),
    ],
    3: [
        ("ring_fragment", "ore", 0, 0.22),
        ("titan_ore", "ore", 0, 0.15),
        ("ammonia_ice", "ore", 0, 0.08),
        ("saturn_sapphire", "ore", 0, 0.04),
        ("health_potion", "consumable", 50, 0.12),
    ],
    4: [
        ("ice_rock", "ore", 0, 0.20),
        ("methane_crystal", "ore", 0, 0.14),
        ("miranda_stone", "ore", 0, 0.08),
        ("uranian_diamond", "ore", 0, 0.03),
        ("health_potion", "consumable", 50, 0.15),
        ("golden_mushroom", "consumable", 25, 0.10),
    ],
    5: [
        ("frozen_nitrogen", "ore", 0, 0.18),
        ("charon_basalt", "ore", 0, 0.12),
        ("dark_matter", "ore", 0, 0.06),
        ("plutonium_core", "ore", 0, 0.03),
        ("eternity_gem", "ore", 0, 0.01),
        ("health_potion", "consumable", 50, 0.18),
        ("golden_mushroom", "consumable", 25, 0.12),
    ],
}

# -- Alien ambush drops ---------------------------------------------------

ALIEN_AMBUSH_DROPS: Final[list[_Drop]] = [
    ("health_potion", "consumable", 50, 0.35),
    ("golden_mushroom", "consumable", 25, 0.25),
    ("star_fragment", "mineral", 350, 0.08),
    ("void_crystal", "mineral", 200, 0.06),
    ("dark_matter", "ore", 0, 0.05),
    ("star_magnet", "equipment", 0, 0.04),
]

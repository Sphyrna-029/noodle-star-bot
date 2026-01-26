"""
Centralized configuration for Noodle Star Bot.
All magic numbers and settings extracted from the original bot.py.
"""

# Database
DATABASE_FILE = "noodle_stars.db"
TABLE_NAME = "noodle_stars"

# Bot
COMMAND_PREFIX = "!"

# Economy - Starting values
STARTING_STARS = 0
STARTING_BANK = 0

# Gambling - Gamble Command
GAMBLE_DICE_SIDES = 7  # Roll 1-7
GAMBLE_WIN_TARGET = 7  # Must roll 7 to win
# Multiplier weights: (multiplier, cumulative_threshold)
# 1% for 5x, 33% for 1.25x, 33% for 1.5x, 33% for 2x
GAMBLE_MULTIPLIERS = [
    (20, 0.01),    # 1% chance for ~20x
    (5, 0.34),     # next 33% for ~5x
    (7, 0.67),     # next 33% for ~6x
    (8, 1.0),      # last 33% for ~8x
]

# Gambling - Coinflip
COINFLIP_WIN_MULTIPLIER = 1.95
COINFLIP_MIN_BET = 20

# Gambling - Duel
DUEL_DICE_SIDES = 20  # Roll 1-20

# Mining - Cooldowns (in minutes)
MINING_BASE_COOLDOWN_MINUTES = 30
MINING_POTATO_COOLDOWN_MINUTES = 5
# Mushroom = instant (no cooldown)

# Banking - Cooldowns (in minutes)
BANKING_DEPOSIT_COOLDOWN_MINUTES = 60
BANKING_WITHDRAW_COOLDOWN_MINUTES = 60

# Mining - Disaster
MINING_DISASTER_CHANCE = 0.10  # 10%
MINING_COLLAPSE_LOSS_PERCENT = 0.50  # 50% of wallet
MINING_GOBLIN_LOSS_PERCENT = 0.75  # 75% of wallet

# Mining - Minerals (normal pickaxe)
MINERALS_NORMAL = [
    {"name": "Stone", "emoji": "🪨", "stars": 5, "weight": 40},
    {"name": "Coal", "emoji": "⚫", "stars": 10, "weight": 30},
    {"name": "Iron", "emoji": "⚙️", "stars": 20, "weight": 15},
    {"name": "Gold", "emoji": "🟡", "stars": 40, "weight": 10},
    {"name": "Diamond", "emoji": "💎", "stars": 100, "weight": 5},
]

# Mining - Minerals (gold pickaxe)
MINERALS_GOLD_PICKAXE = [
    {"name": "Stone", "emoji": "🪨", "stars": 5, "weight": 30},
    {"name": "Coal", "emoji": "⚫", "stars": 10, "weight": 25},
    {"name": "Iron", "emoji": "⚙️", "stars": 20, "weight": 20},
    {"name": "Gold", "emoji": "🟡", "stars": 40, "weight": 15},
    {"name": "Diamond", "emoji": "💎", "stars": 100, "weight": 10},
]

# Shop Items
# Format: item_key -> {price, db_column, consumable, emoji, display_name, description, aliases}
SHOP_ITEMS = {
    "gold_pickaxe": {
        "price": 500,
        "db_column": "gold_pickaxe",
        "consumable": False,
        "emoji": "⛏️",
        "display_name": "Gold Pickaxe",
        "description": "Permanently increases your mining luck! Find rare minerals more often.",
        "aliases": ["gold pickaxe", "pickaxe"],
    },
    "helmet": {
        "price": 50,
        "db_column": "helmet",
        "consumable": True,
        "emoji": "🪖",
        "display_name": "Mining Helmet",
        "description": "Protects you from one mine collapse. Single use.",
        "aliases": ["helmet", "mining helmet"],
    },
    "sword": {
        "price": 75,
        "db_column": "sword",
        "consumable": True,
        "emoji": "⚔️",
        "display_name": "Sword",
        "description": "Protects you from one goblin attack. Single use.",
        "aliases": ["sword"],
    },
    "raw_potato": {
        "price": 2,
        "db_column": "raw_potato",
        "consumable": True,
        "emoji": "🥔",
        "display_name": "Raw Potato",
        "description": "Mine early after 5 min instead of waiting 30 min. Single use. Use: `!mine potato`",
        "aliases": ["raw potato", "potato"],
    },
    "golden_mushroom": {
        "price": 25,
        "db_column": "golden_mushroom",
        "consumable": True,
        "emoji": "🍄",
        "display_name": "Golden Mushroom",
        "description": "Mine instantly with no cooldown! Single use. Use: `!mine mushroom`",
        "aliases": ["golden mushroom", "mushroom"],
    },
    # Fishing Bait
    "bait_worm": {
        "price": 33,
        "db_column": "bait_worm",
        "consumable": True,
        "emoji": "🪱",
        "display_name": "Worm Bait",
        "description": "Basic bait. Fast bite (15-60s), large pull window (60s). Consistent returns. Use: `!use bait worm`",
        "aliases": ["worm", "worm bait", "bait worm"],
    },
    "bait_herring": {
        "price": 79,
        "db_column": "bait_herring",
        "consumable": True,
        "emoji": "🐟",
        "display_name": "Herring Bait",
        "description": "Medium bait. Better fish, longer bite (90-180s), tighter window (35s). Use: `!use bait herring`",
        "aliases": ["herring", "herring bait", "bait herring"],
    },
    "bait_sturgeon": {
        "price": 110,
        "db_column": "bait_sturgeon",
        "consumable": True,
        "emoji": "🐋",
        "display_name": "Sturgeon Bait",
        "description": "Premium bait. Best fish odds, long bite (5-8min), tiny window (20s). High risk/reward! Use: `!use bait sturgeon`",
        "aliases": ["sturgeon", "sturgeon bait", "bait sturgeon"],
    },
}

# =============================================================================
# FISHING CONFIGURATION
# =============================================================================

# Fishing cooldown after each attempt (success or fail) in seconds
FISHING_COOLDOWN_SECONDS = 120  # 2 minutes

# Bait tiers configuration
# bite_wait: (min_seconds, max_seconds) - time until fish bites
# pull_window: seconds to react after bite
# rare_boost: multiplier for rare/legendary odds (1.0 = base)
FISHING_BAIT_TIERS = {
    "worm": {
        "emoji": "🪱",
        "display_name": "Worm",
        "bite_wait": (15, 60),
        "pull_window": 60,
        "rare_boost": 0.4924,
    },
    "herring": {
        "emoji": "🐟",
        "display_name": "Herring",
        "bite_wait": (90, 180),
        "pull_window": 35,
        "rare_boost": 2.009,
    },
    "sturgeon": {
        "emoji": "🐋",
        "display_name": "Sturgeon",
        "bite_wait": (300, 480),
        "pull_window": 20,
        "rare_boost": 9.964,
    },
}

# Catch table with base probabilities (before bait rare_boost)
# Probabilities are weights, will be normalized
# "junk" items have 0 stars and act as item sinks
FISHING_CATCH_TABLE = {
    "common": {
        "weight": 70,  # Base 70% chance
        "catches": [
            {"name": "Old Boot", "emoji": "🥾", "stars": 0, "weight": 15},
            {"name": "Seaweed", "emoji": "🌿", "stars": 0, "weight": 15},
            {"name": "Tin Can", "emoji": "🥫", "stars": 0, "weight": 10},
            {"name": "Small Fish", "emoji": "🐟", "stars": 8, "weight": 25},
            {"name": "Crab", "emoji": "🦀", "stars": 12, "weight": 20},
            {"name": "Shrimp", "emoji": "🦐", "stars": 15, "weight": 15},
        ],
    },
    "rare": {
        "weight": 25,  # Base 25% chance
        "catches": [
            {"name": "Salmon", "emoji": "🐠", "stars": 40, "weight": 30},
            {"name": "Tuna", "emoji": "🐟", "stars": 65, "weight": 25},
            {"name": "Lobster", "emoji": "🦞", "stars": 90, "weight": 20},
            {"name": "Octopus", "emoji": "🐙", "stars": 130, "weight": 15},
            {"name": "Treasure Chest", "emoji": "📦", "stars": 200, "weight": 10},
        ],
    },
    "legendary": {
        "weight": 5,  # Base 5% chance
        "catches": [
            {"name": "Golden Fish", "emoji": "✨", "stars": 500, "weight": 40},
            {"name": "Giant Squid", "emoji": "🦑", "stars": 800, "weight": 30},
            {"name": "Ancient Artifact", "emoji": "🏺", "stars": 1200, "weight": 20},
            {"name": "Mermaid's Pearl", "emoji": "🔮", "stars": 2000, "weight": 10},
        ],
    },
}


def get_item_by_alias(alias: str) -> dict | None:
    """Look up a shop item by any of its aliases."""
    alias_lower = alias.lower().strip()
    for item_key, item_data in SHOP_ITEMS.items():
        if alias_lower in item_data["aliases"]:
            return {"key": item_key, **item_data}
    return None

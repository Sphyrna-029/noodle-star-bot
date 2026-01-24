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
    (5.0, 0.01),    # 1% chance for 5x
    (1.25, 0.34),   # 33% chance for 1.25x
    (1.5, 0.67),    # 33% chance for 1.5x
    (2.0, 1.0),     # 33% chance for 2x
]

# Gambling - Coinflip
COINFLIP_WIN_MULTIPLIER = 1.9

# Gambling - Duel
DUEL_DICE_SIDES = 20  # Roll 1-20

# Mining - Cooldowns (in minutes)
MINING_BASE_COOLDOWN_MINUTES = 30
MINING_POTATO_COOLDOWN_MINUTES = 5
# Mushroom = instant (no cooldown)

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
        "price": 100,
        "db_column": "helmet",
        "consumable": True,
        "emoji": "🪖",
        "display_name": "Mining Helmet",
        "description": "Protects you from one mine collapse. Single use.",
        "aliases": ["helmet", "mining helmet"],
    },
    "sword": {
        "price": 300,
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
        "description": "Reduces mining cooldown to 5 minutes. Single use. Use: `!mine potato`",
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
}


def get_item_by_alias(alias: str) -> dict | None:
    """Look up a shop item by any of its aliases."""
    alias_lower = alias.lower().strip()
    for item_key, item_data in SHOP_ITEMS.items():
        if alias_lower in item_data["aliases"]:
            return {"key": item_key, **item_data}
    return None

from typing import Final

__all__ = [
    "STARTING_STARS",
    "STARTING_BANK",
    "BANKING_DEPOSIT_COOLDOWN_MINUTES",
    "BANKING_WITHDRAW_COOLDOWN_MINUTES",
    "ACHIEVEMENT_DEFS",
]

STARTING_STARS: Final[int] = 0
STARTING_BANK: Final[int] = 0

BANKING_DEPOSIT_COOLDOWN_MINUTES = 60
BANKING_WITHDRAW_COOLDOWN_MINUTES = 15

ACHIEVEMENT_DEFS = (
    {
        "key": "first_star",
        "name": "First Star",
        "emoji": "⭐",
        "description": "Own at least 1 total star.",
    },
    {
        "key": "baby_saver",
        "name": "Baby Saver",
        "emoji": "🏦",
        "description": "Keep at least 1000 stars in the bank.",
    },
    {
        "key": "small_saver",
        "name": "Small Saver",
        "emoji": "🏦",
        "description": "Keep at least 5000 stars in the bank.",
    },
    {
        "key": "medium_saver",
        "name": "Medium Saver",
        "emoji": "🏦",
        "description": "Keep at least 10000 stars in the bank.",
    },
    {
        "key": "miner_upgrade",
        "name": "Miner Upgrade",
        "emoji": "⛏️",
        "description": "Reach mine level 5.",
    },
    {
        "key": "prepared_miner",
        "name": "Prepared Miner",
        "emoji": "🛡️",
        "description": "Own both a helmet and a sword.",
    },
    {
        "key": "tool_owner",
        "name": "Tool Owner",
        "emoji": "✨",
        "description": "Own either a Gold Pickaxe or Telescope.",
    },
    {
        "key": "space_ready",
        "name": "Space Ready",
        "emoji": "🚀",
        "description": "Own a Rocket Ship.",
    },
    {
        "key": "mine_100",
        "name": "Centurion Miner",
        "emoji": "💎",
        "description": "Mine 100 times total.",
        "progress_key": "mine_runs",
        "target": 100,
    },
    {
        "key": "mine_1000",
        "name": "Mining Legend",
        "emoji": "👑",
        "description": "Mine 1000 times total.",
        "progress_key": "mine_runs",
        "target": 1000,
    },
    {
        "key": "fish_10",
        "name": "Lake Regular",
        "emoji": "🐟",
        "description": "Catch 10 fish total.",
        "progress_key": "fish_catches",
        "target": 10,
    },
    {
        "key": "fish_100",
        "name": "Ocean Veteran",
        "emoji": "🐠",
        "description": "Catch 100 fish total.",
        "progress_key": "fish_catches",
        "target": 100,
    },
    {
        "key": "gambling_lost_1000",
        "name": "House Favorite",
        "emoji": "🎲",
        "description": "Lose 1000 stars total from gambling.",
        "progress_key": "gambling_stars_lost",
        "target": 1000,
    },
)

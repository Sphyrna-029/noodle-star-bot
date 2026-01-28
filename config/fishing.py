from datetime import timedelta
from typing import Final

from .models import BaitTier, Catch, CatchBucket

__all__ = ["FISHING_COOLDOWN", "FISHING_BAIT_TIERS", "FISHING_CATCH_TABLE"]

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

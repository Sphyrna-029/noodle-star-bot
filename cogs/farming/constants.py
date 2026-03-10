"""Farming system constants.

Economics Summary (per plot):
    Wheat:    25⭐/hr (1hr growth)   - Best for active players checking hourly
    Carrot:   30⭐/hr (2hr growth)   - Good for checking every few hours
    Corn:     35⭐/hr (4hr growth)   - Good for checking 2-3x per day
    Tomato:   40⭐/hr (8hr growth)   - Overnight/workday crop
    Melon:    45⭐/hr (16hr growth)  - Maximum convenience, check once daily

Design Philosophy:
    - 1 plot ≈ slightly below mining L1 income (passive vs active trade-off)
    - Farming is always ~7.5% worse than equivalent mining level
    - Zero risk, zero effort = lower reward than active risky mining
    - Leaves room for v2 bonuses (fertilizer, water, etc.)
"""

from typing import Final

from config.models import Crop

__all__ = [
    "CROPS",
    "PLOT_COSTS",
    "MAX_PLOTS",
    "MAX_FARM_LEVEL",
    "FARM_LEVEL_UPGRADE_COSTS",
    "QUALITY_MULTIPLIERS",
    "QUALITY_WEIGHTS_BY_LEVEL",
    "SOIL_MAX_CONDITION",
    "SOIL_DRAIN_BY_CROP",
    "SOIL_MULTIPLIER_BY_THRESHOLD",
    "SOIL_BAD_WEIGHT_BY_THRESHOLD",
    "TEND_ITEM_SOIL_RESTORE",
    "MAX_PRESERVER_LEVEL",
    "PRESERVER_UPGRADE_COSTS",
    "PRESERVER_BONUS_BY_LEVEL",
    "PRESERVER_PROCESSING_HOURS_BY_LEVEL",
    "MAX_GROWBOT_LEVEL",
    "GROWBOT_PLOT_CAPACITY_BY_LEVEL",
    "get_crop_by_name",
]

# ---------------------------------------------------------------------------
# Crop Definitions
# ---------------------------------------------------------------------------
# Net profit per crop (sell_price - seed_cost):
#   Wheat:  +25⭐ in 1hr  = 25⭐/hr
#   Carrot: +60⭐ in 2hr  = 30⭐/hr
#   Corn:   +140⭐ in 4hr = 35⭐/hr
#   Tomato: +320⭐ in 8hr = 40⭐/hr
#   Melon:  +720⭐ in 16hr = 45⭐/hr

CROPS: Final[dict[str, Crop]] = {
    "wheat": Crop(
        name="Wheat",
        emoji="🌾",
        seed_cost=15,
        sell_price=40,
        growth_hours=1,
    ),
    "carrot": Crop(
        name="Carrot",
        emoji="🥕",
        seed_cost=30,
        sell_price=90,
        growth_hours=2,
    ),
    "corn": Crop(
        name="Corn",
        emoji="🌽",
        seed_cost=60,
        sell_price=200,
        growth_hours=4,
    ),
    "tomato": Crop(
        name="Tomato",
        emoji="🍅",
        seed_cost=120,
        sell_price=440,
        growth_hours=8,
    ),
    "melon": Crop(
        name="Melon",
        emoji="🍉",
        seed_cost=240,
        sell_price=960,
        growth_hours=16,
    ),
    "mushroom": Crop(
        name="Mushroom",
        emoji="🍄",
        seed_cost=300,
        sell_price=0,
        growth_hours=24,
        golden_mushroom_yield=5,
    ),
}

# ---------------------------------------------------------------------------
# Plot Costs (scaling)
# ---------------------------------------------------------------------------
# Total investment for 6 plots: 3,300⭐

PLOT_COSTS: Final[dict[int, int]] = {
    1: 300,
    2: 400,
    3: 500,
    4: 600,
    5: 700,
    6: 800,
}

MAX_PLOTS: Final[int] = 6

# ---------------------------------------------------------------------------
# Farm Progression
# ---------------------------------------------------------------------------
# Costs are keyed by target level (e.g. upgrading 1->2 uses key 2).
MAX_FARM_LEVEL: Final[int] = 5
FARM_LEVEL_UPGRADE_COSTS: Final[dict[int, int]] = {
    2: 1200,
    3: 2800,
    4: 5200,
    5: 9000,
}

# Harvest quality bonuses.
QUALITY_MULTIPLIERS: Final[dict[str, float]] = {
    "bad": 0.8,
    "normal": 1.0,
    "great": 1.2,
}

# Weighted quality rolls by farm level.
# (quality, weight)
QUALITY_WEIGHTS_BY_LEVEL: Final[dict[int, tuple[tuple[str, int], ...]]] = {
    1: (("bad", 20), ("normal", 60), ("great", 20)),
    2: (("bad", 16), ("normal", 60), ("great", 24)),
    3: (("bad", 12), ("normal", 58), ("great", 30)),
    4: (("bad", 8), ("normal", 56), ("great", 36)),
    5: (("bad", 5), ("normal", 50), ("great", 45)),
}

# ---------------------------------------------------------------------------
# Soil fatigue and tending
# ---------------------------------------------------------------------------
SOIL_MAX_CONDITION: Final[int] = 100

# Base soil drain applied on harvest by crop type.
SOIL_DRAIN_BY_CROP: Final[dict[str, int]] = {
    "wheat": 4,
    "carrot": 10,
    "corn": 14,
    "tomato": 15,
    "melon": 20,
    "mushroom": 30,
}

# Soil condition thresholds and associated payout multipliers.
SOIL_MULTIPLIER_BY_THRESHOLD: Final[tuple[tuple[int, float], ...]] = (
    (75, 1.00),
    (50, 0.70),
    (25, 0.40),
    (0, 0.15),
)

# Additional bad-quality weight based on soil condition.
SOIL_BAD_WEIGHT_BY_THRESHOLD: Final[tuple[tuple[int, int], ...]] = (
    (75, 0),
    (50, 25),
    (25, 40),
    (0, 70),
)

TEND_ITEM_SOIL_RESTORE: Final[dict[str, int]] = {
    "fertilizer": 30,
    "water": 10,
}

# ---------------------------------------------------------------------------
# Preserver (single processing machine)
# ---------------------------------------------------------------------------
MAX_PRESERVER_LEVEL: Final[int] = 5
PRESERVER_UPGRADE_COSTS: Final[dict[int, int]] = {
    1: 15000,
    2: 24000,
    3: 36000,
    4: 52000,
    5: 72000,
}

# Bonus stars queued for processing from melon harvests by preserver level.
PRESERVER_BONUS_BY_LEVEL: Final[dict[int, float]] = {
    1: 0.20,
    2: 0.35,
    3: 0.50,
    4: 0.70,
    5: 1.00,
}

PRESERVER_PROCESSING_HOURS_BY_LEVEL: Final[dict[int, int]] = {
    1: 6,
    2: 5,
    3: 4,
    4: 3,
    5: 1,
}

# ---------------------------------------------------------------------------
# GrowBot (farm automation helper)
# ---------------------------------------------------------------------------
# Capacity is keyed by GrowBot level. Level 1 already supports all current plots.
# Keeping this map now allows future upgrades without command rewrites.
MAX_GROWBOT_LEVEL: Final[int] = 5
GROWBOT_PLOT_CAPACITY_BY_LEVEL: Final[dict[int, int]] = {
    1: MAX_PLOTS,
}


def get_crop_by_name(name: str) -> Crop | None:
    """Get a crop by its name (case-insensitive)."""
    return CROPS.get(name.lower())

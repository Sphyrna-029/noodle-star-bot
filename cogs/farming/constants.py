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


def get_crop_by_name(name: str) -> Crop | None:
    """Get a crop by its name (case-insensitive)."""
    return CROPS.get(name.lower())

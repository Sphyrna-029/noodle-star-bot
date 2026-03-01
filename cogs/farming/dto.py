from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class PlotStatus:
    """Status of a single farm plot."""

    plot_number: int
    is_empty: bool = True
    crop_name: str = ""
    crop_emoji: str = ""
    planted_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    is_ready: bool = False
    time_remaining_seconds: int = 0


@dataclass(slots=True)
class FarmStatus:
    """Overall farm status for a user."""

    total_plots: int
    plots: list[PlotStatus] = field(default_factory=list)
    next_plot_cost: Optional[int] = None
    can_buy_more: bool = True
    stars: int = 0  # User's current star balance
    farm_level: int = 1
    next_farm_level_cost: Optional[int] = None


@dataclass(slots=True)
class BuyPlotResult:
    """Result of buying a farm plot."""

    success: bool
    message: str
    plot_number: int = 0
    cost: int = 0
    new_balance: int = 0


@dataclass(slots=True)
class PlantResult:
    """Result of planting a crop."""

    success: bool
    message: str
    plot_number: int = 0
    crop_name: str = ""
    crop_emoji: str = ""
    seed_cost: int = 0
    ready_at: Optional[datetime] = None
    new_balance: int = 0


@dataclass(slots=True)
class HarvestResult:
    """Result of harvesting crops."""

    success: bool
    message: str
    harvested: list[tuple[int, str, str, int]] = field(default_factory=list)  # (plot, name, emoji, stars)
    total_stars: int = 0
    new_balance: int = 0
    mushrooms_earned: int = 0
    quality_rolls: list[tuple[int, str, float, float]] = field(default_factory=list)  # (plot, quality, quality_mult, weather_mult)
    weather_blessed: list[tuple[str, str, int, int]] = field(default_factory=list)  # (name, emoji, base_price, actual_price) for bonus crops


@dataclass(slots=True)
class UpgradeFarmLevelResult:
    """Result of upgrading farm level."""

    success: bool
    message: str
    old_level: int = 1
    new_level: int = 1
    cost: int = 0
    new_balance: int = 0


@dataclass(slots=True)
class CropsInfo:
    """Information about available crops."""

    crops: list[tuple[str, str, int, int, int, int]]  # (name, emoji, seed_cost, sell_price, profit, growth_hours)

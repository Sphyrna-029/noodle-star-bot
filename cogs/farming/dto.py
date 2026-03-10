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
    soil_condition: int = 100
    same_crop_streak: int = 0


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
    preserver_owned: bool = False
    preserver_level: int = 0
    preserver_next_cost: Optional[int] = None
    preserver_pending_stars: int = 0
    preserver_ready_in_seconds: int = 0
    growbot_owned: bool = False
    growbot_level: int = 0


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
    preserver_bonus_queued: int = 0
    preserver_ready_in_seconds: int = 0
    items_added: int = 0          # Number of crop items added to inventory
    bag_count: int = 0            # Current inventory count after harvest
    bag_capacity: int = 50        # Max inventory capacity
    inventory_full_skipped: int = 0  # Number of crops skipped due to full inventory


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
class TendPlotResult:
    """Result of tending a farm plot with an item."""

    success: bool
    message: str
    plot_number: int = 0
    item_used: str = ""
    soil_before: int = 0
    soil_after: int = 0
    remaining_items: int = 0


@dataclass(slots=True)
class UpgradePreserverResult:
    """Result of upgrading the Preserver machine."""

    success: bool
    message: str
    old_level: int = 0
    new_level: int = 0
    cost: int = 0
    new_balance: int = 0


@dataclass(slots=True)
class CollectPreserverResult:
    """Result of collecting processed Preserver stars."""

    success: bool
    message: str
    collected_stars: int = 0
    new_balance: int = 0
    ready_in_seconds: int = 0


@dataclass(slots=True)
class StartPreserverResult:
    """Result of starting a Preserver processing batch."""

    success: bool
    message: str
    preserved: list[tuple[int, str, str, int]] = field(default_factory=list)  # (plot, name, emoji, queued_stars)
    total_queued: int = 0
    pending_stars: int = 0
    ready_in_seconds: int = 0


@dataclass(slots=True)
class CropsInfo:
    """Information about available crops."""

    crops: list[tuple[str, str, int, int, int, int]]  # (name, emoji, seed_cost, sell_price, profit, growth_hours)


@dataclass(slots=True)
class GrowBotTendResult:
    """Result of using GrowBot to tend multiple plots."""

    success: bool
    message: str
    item_used: str = ""
    tended_plots: list[tuple[int, int, int]] = field(default_factory=list)  # (plot, before, after)
    skipped_full_soil: list[int] = field(default_factory=list)
    remaining_items: int = 0


@dataclass(slots=True)
class GrowBotPlantResult:
    """Result of using GrowBot to plant across multiple plots."""

    success: bool
    message: str
    crop_name: str = ""
    crop_emoji: str = ""
    planted_plots: list[int] = field(default_factory=list)
    skipped_occupied: list[int] = field(default_factory=list)
    total_seed_cost: int = 0
    new_balance: int = 0

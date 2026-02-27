"""Farming use-cases for the farming minigame.

Economics Summary (per plot):
    Wheat:    25⭐/hr (1hr growth)   - Best for active players checking hourly
    Carrot:   30⭐/hr (2hr growth)   - Good for checking every few hours
    Corn:     35⭐/hr (4hr growth)   - Good for checking 2-3x per day
    Tomato:   40⭐/hr (8hr growth)   - Overnight/workday crop
    Melon:    45⭐/hr (16hr growth)  - Maximum convenience, check once daily

Design Philosophy:
    - Farming is passive, zero-risk income
    - 1 plot ≈ slightly below mining L1 income
    - Always ~7.5% worse than equivalent mining level
    - Leaves room for v2 bonuses (fertilizer, water, etc.)
"""

from datetime import datetime, timedelta
from typing import Optional

from cogs.farming.constants import CROPS, MAX_PLOTS, PLOT_COSTS, get_crop_by_name
from cogs.farming.dto import (
    BuyPlotResult,
    CropsInfo,
    FarmStatus,
    HarvestResult,
    PlantResult,
    PlotStatus,
)
from database.repository import UserRepository


class FarmingUseCases:
    """Handles all farming-related business logic."""

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repo = repository or UserRepository()

    def get_farm_status(self, user_id: int, username: str) -> FarmStatus:
        """Get the current status of a user's farm."""
        # Ensure user exists
        self.repo.get_user(user_id, username)

        total_plots = self.repo.get_farm_plots(user_id)
        planted_crops = self.repo.get_planted_crops(user_id)
        now = datetime.now()

        # Build plot statuses
        plots = []
        planted_by_plot = {crop.plot_number: crop for crop in planted_crops}

        for plot_num in range(1, total_plots + 1):
            crop_data = planted_by_plot.get(plot_num)

            if crop_data is None:
                # Empty plot
                plots.append(PlotStatus(plot_number=plot_num, is_empty=True))
            else:
                # Get crop info
                crop = get_crop_by_name(crop_data.crop_type)
                is_ready = now >= crop_data.ready_at
                time_remaining = 0
                if not is_ready:
                    time_remaining = int((crop_data.ready_at - now).total_seconds())

                plots.append(
                    PlotStatus(
                        plot_number=plot_num,
                        is_empty=False,
                        crop_name=crop.name if crop else crop_data.crop_type,
                        crop_emoji=crop.emoji if crop else "🌱",
                        planted_at=crop_data.planted_at,
                        ready_at=crop_data.ready_at,
                        is_ready=is_ready,
                        time_remaining_seconds=time_remaining,
                    )
                )

        # Determine next plot cost
        next_plot_num = total_plots + 1
        next_plot_cost = PLOT_COSTS.get(next_plot_num)
        can_buy_more = next_plot_num <= MAX_PLOTS
        
        # Get user's star balance
        stars = self.repo.get_user_stars(user_id, username)

        return FarmStatus(
            total_plots=total_plots,
            plots=plots,
            next_plot_cost=next_plot_cost,
            can_buy_more=can_buy_more,
            stars=stars,
        )

    def buy_plot(self, user_id: int, username: str, plot_number: int = 0) -> BuyPlotResult:
        """Buy a new farm plot.
        
        Args:
            user_id: The user's Discord ID
            username: The user's Discord username
            plot_number: Specific plot to buy (1-6). If 0, buys the next available plot.
        """
        # Ensure user exists
        self.repo.get_user(user_id, username)

        current_plots = self.repo.get_farm_plots(user_id)
        
        # Determine which plot to buy
        if plot_number == 0:
            # Buy next available plot (old behavior for backward compatibility)
            target_plot_num = current_plots + 1
        else:
            # Buy specific plot
            target_plot_num = plot_number
            
            # Validate they're buying in order
            if target_plot_num != current_plots + 1:
                if target_plot_num <= current_plots:
                    return BuyPlotResult(
                        success=False,
                        message=f"You already own plot #{target_plot_num}!",
                    )
                else:
                    return BuyPlotResult(
                        success=False,
                        message=f"You must buy plots in order! Buy plot #{current_plots + 1} first.",
                    )

        # Check if can buy more
        if target_plot_num > MAX_PLOTS:
            return BuyPlotResult(
                success=False,
                message=f"You already own the maximum of {MAX_PLOTS} plots!",
            )

        cost = PLOT_COSTS.get(target_plot_num)
        if cost is None:
            return BuyPlotResult(
                success=False,
                message="Invalid plot number.",
            )

        # Check if user has enough stars
        balance = self.repo.get_user_stars(user_id, username)
        if balance < cost:
            return BuyPlotResult(
                success=False,
                message=f"You need **{cost}** stars to buy plot #{target_plot_num}, but you only have **{balance}** stars!",
            )

        # Deduct stars and add plot
        new_balance = balance - cost
        self.repo.update_user_stars(user_id, username, new_balance)
        self.repo.set_farm_plots(user_id, target_plot_num)

        return BuyPlotResult(
            success=True,
            message=f"You bought plot #{target_plot_num} for **{cost}** stars!",
            plot_number=target_plot_num,
            cost=cost,
            new_balance=new_balance,
        )

    def plant_crop(
        self, user_id: int, username: str, crop_name: str, plot_number: int
    ) -> PlantResult:
        """Plant a crop in a specific plot."""
        # Ensure user exists
        self.repo.get_user(user_id, username)

        total_plots = self.repo.get_farm_plots(user_id)

        # Validate plot number
        if plot_number < 1 or plot_number > total_plots:
            if total_plots == 0:
                return PlantResult(
                    success=False,
                    message="You don't own any plots yet! Use `!buyplot` to buy your first plot.",
                )
            return PlantResult(
                success=False,
                message=f"Invalid plot number! You own plots 1-{total_plots}.",
            )

        # Check if plot is already occupied
        existing_crop = self.repo.get_planted_crop(user_id, plot_number)
        if existing_crop is not None:
            crop_info = get_crop_by_name(existing_crop.crop_type)
            emoji = crop_info.emoji if crop_info else "🌱"
            name = crop_info.name if crop_info else existing_crop.crop_type
            return PlantResult(
                success=False,
                message=f"Plot #{plot_number} already has {emoji} **{name}** planted! Harvest it first.",
            )

        # Validate crop type
        crop = get_crop_by_name(crop_name)
        if crop is None:
            available = ", ".join(CROPS.keys())
            return PlantResult(
                success=False,
                message=f"Unknown crop `{crop_name}`! Available crops: {available}",
            )

        # Check if user has enough stars for seeds
        balance = self.repo.get_user_stars(user_id, username)
        if balance < crop.seed_cost:
            return PlantResult(
                success=False,
                message=f"You need **{crop.seed_cost}** stars for {crop.emoji} {crop.name} seeds, but you only have **{balance}** stars!",
            )

        # Deduct seed cost and plant
        new_balance = balance - crop.seed_cost
        self.repo.update_user_stars(user_id, username, new_balance)

        now = datetime.now()
        ready_at = now + timedelta(hours=crop.growth_hours)

        self.repo.plant_crop(user_id, plot_number, crop_name.lower(), now, ready_at)

        return PlantResult(
            success=True,
            message=f"Planted {crop.emoji} **{crop.name}** in plot #{plot_number}!",
            plot_number=plot_number,
            crop_name=crop.name,
            crop_emoji=crop.emoji,
            seed_cost=crop.seed_cost,
            ready_at=ready_at,
            new_balance=new_balance,
        )

    def harvest(
        self, user_id: int, username: str, plot_number: Optional[int] = None
    ) -> HarvestResult:
        """Harvest ready crops from one or all plots."""
        # Ensure user exists
        self.repo.get_user(user_id, username)

        total_plots = self.repo.get_farm_plots(user_id)

        if total_plots == 0:
            return HarvestResult(
                success=False,
                message="You don't own any plots yet! Use `!buyplot` to buy your first plot.",
            )

        planted_crops = self.repo.get_planted_crops(user_id)
        now = datetime.now()

        # Filter to specific plot if requested
        if plot_number is not None:
            if plot_number < 1 or plot_number > total_plots:
                return HarvestResult(
                    success=False,
                    message=f"Invalid plot number! You own plots 1-{total_plots}.",
                )
            planted_crops = [c for c in planted_crops if c.plot_number == plot_number]
            if not planted_crops:
                return HarvestResult(
                    success=False,
                    message=f"Plot #{plot_number} is empty! Use `!plant <crop> {plot_number}` to plant something.",
                )

        # Find ready crops
        ready_crops = [c for c in planted_crops if now >= c.ready_at]

        if not ready_crops:
            if plot_number is not None:
                crop_data = planted_crops[0]
                crop_info = get_crop_by_name(crop_data.crop_type)
                time_left = int((crop_data.ready_at - now).total_seconds())
                hours = time_left // 3600
                minutes = (time_left % 3600) // 60
                if hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m"
                return HarvestResult(
                    success=False,
                    message=f"Plot #{plot_number} has {crop_info.emoji if crop_info else '🌱'} **{crop_info.name if crop_info else crop_data.crop_type}** growing. Ready in **{time_str}**!",
                )
            return HarvestResult(
                success=False,
                message="No crops are ready to harvest yet!",
            )

        # Harvest all ready crops
        harvested = []
        total_stars = 0
        plots_to_clear = []

        for crop_data in ready_crops:
            crop_info = get_crop_by_name(crop_data.crop_type)
            if crop_info:
                harvested.append(
                    (crop_data.plot_number, crop_info.name, crop_info.emoji, crop_info.sell_price)
                )
                total_stars += crop_info.sell_price
                plots_to_clear.append(crop_data.plot_number)

        # Update database
        if plots_to_clear:
            self.repo.remove_crops(user_id, plots_to_clear)

        # Add stars to user
        balance = self.repo.get_user_stars(user_id, username)
        new_balance = balance + total_stars
        self.repo.update_user_stars(user_id, username, new_balance)

        return HarvestResult(
            success=True,
            message=f"Harvested {len(harvested)} crop(s) for **{total_stars}** stars!",
            harvested=harvested,
            total_stars=total_stars,
            new_balance=new_balance,
        )

    def get_crops_info(self) -> CropsInfo:
        """Get information about all available crops."""
        crops_list = []
        for crop_key, crop in CROPS.items():
            profit = crop.sell_price - crop.seed_cost
            crops_list.append(
                (crop.name, crop.emoji, crop.seed_cost, crop.sell_price, profit, crop.growth_hours)
            )
        return CropsInfo(crops=crops_list)

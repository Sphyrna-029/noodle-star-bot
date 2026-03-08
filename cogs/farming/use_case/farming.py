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

import random
from datetime import datetime, timedelta
from typing import Optional

from cogs.farming.constants import (
    CROPS,
    FARM_LEVEL_UPGRADE_COSTS,
    MAX_FARM_LEVEL,
    MAX_PLOTS,
    PLOT_COSTS,
    QUALITY_MULTIPLIERS,
    QUALITY_WEIGHTS_BY_LEVEL,
    SOIL_BAD_WEIGHT_BY_THRESHOLD,
    SOIL_DRAIN_BY_CROP,
    SOIL_MAX_CONDITION,
    SOIL_MULTIPLIER_BY_THRESHOLD,
    TEND_ITEM_SOIL_RESTORE,
    get_crop_by_name,
)
from cogs.farming.dto import (
    BuyPlotResult,
    CropsInfo,
    FarmStatus,
    HarvestResult,
    PlantResult,
    PlotStatus,
    TendPlotResult,
    UpgradeFarmLevelResult,
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
        plot_states = self.repo.get_plot_states(user_id)
        now = datetime.now()

        # Build plot statuses
        plots = []
        planted_by_plot = {crop.plot_number: crop for crop in planted_crops}

        for plot_num in range(1, total_plots + 1):
            crop_data = planted_by_plot.get(plot_num)

            if crop_data is None:
                # Empty plot
                state = plot_states.get(plot_num)
                plots.append(
                    PlotStatus(
                        plot_number=plot_num,
                        is_empty=True,
                        soil_condition=state.soil_condition if state else SOIL_MAX_CONDITION,
                        same_crop_streak=state.same_crop_streak if state else 0,
                    )
                )
            else:
                # Get crop info
                crop = get_crop_by_name(crop_data.crop_type)
                is_ready = now >= crop_data.ready_at
                time_remaining = 0
                if not is_ready:
                    time_remaining = int((crop_data.ready_at - now).total_seconds())
                state = plot_states.get(plot_num)

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
                        soil_condition=state.soil_condition if state else SOIL_MAX_CONDITION,
                        same_crop_streak=state.same_crop_streak if state else 0,
                    )
                )

        # Determine next plot cost
        next_plot_num = total_plots + 1
        next_plot_cost = PLOT_COSTS.get(next_plot_num)
        can_buy_more = next_plot_num <= MAX_PLOTS

        # Get user's star balance
        stars = self.repo.get_user_stars(user_id, username)
        farm_level = self.repo.get_farm_level(user_id)
        next_farm_level_cost = FARM_LEVEL_UPGRADE_COSTS.get(farm_level + 1)

        return FarmStatus(
            total_plots=total_plots,
            plots=plots,
            next_plot_cost=next_plot_cost,
            can_buy_more=can_buy_more,
            stars=stars,
            farm_level=farm_level,
            next_farm_level_cost=next_farm_level_cost,
        )

    def get_farm_level_info(self, user_id: int, username: str) -> tuple[int, Optional[int], int]:
        """Return (farm_level, next_upgrade_cost, current_stars)."""
        self.repo.get_user(user_id, username)
        farm_level = self.repo.get_farm_level(user_id)
        next_cost = FARM_LEVEL_UPGRADE_COSTS.get(farm_level + 1)
        stars = self.repo.get_user_stars(user_id, username)
        return farm_level, next_cost, stars

    def upgrade_farm_level(self, user_id: int, username: str) -> UpgradeFarmLevelResult:
        """Upgrade farm level to improve harvest quality odds."""
        self.repo.get_user(user_id, username)
        current_level = self.repo.get_farm_level(user_id)

        if current_level >= MAX_FARM_LEVEL:
            return UpgradeFarmLevelResult(
                success=False,
                message=f"Your farm is already max level ({MAX_FARM_LEVEL})!",
                old_level=current_level,
                new_level=current_level,
            )

        next_level = current_level + 1
        cost = FARM_LEVEL_UPGRADE_COSTS.get(next_level, 0)
        balance = self.repo.get_user_stars(user_id, username)

        if balance < cost:
            return UpgradeFarmLevelResult(
                success=False,
                message=f"You need **{cost}** stars to upgrade to farm level {next_level}, but you only have **{balance}** stars.",
                old_level=current_level,
                new_level=current_level,
                cost=cost,
                new_balance=balance,
            )

        new_balance = balance - cost
        self.repo.update_user_stars(user_id, username, new_balance)
        self.repo.set_farm_level(user_id, next_level)

        return UpgradeFarmLevelResult(
            success=True,
            message=f"Farm upgraded to **Level {next_level}**!",
            old_level=current_level,
            new_level=next_level,
            cost=cost,
            new_balance=new_balance,
        )

    @staticmethod
    def _soil_bad_weight_bonus(soil_condition: int) -> int:
        for threshold, bonus in SOIL_BAD_WEIGHT_BY_THRESHOLD:
            if soil_condition >= threshold:
                return bonus
        return 0

    @staticmethod
    def _soil_multiplier(soil_condition: int) -> float:
        for threshold, mult in SOIL_MULTIPLIER_BY_THRESHOLD:
            if soil_condition >= threshold:
                return mult
        return SOIL_MULTIPLIER_BY_THRESHOLD[-1][1]

    @classmethod
    def _roll_quality(cls, farm_level: int, soil_condition: int) -> tuple[str, float]:
        level = min(max(farm_level, 1), MAX_FARM_LEVEL)
        entries = list(QUALITY_WEIGHTS_BY_LEVEL[level])
        bad_bonus = cls._soil_bad_weight_bonus(soil_condition)
        if bad_bonus > 0:
            adjusted: dict[str, int] = {name: weight for name, weight in entries}
            adjusted["bad"] = adjusted.get("bad", 0) + bad_bonus
            # Remove from normal first, then great, to keep total at 100.
            shift_remaining = bad_bonus
            from_normal = min(shift_remaining, adjusted.get("normal", 0))
            adjusted["normal"] -= from_normal
            shift_remaining -= from_normal
            if shift_remaining > 0:
                adjusted["great"] = max(0, adjusted.get("great", 0) - shift_remaining)
            entries = list(adjusted.items())

        quality = random.choices(
            [entry[0] for entry in entries],
            weights=[entry[1] for entry in entries],
            k=1,
        )[0]
        return quality, QUALITY_MULTIPLIERS[quality]

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
        self.repo.get_plot_state(user_id, plot_number)

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
        plot_state = self.repo.get_plot_state(user_id, plot_number)
        new_streak = 1
        is_rotation = False
        if plot_state.last_crop_type == crop_name.lower():
            new_streak = plot_state.same_crop_streak + 1
        elif plot_state.last_crop_type:
            is_rotation = True
        self.repo.set_plot_crop_streak(user_id, plot_number, crop_name.lower(), new_streak)
        if is_rotation:
            self.repo.increment_achievement_progress(user_id, "farming_crop_rotations", 1)

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
        weather_blessed = []
        quality_rolls = []
        farm_level = self.repo.get_farm_level(user_id)
        mushrooms_earned = 0

        for crop_data in ready_crops:
            crop_info = get_crop_by_name(crop_data.crop_type)
            if crop_info:
                plot_state = self.repo.get_plot_state(user_id, crop_data.plot_number)
                soil_condition = max(0, min(SOIL_MAX_CONDITION, plot_state.soil_condition))
                soil_mult = self._soil_multiplier(soil_condition)
                # Special crop: mushroom plants yield mining mushrooms, not stars.
                if crop_info.golden_mushroom_yield > 0:
                    actual_price = 0
                    mushrooms_earned += crop_info.golden_mushroom_yield
                else:
                    quality_name, quality_multiplier = self._roll_quality(farm_level, soil_condition)
                    weather_multiplier = crop_data.weather_bonus
                    # Apply bonuses additively to match gameplay expectation:
                    # +20% great quality and +100% perfect weather = +120% total.
                    combined_multiplier = 1.0 + (quality_multiplier - 1.0) + (weather_multiplier - 1.0)
                    # Apply soil multiplier separately as a balancing gate.
                    actual_price = max(0, int(crop_info.sell_price * combined_multiplier * soil_mult))
                    quality_rolls.append(
                        (crop_data.plot_number, quality_name, quality_multiplier, weather_multiplier)
                    )
                    if weather_multiplier != 1.0:
                        weather_blessed.append(
                            (crop_info.name, crop_info.emoji, crop_info.sell_price, actual_price)
                        )

                harvested.append(
                    (crop_data.plot_number, crop_info.name, crop_info.emoji, actual_price)
                )
                total_stars += actual_price
                plots_to_clear.append(crop_data.plot_number)

                # Soil drain: base by crop + penalty for repeated same-crop streak.
                base_drain = SOIL_DRAIN_BY_CROP.get(crop_data.crop_type, 3)
                streak_penalty = max(0, min(3, plot_state.same_crop_streak - 1))
                new_soil = max(0, soil_condition - (base_drain + streak_penalty))
                self.repo.set_plot_soil_condition(user_id, crop_data.plot_number, new_soil)

        # Update database
        if plots_to_clear:
            self.repo.remove_crops(user_id, plots_to_clear)

        # Add stars to user
        balance = self.repo.get_user_stars(user_id, username)
        new_balance = balance + total_stars
        self.repo.update_user_stars(user_id, username, new_balance)

        if mushrooms_earned > 0:
            inventory = self.repo.get_user_inventory(user_id)
            self.repo.update_user_inventory(
                user_id,
                "golden_mushroom",
                inventory.get("golden_mushroom", 0) + mushrooms_earned,
            )

        summary = f"Harvested {len(harvested)} crop(s) for **{total_stars}** stars!"
        if mushrooms_earned > 0:
            summary += f" Found **{mushrooms_earned}** golden mushroom(s)!"

        return HarvestResult(
            success=True,
            message=summary,
            harvested=harvested,
            total_stars=total_stars,
            new_balance=new_balance,
            mushrooms_earned=mushrooms_earned,
            quality_rolls=quality_rolls,
            weather_blessed=weather_blessed,
        )

    def tend_plot(self, user_id: int, username: str, plot_number: int, item_name: str) -> TendPlotResult:
        """Apply a tending item to restore soil condition on a plot."""
        self.repo.get_user(user_id, username)
        total_plots = self.repo.get_farm_plots(user_id)
        if total_plots == 0:
            return TendPlotResult(
                success=False,
                message="You don't own any plots yet! Use `!buyplot` to buy your first plot.",
            )
        if plot_number < 1 or plot_number > total_plots:
            return TendPlotResult(
                success=False,
                message=f"Invalid plot number! You own plots 1-{total_plots}.",
            )

        item_key = item_name.strip().lower()
        if item_key not in TEND_ITEM_SOIL_RESTORE:
            valid = ", ".join(TEND_ITEM_SOIL_RESTORE.keys())
            return TendPlotResult(
                success=False,
                message=f"Unknown tending item `{item_name}`. Use one of: {valid}",
            )

        inventory = self.repo.get_user_inventory(user_id)
        current_count = inventory.get(item_key, 0)
        if current_count <= 0:
            return TendPlotResult(
                success=False,
                message=f"You don't have any {item_key}. Buy some from `!store` first.",
            )

        plot_state = self.repo.get_plot_state(user_id, plot_number)
        soil_before = max(0, min(SOIL_MAX_CONDITION, plot_state.soil_condition))
        restore = TEND_ITEM_SOIL_RESTORE[item_key]
        soil_after = min(SOIL_MAX_CONDITION, soil_before + restore)
        self.repo.set_plot_soil_condition(user_id, plot_number, soil_after)
        self.repo.update_user_inventory(user_id, item_key, current_count - 1)
        self.repo.increment_achievement_progress(user_id, "farming_tends", 1)

        return TendPlotResult(
            success=True,
            message=f"Tended plot #{plot_number} with {item_key}.",
            plot_number=plot_number,
            item_used=item_key,
            soil_before=soil_before,
            soil_after=soil_after,
            remaining_items=current_count - 1,
        )

    def get_crops_info(self) -> CropsInfo:
        """Get information about all available crops."""
        crops_list = []
        for crop_key, crop in CROPS.items():
            if crop.golden_mushroom_yield > 0:
                profit = 0
            else:
                profit = crop.sell_price - crop.seed_cost
            crops_list.append(
                (crop.name, crop.emoji, crop.seed_cost, crop.sell_price, profit, crop.growth_hours)
            )
        return CropsInfo(crops=crops_list)

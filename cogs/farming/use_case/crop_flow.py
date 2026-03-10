"""Crop purchase, planting, harvesting, and quality helpers."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional

from cogs.farming.constants import (
    CROPS,
    MAX_FARM_LEVEL,
    MAX_PLOTS,
    PLOT_COSTS,
    QUALITY_MULTIPLIERS,
    QUALITY_WEIGHTS_BY_LEVEL,
    SOIL_BAD_WEIGHT_BY_THRESHOLD,
    SOIL_DRAIN_BY_CROP,
    SOIL_MAX_CONDITION,
    SOIL_MULTIPLIER_BY_THRESHOLD,
    get_crop_by_name,
)
from cogs.farming.dto import BuyPlotResult, HarvestResult, PlantResult
from .base import FarmingUseCaseMixin


class CropFlowMixin(FarmingUseCaseMixin):
    """Crop and plot flow operations."""

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
        """Buy a new farm plot."""
        self.repo.get_user(user_id, username)
        current_plots = self.repo.get_farm_plots(user_id)

        if plot_number == 0:
            target_plot_num = current_plots + 1
        else:
            target_plot_num = plot_number
            if target_plot_num != current_plots + 1:
                if target_plot_num <= current_plots:
                    return BuyPlotResult(success=False, message=f"You already own plot #{target_plot_num}!")
                return BuyPlotResult(
                    success=False,
                    message=f"You must buy plots in order! Buy plot #{current_plots + 1} first.",
                )

        if target_plot_num > MAX_PLOTS:
            return BuyPlotResult(
                success=False,
                message=f"You already own the maximum of {MAX_PLOTS} plots!",
            )

        cost = PLOT_COSTS.get(target_plot_num)
        if cost is None:
            return BuyPlotResult(success=False, message="Invalid plot number.")

        balance = self.repo.get_user_stars(user_id, username)
        if balance < cost:
            return BuyPlotResult(
                success=False,
                message=f"You need **{cost}** stars to buy plot #{target_plot_num}, but you only have **{balance}** stars!",
            )

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

    def plant_crop(self, user_id: int, username: str, crop_name: str, plot_number: int) -> PlantResult:
        """Plant a crop in a specific plot."""
        self.repo.get_user(user_id, username)
        total_plots = self.repo.get_farm_plots(user_id)

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

        existing_crop = self.repo.get_planted_crop(user_id, plot_number)
        if existing_crop is not None:
            crop_info = get_crop_by_name(existing_crop.crop_type)
            emoji = crop_info.emoji if crop_info else "🌱"
            name = crop_info.name if crop_info else existing_crop.crop_type
            return PlantResult(
                success=False,
                message=f"Plot #{plot_number} already has {emoji} **{name}** planted! Harvest it first.",
            )

        crop = get_crop_by_name(crop_name)
        if crop is None:
            available = ", ".join(CROPS.keys())
            return PlantResult(
                success=False,
                message=f"Unknown crop `{crop_name}`! Available crops: {available}",
            )

        balance = self.repo.get_user_stars(user_id, username)
        if balance < crop.seed_cost:
            return PlantResult(
                success=False,
                message=f"You need **{crop.seed_cost}** stars for {crop.emoji} {crop.name} seeds, but you only have **{balance}** stars!",
            )

        new_balance = balance - crop.seed_cost
        self.repo.update_user_stars(user_id, username, new_balance)

        now = datetime.now()
        ready_at = now + timedelta(hours=crop.growth_hours)
        crop_key = crop_name.lower()
        self.repo.plant_crop(user_id, plot_number, crop_key, now, ready_at)

        plot_state = self.repo.get_plot_state(user_id, plot_number)
        new_streak = 1
        is_rotation = False
        if plot_state.last_crop_type == crop_key:
            new_streak = plot_state.same_crop_streak + 1
        elif plot_state.last_crop_type:
            is_rotation = True
        self.repo.set_plot_crop_streak(user_id, plot_number, crop_key, new_streak)
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

    def harvest(self, user_id: int, username: str, plot_number: Optional[int] = None) -> HarvestResult:
        """Harvest ready crops from one or all plots."""
        self.repo.get_user(user_id, username)
        total_plots = self.repo.get_farm_plots(user_id)
        if total_plots == 0:
            return HarvestResult(
                success=False,
                message="You don't own any plots yet! Use `!buyplot` to buy your first plot.",
            )

        planted_crops = self.repo.get_planted_crops(user_id)
        now = datetime.now()

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

        ready_crops = [c for c in planted_crops if now >= c.ready_at]
        if not ready_crops:
            if plot_number is not None:
                crop_data = planted_crops[0]
                crop_info = get_crop_by_name(crop_data.crop_type)
                time_left = int((crop_data.ready_at - now).total_seconds())
                hours = time_left // 3600
                minutes = (time_left % 3600) // 60
                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                return HarvestResult(
                    success=False,
                    message=f"Plot #{plot_number} has {crop_info.emoji if crop_info else '🌱'} **{crop_info.name if crop_info else crop_data.crop_type}** growing. Ready in **{time_str}**!",
                )
            return HarvestResult(success=False, message="No crops are ready to harvest yet!")

        harvested = []
        total_stars = 0
        plots_to_clear = []
        weather_blessed = []
        quality_rolls = []
        farm_level = self.repo.get_farm_level(user_id)
        mushrooms_earned = 0

        bag_count = self.repo.get_inventory_count(user_id)
        bag_capacity = self.repo.get_inventory_capacity(user_id)
        available_space = bag_capacity - bag_count
        items_added = 0
        skipped = 0

        for crop_data in ready_crops:
            crop_info = get_crop_by_name(crop_data.crop_type)
            if not crop_info:
                continue

            plot_state = self.repo.get_plot_state(user_id, crop_data.plot_number)
            soil_condition = max(0, min(SOIL_MAX_CONDITION, plot_state.soil_condition))
            soil_mult = self._soil_multiplier(soil_condition)

            if crop_info.golden_mushroom_yield > 0:
                actual_price = 0
                mushrooms_earned += crop_info.golden_mushroom_yield
            else:
                quality_name, quality_multiplier = self._roll_quality(farm_level, soil_condition)
                weather_multiplier = crop_data.weather_bonus
                combined_multiplier = 1.0 + (quality_multiplier - 1.0) + (weather_multiplier - 1.0)
                actual_price = max(0, int(crop_info.sell_price * combined_multiplier * soil_mult))
                quality_rolls.append(
                    (crop_data.plot_number, quality_name, quality_multiplier, weather_multiplier)
                )
                if weather_multiplier != 1.0:
                    weather_blessed.append((crop_info.name, crop_info.emoji, crop_info.sell_price, actual_price))

                # Add crop item to inventory with baked-in sell value
                crop_key = crop_info.name.lower().replace(" ", "_")
                if items_added < available_space:
                    self.repo.add_item(user_id, crop_key, "crop", actual_price, quality=quality_name)
                    items_added += 1
                else:
                    skipped += 1
                    continue  # Skip this crop but keep it planted (don't remove it)

            harvested.append((crop_data.plot_number, crop_info.name, crop_info.emoji, actual_price))
            total_stars += actual_price
            plots_to_clear.append(crop_data.plot_number)

            base_drain = SOIL_DRAIN_BY_CROP.get(crop_data.crop_type, 3)
            streak_penalty = max(0, min(3, plot_state.same_crop_streak - 1))
            new_soil = max(0, soil_condition - (base_drain + streak_penalty))
            self.repo.set_plot_soil_condition(user_id, crop_data.plot_number, new_soil)

        if plots_to_clear:
            self.repo.remove_crops(user_id, plots_to_clear)

        balance = self.repo.get_user_stars(user_id, username)
        new_balance = balance  # No star change from harvesting

        if mushrooms_earned > 0:
            inventory_after = self.repo.get_user_inventory(user_id)
            self.repo.update_user_inventory(
                user_id,
                "golden_mushroom",
                inventory_after.get("golden_mushroom", 0) + mushrooms_earned,
            )


        summary = f"Harvested {len(harvested)} crop(s)!"
        if mushrooms_earned > 0:
            summary += f" Found **{mushrooms_earned}** golden mushroom(s)!"
        if skipped > 0:
            summary += f" {skipped} crop(s) left unharvested (inventory full)."

        return HarvestResult(
            success=True,
            message=summary,
            harvested=harvested,
            total_stars=total_stars,
            new_balance=new_balance,
            mushrooms_earned=mushrooms_earned,
            quality_rolls=quality_rolls,
            weather_blessed=weather_blessed,
            preserver_bonus_queued=0,
            preserver_ready_in_seconds=0,
            items_added=items_added,
            bag_count=self.repo.get_inventory_count(user_id),
            bag_capacity=bag_capacity,
            inventory_full_skipped=skipped,
        )

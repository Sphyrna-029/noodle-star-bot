"""GrowBot automation helpers for farming actions."""

from __future__ import annotations

from datetime import datetime, timedelta

from cogs.farming.constants import (
    CROPS,
    GROWBOT_PLOT_CAPACITY_BY_LEVEL,
    MAX_GROWBOT_LEVEL,
    MAX_PLOTS,
    SOIL_MAX_CONDITION,
    TEND_ITEM_SOIL_RESTORE,
    get_crop_by_name,
)
from cogs.farming.dto import GrowBotPlantResult, GrowBotTendResult, HarvestResult
from .base import FarmingUseCaseMixin


class GrowBotMixin(FarmingUseCaseMixin):
    """Farm automation actions gated by GrowBot ownership."""

    @staticmethod
    def _growbot_capacity(level: int) -> int:
        clamped_level = min(max(level, 1), MAX_GROWBOT_LEVEL)
        return GROWBOT_PLOT_CAPACITY_BY_LEVEL.get(clamped_level, MAX_PLOTS)

    def _get_growbot_level(self, user_id: int) -> int:
        inventory = self.repo.get_user_inventory(user_id)
        if inventory.get("growbot_owned", 0) <= 0:
            return 0
        level = inventory.get("growbot_level", 0)
        return max(1, level)

    def growbot_harvest(self, user_id: int, username: str) -> HarvestResult:
        """Harvest all ready crops using GrowBot."""
        level = self._get_growbot_level(user_id)
        if level <= 0:
            return HarvestResult(
                success=False,
                message="You don't own a GrowBot yet. Buy one from `!store` first.",
            )

        # Level-based capacity exists for future upgrades; level 1 covers all current plots.
        return self.harvest(user_id, username, plot_number=None)

    def growbot_tend_all(
        self,
        user_id: int,
        username: str,
        item_name: str,
    ) -> GrowBotTendResult:
        """Tend multiple plots with one command using GrowBot."""
        self.repo.get_user(user_id, username)
        level = self._get_growbot_level(user_id)
        if level <= 0:
            return GrowBotTendResult(
                success=False,
                message="You don't own a GrowBot yet. Buy one from `!store` first.",
            )

        total_plots = self.repo.get_farm_plots(user_id)
        if total_plots == 0:
            return GrowBotTendResult(
                success=False,
                message="You don't own any plots yet! Use `!buyplot` to buy your first plot.",
            )

        item_key = item_name.strip().lower()
        if item_key not in TEND_ITEM_SOIL_RESTORE:
            valid = ", ".join(TEND_ITEM_SOIL_RESTORE.keys())
            return GrowBotTendResult(
                success=False,
                message=f"Unknown tending item `{item_name}`. Use one of: {valid}",
            )

        inventory = self.repo.get_user_inventory(user_id)
        remaining_items = inventory.get(item_key, 0)
        if remaining_items <= 0:
            return GrowBotTendResult(
                success=False,
                message=f"You don't have any {item_key}. Buy some from `!store` first.",
            )

        restore = TEND_ITEM_SOIL_RESTORE[item_key]
        capacity = min(total_plots, self._growbot_capacity(level))
        tended_plots: list[tuple[int, int, int]] = []
        skipped_full_soil: list[int] = []

        for plot_number in range(1, capacity + 1):
            plot_state = self.repo.get_plot_state(user_id, plot_number)
            soil_before = max(0, min(SOIL_MAX_CONDITION, plot_state.soil_condition))

            if soil_before >= SOIL_MAX_CONDITION:
                skipped_full_soil.append(plot_number)
                continue

            if remaining_items <= 0:
                break

            soil_after = min(SOIL_MAX_CONDITION, soil_before + restore)
            self.repo.set_plot_soil_condition(user_id, plot_number, soil_after)
            tended_plots.append((plot_number, soil_before, soil_after))
            remaining_items -= 1

        used_items = inventory.get(item_key, 0) - remaining_items
        if used_items > 0:
            self.repo.update_user_inventory(user_id, item_key, remaining_items)
            self.repo.increment_achievement_progress(user_id, "farming_tends", used_items)

        if not tended_plots:
            if skipped_full_soil:
                return GrowBotTendResult(
                    success=False,
                    message="All eligible plots are already at max soil condition.",
                    item_used=item_key,
                    skipped_full_soil=skipped_full_soil,
                    remaining_items=remaining_items,
                )
            return GrowBotTendResult(
                success=False,
                message="No plots were tended.",
                item_used=item_key,
                remaining_items=remaining_items,
            )

        return GrowBotTendResult(
            success=True,
            message=f"GrowBot tended {len(tended_plots)} plot(s).",
            item_used=item_key,
            tended_plots=tended_plots,
            skipped_full_soil=skipped_full_soil,
            remaining_items=remaining_items,
        )

    def growbot_plant_all(
        self,
        user_id: int,
        username: str,
        crop_name: str,
        plot_selector: str = "",
    ) -> GrowBotPlantResult:
        """Plant one crop type across all eligible empty plots."""
        self.repo.get_user(user_id, username)
        level = self._get_growbot_level(user_id)
        if level <= 0:
            return GrowBotPlantResult(
                success=False,
                message="You don't own a GrowBot yet. Buy one from `!store` first.",
            )

        total_plots = self.repo.get_farm_plots(user_id)
        if total_plots == 0:
            return GrowBotPlantResult(
                success=False,
                message="You don't own any plots yet! Use `!buyplot` to buy your first plot.",
            )

        crop_key = crop_name.strip().lower()
        crop = get_crop_by_name(crop_key)
        if crop is None:
            available = ", ".join(CROPS.keys())
            return GrowBotPlantResult(
                success=False,
                message=f"Unknown crop `{crop_name}`! Available crops: {available}",
            )

        balance = self.repo.get_user_stars(user_id, username)
        capacity = min(total_plots, self._growbot_capacity(level))

        selector = plot_selector.strip()
        if selector:
            # Single integer means "first N eligible plots".
            if selector.isdigit():
                requested_count = int(selector)
                if requested_count <= 0:
                    return GrowBotPlantResult(
                        success=False,
                        message="Plot count must be at least 1.",
                    )
                target_plots = list(range(1, capacity + 1))[:requested_count]
            else:
                raw_parts = [part.strip() for part in selector.replace(",", " ").split() if part.strip()]
                try:
                    requested_plots = [int(part) for part in raw_parts]
                except ValueError:
                    return GrowBotPlantResult(
                        success=False,
                        message="Invalid plot selector. Use a number (`3`) or plot list (`1,3,6`).",
                    )
                if not requested_plots:
                    return GrowBotPlantResult(
                        success=False,
                        message="Invalid plot selector. Use a number (`3`) or plot list (`1,3,6`).",
                    )
                unique_plots: list[int] = []
                seen = set()
                for plot_number in requested_plots:
                    if plot_number in seen:
                        continue
                    seen.add(plot_number)
                    unique_plots.append(plot_number)
                invalid = [plot for plot in unique_plots if plot < 1 or plot > capacity]
                if invalid:
                    return GrowBotPlantResult(
                        success=False,
                        message=(
                            f"Invalid plot numbers: {', '.join(str(p) for p in invalid)}. "
                            f"You can target plots 1-{capacity}."
                        ),
                    )
                target_plots = unique_plots
        else:
            target_plots = list(range(1, capacity + 1))

        planted_by_plot = {
            planted.plot_number: planted
            for planted in self.repo.get_planted_crops(user_id)
        }

        planted_plots: list[int] = []
        skipped_occupied: list[int] = []
        total_seed_cost = 0
        now = datetime.now()

        for plot_number in target_plots:
            if plot_number in planted_by_plot:
                skipped_occupied.append(plot_number)
                continue

            if balance < crop.seed_cost:
                break

            ready_at = now + timedelta(hours=crop.growth_hours)
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

            balance -= crop.seed_cost
            total_seed_cost += crop.seed_cost
            planted_plots.append(plot_number)

        if total_seed_cost > 0:
            self.repo.update_user_stars(user_id, username, balance)

        if not planted_plots:
            if skipped_occupied:
                return GrowBotPlantResult(
                    success=False,
                    message="No empty plots available for planting.",
                    crop_name=crop.name,
                    crop_emoji=crop.emoji,
                    skipped_occupied=skipped_occupied,
                    new_balance=balance,
                )
            return GrowBotPlantResult(
                success=False,
                message=f"You need at least **{crop.seed_cost}** stars to plant {crop.emoji} **{crop.name}**.",
                crop_name=crop.name,
                crop_emoji=crop.emoji,
                new_balance=balance,
            )

        return GrowBotPlantResult(
            success=True,
            message=f"GrowBot planted {crop.emoji} {crop.name} in {len(planted_plots)} plot(s).",
            crop_name=crop.name,
            crop_emoji=crop.emoji,
            planted_plots=planted_plots,
            skipped_occupied=skipped_occupied,
            total_seed_cost=total_seed_cost,
            new_balance=balance,
        )

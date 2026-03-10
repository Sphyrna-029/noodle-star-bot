"""Farm status and base progression use-cases."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from cogs.farming.constants import (
    FARM_LEVEL_UPGRADE_COSTS,
    MAX_FARM_LEVEL,
    MAX_PLOTS,
    PLOT_COSTS,
    PRESERVER_UPGRADE_COSTS,
    SOIL_MAX_CONDITION,
    get_crop_by_name,
)
from cogs.farming.dto import FarmStatus, PlotStatus, UpgradeFarmLevelResult
from .base import FarmingUseCaseMixin


class FarmProgressionMixin(FarmingUseCaseMixin):
    """Farm status and level progression operations."""

    def get_farm_status(self, user_id: int, username: str) -> FarmStatus:
        """Get the current status of a user's farm."""
        self.repo.get_user(user_id, username)

        total_plots = self.repo.get_farm_plots(user_id)
        planted_crops = self.repo.get_planted_crops(user_id)
        plot_states = self.repo.get_plot_states(user_id)
        now = datetime.now()

        plots = []
        planted_by_plot = {crop.plot_number: crop for crop in planted_crops}

        for plot_num in range(1, total_plots + 1):
            crop_data = planted_by_plot.get(plot_num)

            if crop_data is None:
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
                crop = get_crop_by_name(crop_data.crop_type)
                is_ready = now >= crop_data.ready_at
                time_remaining = int((crop_data.ready_at - now).total_seconds()) if not is_ready else 0
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

        next_plot_num = total_plots + 1
        next_plot_cost = PLOT_COSTS.get(next_plot_num)
        can_buy_more = next_plot_num <= MAX_PLOTS

        stars = self.repo.get_user_stars(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        farm_level = self.repo.get_farm_level(user_id)
        next_farm_level_cost = FARM_LEVEL_UPGRADE_COSTS.get(farm_level + 1)
        preserver_owned = inventory.get("preserver_owned", 0) > 0
        preserver_level = inventory.get("preserver_level", 0)
        preserver_next_cost = PRESERVER_UPGRADE_COSTS.get(preserver_level + 1) if preserver_owned else None
        preserver_pending_stars = inventory.get("preserver_pending_stars", 0)
        ready_ts = inventory.get("preserver_ready_ts", 0)
        now_ts = int(datetime.now().timestamp())
        preserver_ready_in_seconds = max(0, int(ready_ts) - now_ts) if ready_ts else 0
        growbot_owned = inventory.get("growbot_owned", 0) > 0
        growbot_level = max(1, inventory.get("growbot_level", 0)) if growbot_owned else 0

        return FarmStatus(
            total_plots=total_plots,
            plots=plots,
            next_plot_cost=next_plot_cost,
            can_buy_more=can_buy_more,
            stars=stars,
            farm_level=farm_level,
            next_farm_level_cost=next_farm_level_cost,
            preserver_owned=preserver_owned,
            preserver_level=preserver_level,
            preserver_next_cost=preserver_next_cost,
            preserver_pending_stars=preserver_pending_stars,
            preserver_ready_in_seconds=preserver_ready_in_seconds,
            growbot_owned=growbot_owned,
            growbot_level=growbot_level,
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

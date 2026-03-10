"""Soil tending and crop catalog use-cases."""

from __future__ import annotations

from cogs.farming.constants import CROPS, SOIL_MAX_CONDITION, TEND_ITEM_SOIL_RESTORE
from cogs.farming.dto import CropsInfo, TendPlotResult
from .base import FarmingUseCaseMixin


class TendingMixin(FarmingUseCaseMixin):
    """Tending and crop-info helpers."""

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
        for crop in CROPS.values():
            profit = 0 if crop.golden_mushroom_yield > 0 else crop.sell_price - crop.seed_cost
            crops_list.append(
                (crop.name, crop.emoji, crop.seed_cost, crop.sell_price, profit, crop.growth_hours)
            )
        return CropsInfo(crops=crops_list)

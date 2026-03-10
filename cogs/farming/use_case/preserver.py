"""Preserver machine use-cases."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from cogs.farming.constants import (
    MAX_PRESERVER_LEVEL,
    PRESERVER_BONUS_BY_LEVEL,
    PRESERVER_PROCESSING_HOURS_BY_LEVEL,
    PRESERVER_UPGRADE_COSTS,
    SOIL_DRAIN_BY_CROP,
    SOIL_MAX_CONDITION,
    get_crop_by_name,
)
from cogs.farming.dto import CollectPreserverResult, StartPreserverResult, UpgradePreserverResult
from .base import FarmingUseCaseMixin


class PreserverMixin(FarmingUseCaseMixin):
    """Preserver machine status and progression."""

    def _normalize_preserver_level(self, user_id: int, inventory: dict) -> int:
        """Ensure owned preservers have a minimum level of 1."""
        if inventory.get("preserver_owned", 0) <= 0:
            return 0
        raw_level = int(inventory.get("preserver_level", 0) or 0)
        level = max(1, raw_level)
        if level != raw_level:
            self.repo.update_user_inventory(user_id, "preserver_level", level)
            inventory["preserver_level"] = level
        return level

    def get_preserver_info(
        self, user_id: int, username: str
    ) -> tuple[bool, int, Optional[int], int, int]:
        """Return (owned, level, next_upgrade_cost, pending_stars, ready_in_seconds)."""
        self.repo.get_user(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        owned = inventory.get("preserver_owned", 0) > 0
        level = self._normalize_preserver_level(user_id, inventory)
        next_cost = PRESERVER_UPGRADE_COSTS.get(level + 1) if owned else None
        pending = inventory.get("preserver_pending_stars", 0)
        ready_ts = inventory.get("preserver_ready_ts", 0)
        now_ts = int(datetime.now().timestamp())
        ready_in = max(0, int(ready_ts) - now_ts) if ready_ts else 0
        return owned, level, next_cost, pending, ready_in

    def upgrade_preserver(self, user_id: int, username: str) -> UpgradePreserverResult:
        """Upgrade preserver level (single machine progression)."""
        self.repo.get_user(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        if inventory.get("preserver_owned", 0) <= 0:
            return UpgradePreserverResult(
                success=False,
                message="You need to buy a Preserver from `!store` first.",
            )

        current_level = self._normalize_preserver_level(user_id, inventory)
        if current_level >= MAX_PRESERVER_LEVEL:
            return UpgradePreserverResult(
                success=False,
                message=f"Your Preserver is already max level ({MAX_PRESERVER_LEVEL})!",
                old_level=current_level,
                new_level=current_level,
            )

        next_level = current_level + 1
        cost = PRESERVER_UPGRADE_COSTS.get(next_level, 0)
        balance = self.repo.get_user_stars(user_id, username)
        if balance < cost:
            return UpgradePreserverResult(
                success=False,
                message=f"You need **{cost}** stars to upgrade Preserver level {next_level}, but you only have **{balance}** stars.",
                old_level=current_level,
                new_level=current_level,
                cost=cost,
                new_balance=balance,
            )

        new_balance = balance - cost
        self.repo.update_user_stars(user_id, username, new_balance)
        self.repo.update_user_inventory(user_id, "preserver_level", next_level)
        return UpgradePreserverResult(
            success=True,
            message=f"Preserver upgraded to **Level {next_level}**!",
            old_level=current_level,
            new_level=next_level,
            cost=cost,
            new_balance=new_balance,
        )

    def start_preserver(self, user_id: int, username: str) -> StartPreserverResult:
        """Start Preserver processing by consuming ready preservable crops."""
        self.repo.get_user(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        if inventory.get("preserver_owned", 0) <= 0:
            return StartPreserverResult(
                success=False,
                message="You don't own a Preserver yet. Buy one from `!store`.",
            )

        preserver_level = self._normalize_preserver_level(user_id, inventory)

        planted_crops = self.repo.get_planted_crops(user_id)
        if not planted_crops:
            return StartPreserverResult(
                success=False,
                message="You don't have any crops planted yet.",
            )

        now = datetime.now()
        ready_preservable = [
            crop
            for crop in planted_crops
            if now >= crop.ready_at and crop.crop_type == "melon"
        ]
        if not ready_preservable:
            return StartPreserverResult(
                success=False,
                message="No ready crops can be preserved right now. Only 🍉 Melons are preservable.",
            )

        farm_level = self.repo.get_farm_level(user_id)
        preserver_pending = inventory.get("preserver_pending_stars", 0)
        preserver_ready_ts = inventory.get("preserver_ready_ts", 0)
        now_ts = int(now.timestamp())

        preserved: list[tuple[int, str, str, int]] = []
        total_queued = 0
        plots_to_clear: list[int] = []

        for crop_data in ready_preservable:
            crop_info = get_crop_by_name(crop_data.crop_type)
            if not crop_info:
                continue

            plot_state = self.repo.get_plot_state(user_id, crop_data.plot_number)
            soil_condition = max(0, min(SOIL_MAX_CONDITION, plot_state.soil_condition))
            soil_mult = self._soil_multiplier(soil_condition)

            _quality_name, quality_multiplier = self._roll_quality(farm_level, soil_condition)
            weather_multiplier = crop_data.weather_bonus
            combined_multiplier = 1.0 + (quality_multiplier - 1.0) + (weather_multiplier - 1.0)
            actual_price = max(0, int(crop_info.sell_price * combined_multiplier * soil_mult))
            if actual_price <= 0:
                continue

            bonus_rate = PRESERVER_BONUS_BY_LEVEL.get(preserver_level, 0.0)
            queued_bonus = int(actual_price * bonus_rate)
            queued_total = actual_price + queued_bonus
            if queued_total <= 0:
                continue

            preserved.append((crop_data.plot_number, crop_info.name, crop_info.emoji, queued_total))
            total_queued += queued_total
            preserver_pending += queued_total
            plots_to_clear.append(crop_data.plot_number)

            base_drain = SOIL_DRAIN_BY_CROP.get(crop_data.crop_type, 3)
            streak_penalty = max(0, min(3, plot_state.same_crop_streak - 1))
            new_soil = max(0, soil_condition - (base_drain + streak_penalty))
            self.repo.set_plot_soil_condition(user_id, crop_data.plot_number, new_soil)

        if not plots_to_clear:
            return StartPreserverResult(
                success=False,
                message="No ready crops produced preservable stars. Try again later.",
            )

        self.repo.remove_crops(user_id, plots_to_clear)
        if preserver_ready_ts <= now_ts:
            processing_hours = PRESERVER_PROCESSING_HOURS_BY_LEVEL.get(preserver_level, 6)
            preserver_ready_ts = now_ts + (processing_hours * 3600)

        self.repo.update_user_inventory(user_id, "preserver_pending_stars", preserver_pending)
        self.repo.update_user_inventory(user_id, "preserver_ready_ts", preserver_ready_ts)

        ready_in = max(0, int(preserver_ready_ts) - now_ts) if preserver_ready_ts else 0
        return StartPreserverResult(
            success=True,
            message=f"Preserver started with **{len(preserved)}** crop(s).",
            preserved=preserved,
            total_queued=total_queued,
            pending_stars=preserver_pending,
            ready_in_seconds=ready_in,
        )

    def collect_preserver(self, user_id: int, username: str) -> CollectPreserverResult:
        """Collect processed stars from Preserver if ready."""
        self.repo.get_user(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        if inventory.get("preserver_owned", 0) <= 0:
            return CollectPreserverResult(
                success=False,
                message="You don't own a Preserver yet. Buy one from `!store`.",
            )

        pending = inventory.get("preserver_pending_stars", 0)
        ready_ts = inventory.get("preserver_ready_ts", 0)
        now_ts = int(datetime.now().timestamp())
        ready_in = max(0, int(ready_ts) - now_ts) if ready_ts else 0

        if pending <= 0:
            return CollectPreserverResult(
                success=False,
                message="You have no processed stars waiting in the Preserver.",
            )
        if ready_in > 0:
            return CollectPreserverResult(
                success=False,
                message="Your Preserver is still processing.",
                ready_in_seconds=ready_in,
            )

        balance = self.repo.get_user_stars(user_id, username)
        new_balance = balance + pending
        self.repo.update_user_stars(user_id, username, new_balance)
        self.repo.update_user_inventory(user_id, "preserver_pending_stars", 0)
        self.repo.update_user_inventory(user_id, "preserver_ready_ts", 0)
        return CollectPreserverResult(
            success=True,
            message=f"Collected **{pending}** processed stars from the Preserver!",
            collected_stars=pending,
            new_balance=new_balance,
            ready_in_seconds=0,
        )

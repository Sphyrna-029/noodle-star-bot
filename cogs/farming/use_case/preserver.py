"""Preserver machine use-cases."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from cogs.farming.constants import MAX_PRESERVER_LEVEL, PRESERVER_UPGRADE_COSTS
from cogs.farming.dto import CollectPreserverResult, UpgradePreserverResult
from .base import FarmingUseCaseMixin


class PreserverMixin(FarmingUseCaseMixin):
    """Preserver machine status and progression."""

    def get_preserver_info(
        self, user_id: int, username: str
    ) -> tuple[bool, int, Optional[int], int, int]:
        """Return (owned, level, next_upgrade_cost, pending_stars, ready_in_seconds)."""
        self.repo.get_user(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        owned = inventory.get("preserver_owned", 0) > 0
        level = inventory.get("preserver_level", 0)
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

        current_level = inventory.get("preserver_level", 0)
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

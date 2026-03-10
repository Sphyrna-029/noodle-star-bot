"""Shared typing base for farming use-case mixins."""

from __future__ import annotations

from typing import Optional

from database.repository import UserRepository

from cogs.farming.dto import HarvestResult


class FarmingUseCaseMixin:
    """Declare attributes injected by the composed farming facade."""

    repo: UserRepository

    def harvest(self, user_id: int, username: str, plot_number: Optional[int] = None) -> HarvestResult:
        """Declared for mixins that delegate to crop-flow harvest logic."""
        raise NotImplementedError

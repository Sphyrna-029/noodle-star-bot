import random
from typing import Optional

from cogs.gambling.constants import GAMBLE_TIER_CDF
from cogs.gambling.dto import GambleResult
from .base import BaseGamblingUseCase


class GambleUseCase(BaseGamblingUseCase):
    """Handles the basic gamble game logic."""

    def _roll_tier(self) -> int:
        """Roll once against the tier CDF and return the multiplier (0 = loss)."""
        rand = random.random()
        for multiplier, threshold in GAMBLE_TIER_CDF:
            if rand < threshold:
                return multiplier
        return 0

    def execute(self, user_id: int, username: str, amount: Optional[int]) -> GambleResult:
        """
        Play the gamble game (single-roll tier system).

        Args:
            user_id: Discord user ID
            username: Discord username
            amount: Amount to gamble

        Returns:
            GambleResult with outcome
        """
        current_stars = self.repo.get_user_stars(user_id, username)

        if amount is None:
            return GambleResult(
                success=False,
                won=False,
                message="Please specify how many stars to gamble! Usage: `!gamble <amount>`",
            )

        if amount <= 0:
            return GambleResult(
                success=False,
                won=False,
                message="You must gamble at least 1 noodle star!",
            )

        if current_stars <= 0:
            return GambleResult(
                success=False,
                won=False,
                message=f"You need at least 1 noodle star to gamble! Current balance: **{current_stars}** stars",
            )

        if amount > current_stars:
            return GambleResult(
                success=False,
                won=False,
                message=f"You only have **{current_stars}** stars! You can't gamble **{amount}** stars!",
            )

        multiplier = self._roll_tier()
        deducted_balance = current_stars - amount

        if multiplier > 0:
            winnings = int(amount * multiplier)
            new_balance = deducted_balance + winnings
            self.repo.update_user_stars(
                user_id, username, new_balance, reason="gambling:gamble_win"
            )

            return GambleResult(
                success=True,
                won=True,
                message="WIN",
                multiplier=multiplier,
                amount_changed=winnings - amount,
                new_balance=new_balance,
            )
        else:
            new_balance = deducted_balance
            self.repo.update_user_stars(
                user_id, username, new_balance, reason="gambling:gamble_loss"
            )

            return GambleResult(
                success=True,
                won=False,
                message="LOSE",
                multiplier=0,
                amount_changed=-amount,
                new_balance=new_balance,
            )

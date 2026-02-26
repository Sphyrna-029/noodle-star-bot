import random
from typing import Optional

from cogs.gambling.constants import (
    GAMBLE_DICE_SIDES,
    GAMBLE_MULTIPLIER_CDF,
    GAMBLE_WIN_TARGET,
)
from cogs.gambling.dto import GambleResult
from .base import BaseGamblingUseCase


class GambleUseCase(BaseGamblingUseCase):
    """Handles the basic gamble game logic."""

    def _select_multiplier(self) -> float:
        """
        Select a random multiplier based on weighted probabilities.

        Uses the original bot's logic:
        - 1% chance for 5x
        - 33% chance for 1.25x
        - 33% chance for 1.5x
        - 33% chance for 2x
        """
        rand = random.random()
        for multiplier, threshold in GAMBLE_MULTIPLIER_CDF:
            if rand < threshold:
                return multiplier
        return GAMBLE_MULTIPLIER_CDF[-1][0]  # Default to last multiplier

    def execute(self, user_id: int, username: str, amount: Optional[int]) -> GambleResult:
        """
        Play the gamble game (roll to 7).

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

        multiplier = self._select_multiplier()
        roll = random.randint(1, GAMBLE_DICE_SIDES)

        deducted_balance = current_stars - amount

        if roll == GAMBLE_WIN_TARGET:
            winnings = int(amount * multiplier)
            new_balance = deducted_balance + winnings
            self.repo.update_user_stars(user_id, username, new_balance)

            return GambleResult(
                success=True,
                won=True,
                message="WIN",
                roll=roll,
                multiplier=multiplier,
                amount_changed=winnings - amount,
                new_balance=new_balance,
            )
        else:
            new_balance = deducted_balance
            self.repo.update_user_stars(user_id, username, new_balance)

            return GambleResult(
                success=True,
                won=False,
                message="LOSE",
                roll=roll,
                multiplier=multiplier,
                amount_changed=-amount,
                new_balance=new_balance,
            )

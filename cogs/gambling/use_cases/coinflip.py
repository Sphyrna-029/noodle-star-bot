import random
from typing import Optional

from cogs.gambling.constants import (
    COINFLIP_MIN_BET,
    COINFLIP_WIN_MULTIPLIER,
)
from cogs.gambling.dto import CoinflipResult
from .base import BaseGamblingUseCase


class CoinflipUseCase(BaseGamblingUseCase):
    """Handles the coinflip game logic."""

    def execute(
        self, user_id: int, username: str, amount: Optional[int], choice: str
    ) -> CoinflipResult:
        """
        Play the coinflip game.

        Args:
            user_id: Discord user ID
            username: Discord username
            amount: Amount to bet
            choice: "heads" or "tails" (or "h"/"t")

        Returns:
            CoinflipResult with outcome
        """
        current_stars = self.repo.get_user_stars(user_id, username)

        # Validation
        if amount is None or choice is None:
            return CoinflipResult(
                success=False,
                won=False,
                message="Please specify an amount and choice! Usage: `!coinflip <amount> <heads/tails>`",
            )

        # Normalize choice
        choice = choice.lower()
        if choice not in ["heads", "tails", "h", "t"]:
            return CoinflipResult(
                success=False,
                won=False,
                message="Please choose either `heads` or `tails`!",
            )

        if choice == "h":
            choice = "heads"
        elif choice == "t":
            choice = "tails"

        if amount < COINFLIP_MIN_BET:
            return CoinflipResult(
                success=False,
                won=False,
                message=f"Minimum bet for coinflip is {COINFLIP_MIN_BET} noodle stars!",
            )

        if current_stars <= 0:
            return CoinflipResult(
                success=False,
                won=False,
                message=f"You need at least 1 noodle star to play! Current balance: **{current_stars}** stars",
            )

        if amount > current_stars:
            return CoinflipResult(
                success=False,
                won=False,
                message=f"You only have **{current_stars}** stars! You can't bet **{amount}** stars!",
            )

        # Flip the coin
        result = random.choice(["heads", "tails"])

        # Deduct the bet immediately
        deducted_balance = current_stars - amount

        if result == choice:
            winnings = int(amount * COINFLIP_WIN_MULTIPLIER)
            new_balance = deducted_balance + winnings
            self.repo.update_user_stars(
                user_id, username, new_balance, reason="gambling:coinflip_win"
            )

            return CoinflipResult(
                success=True,
                won=True,
                message="WIN",
                result=result,
                amount_changed=winnings - amount,
                new_balance=new_balance,
            )
        else:
            new_balance = deducted_balance
            self.repo.update_user_stars(
                user_id, username, new_balance, reason="gambling:coinflip_loss"
            )

            return CoinflipResult(
                success=True,
                won=False,
                message="LOSE",
                result=result,
                amount_changed=-amount,
                new_balance=new_balance,
            )

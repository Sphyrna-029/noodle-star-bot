"""Economy use-cases for balance management."""

from datetime import datetime, timedelta
from typing import List, Tuple

from cogs.economy.constants import (
    BANKING_DEPOSIT_COOLDOWN_MINUTES,
    BANKING_WITHDRAW_COOLDOWN_MINUTES,
)
from database.repository import UserRepository
from utils.formatters import format_time_remaining
from .dto import BalanceResult


class EconomyUseCases:
    """Handles all economy-related business logic."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def get_balance(self, user_id: int, username: str) -> BalanceResult:
        """Get user's current balance."""
        user = self.repo.get_user(user_id, username)
        return BalanceResult(
            success=True,
            message="Balance retrieved",
            wallet=user.stars,
            bank=user.bank,
        )

    def add_stars(self, user_id: int, username: str, amount: int) -> BalanceResult:
        """
        Add stars to user's wallet.

        Args:
            user_id: Discord user ID
            username: Discord username
            amount: Amount to add (can be negative)

        Returns:
            BalanceResult with new balance
        """
        current = self.repo.get_user_stars(user_id, username)
        new_balance = max(0, current + amount)
        self.repo.update_user_stars(user_id, username, new_balance)
        self.repo.update_username(user_id, username)

        return BalanceResult(
            success=True,
            message=f"Added {amount} stars",
            wallet=new_balance,
            bank=self.repo.get_user_bank(user_id),
        )

    def remove_stars(self, user_id: int, username: str, amount: int) -> BalanceResult:
        """
        Remove stars from user's wallet.

        Args:
            user_id: Discord user ID
            username: Discord username
            amount: Amount to remove

        Returns:
            BalanceResult with new balance
        """
        return self.add_stars(user_id, username, -amount)

    def deposit(self, user_id: int, username: str, amount: int | str) -> BalanceResult:
        """
        Deposit stars from wallet to bank.

        Args:
            user_id: Discord user ID
            username: Discord username
            amount: Amount to deposit, or "all"

        Returns:
            BalanceResult with success/failure and new balances
        """
        current_stars = self.repo.get_user_stars(user_id, username)
        current_bank = self.repo.get_user_bank(user_id)

        # Check deposit cooldown
        last_deposit = self.repo.get_last_deposit(user_id)
        if last_deposit is not None:
            time_since = datetime.now() - last_deposit
            cooldown = timedelta(minutes=BANKING_DEPOSIT_COOLDOWN_MINUTES)
            if time_since < cooldown:
                remaining = cooldown - time_since
                return BalanceResult(
                    success=False,
                    message=f"You must wait **{format_time_remaining(remaining)}** before depositing again!",
                    wallet=current_stars,
                    bank=current_bank,
                )

        # Handle "all" keyword
        if isinstance(amount, str) and amount.lower() == "all":
            if current_stars <= 0:
                return BalanceResult(
                    success=False,
                    message="You don't have any stars to deposit!",
                    wallet=current_stars,
                    bank=current_bank,
                )
            deposit_amount = current_stars
        else:
            try:
                deposit_amount = int(amount)
            except (ValueError, TypeError):
                return BalanceResult(
                    success=False,
                    message='Please enter a valid number or "all"!',
                    wallet=current_stars,
                    bank=current_bank,
                )

            if deposit_amount <= 0:
                return BalanceResult(
                    success=False,
                    message="You must deposit at least 1 star!",
                    wallet=current_stars,
                    bank=current_bank,
                )

            if deposit_amount > current_stars:
                return BalanceResult(
                    success=False,
                    message=f"You only have **{current_stars}** stars in your wallet!",
                    wallet=current_stars,
                    bank=current_bank,
                )

        # Update balances
        new_stars = current_stars - deposit_amount
        new_bank = current_bank + deposit_amount

        self.repo.update_user_stars(user_id, username, new_stars)
        self.repo.update_user_bank(user_id, username, new_bank)
        self.repo.update_last_deposit(user_id)

        return BalanceResult(
            success=True,
            message=f"Deposited **{deposit_amount}** stars into the bank!",
            wallet=new_stars,
            bank=new_bank,
        )

    def withdraw(self, user_id: int, username: str, amount: int | str) -> BalanceResult:
        """
        Withdraw stars from bank to wallet.

        Args:
            user_id: Discord user ID
            username: Discord username
            amount: Amount to withdraw, or "all"

        Returns:
            BalanceResult with success/failure and new balances
        """
        current_stars = self.repo.get_user_stars(user_id, username)
        current_bank = self.repo.get_user_bank(user_id)

        # Check withdraw cooldown
        last_withdraw = self.repo.get_last_withdraw(user_id)
        if last_withdraw is not None:
            time_since = datetime.now() - last_withdraw
            cooldown = timedelta(minutes=BANKING_WITHDRAW_COOLDOWN_MINUTES)
            if time_since < cooldown:
                remaining = cooldown - time_since
                return BalanceResult(
                    success=False,
                    message=f"You must wait **{format_time_remaining(remaining)}** before withdrawing again!",
                    wallet=current_stars,
                    bank=current_bank,
                )

        # Handle "all" keyword
        if isinstance(amount, str) and amount.lower() == "all":
            if current_bank <= 0:
                return BalanceResult(
                    success=False,
                    message="You don't have any stars in the bank!",
                    wallet=current_stars,
                    bank=current_bank,
                )
            withdraw_amount = current_bank
        else:
            try:
                withdraw_amount = int(amount)
            except (ValueError, TypeError):
                return BalanceResult(
                    success=False,
                    message='Please enter a valid number or "all"!',
                    wallet=current_stars,
                    bank=current_bank,
                )

            if withdraw_amount <= 0:
                return BalanceResult(
                    success=False,
                    message="You must withdraw at least 1 star!",
                    wallet=current_stars,
                    bank=current_bank,
                )

            if withdraw_amount > current_bank:
                return BalanceResult(
                    success=False,
                    message=f"You only have **{current_bank}** stars in the bank!",
                    wallet=current_stars,
                    bank=current_bank,
                )

        # Update balances
        new_stars = current_stars + withdraw_amount
        new_bank = current_bank - withdraw_amount

        self.repo.update_user_stars(user_id, username, new_stars)
        self.repo.update_user_bank(user_id, username, new_bank)
        self.repo.update_last_withdraw(user_id)

        return BalanceResult(
            success=True,
            message=f"Withdrew **{withdraw_amount}** stars from the bank!",
            wallet=new_stars,
            bank=new_bank,
        )

    def get_leaderboard(
        self, limit: int = 10, ascending: bool = False
    ) -> List[Tuple[str, int]]:
        """
        Get leaderboard of users.

        Args:
            limit: Maximum number of users
            ascending: If True, return lowest first

        Returns:
            List of (username, stars) tuples
        """
        return self.repo.get_leaderboard(limit, ascending)

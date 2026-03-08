"""Economy use-cases for balance management."""

from datetime import datetime, timedelta
from typing import List, Tuple

from cogs.economy.constants import (
    ACHIEVEMENT_DEFS,
    BANKING_DEPOSIT_COOLDOWN_MINUTES,
    BANKING_WITHDRAW_COOLDOWN_MINUTES,
)
from cogs.farming.constants import MAX_FARM_LEVEL, MAX_PLOTS
from database.repository import UserRepository
from utils.formatters import format_time_remaining
from ..dto import AchievementStatus, BalanceResult, EconomyStats, ProfileResult


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

    def get_profile(self, user_id: int, username: str) -> ProfileResult:
        """Get user profile information, including simple achievements."""
        user = self.repo.get_user(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        farm_plots = self.repo.get_farm_plots(user_id)
        progress = self.repo.get_achievement_progress(user_id)
        progress["gambling_stars_lost"] = self.get_user_gambling_stars_lost(user_id)
        progress["gambling_stars_won"] = self.get_user_gambling_stars_won(user_id)
        progress["farming_harvest_stars_earned"] = self.get_user_farming_harvest_stars_earned(
            user_id
        )
        unlocked_keys = set(self.repo.get_unlocked_achievements(user_id).keys())
        achievements: list[AchievementStatus] = []
        newly_unlocked: list[AchievementStatus] = []

        for definition in ACHIEVEMENT_DEFS:
            key = definition["key"]
            progress_key = definition.get("progress_key")
            target = definition.get("target")

            # Evaluate unlock condition
            condition_met = False
            if key == "first_star":
                condition_met = user.total_stars >= 1
            elif key == "baby_saver":
                condition_met = user.bank >= 1000
            elif key == "small_saver":
                condition_met = user.bank >= 5000
            elif key == "medium_saver":
                condition_met = user.bank >= 10000
            elif key == "miner_upgrade":
                condition_met = inventory.get("mine_level", 1) >= 5
            elif key == "prepared_miner":
                condition_met = (
                    inventory.get("helmet", 0) > 0
                    and inventory.get("sword", 0) > 0
                )
            elif key == "tool_owner":
                condition_met = (
                    inventory.get("gold_pickaxe", 0) > 0
                    or inventory.get("telescope", 0) > 0
                )
            elif key == "space_ready":
                condition_met = inventory.get("rocket_ship", 0) > 0
            elif key == "budding_farmer":
                condition_met = farm_plots >= 1
            elif key == "land_baron":
                condition_met = farm_plots >= MAX_PLOTS
            elif key == "master_farmer":
                condition_met = inventory.get("farm_level", 1) >= 5
            elif key == "grandmaster_farmer":
                condition_met = inventory.get("farm_level", 1) >= MAX_FARM_LEVEL
            elif progress_key and target is not None:
                condition_met = progress.get(progress_key, 0) >= int(target)

            is_unlocked = key in unlocked_keys
            unlocked_now = False
            if not is_unlocked and condition_met:
                unlocked_now = self.repo.unlock_achievement(user_id, key)
                if unlocked_now:
                    unlocked_keys.add(key)
                    is_unlocked = True

            achievement_status = AchievementStatus(
                key=key,
                name=definition["name"],
                emoji=definition["emoji"],
                description=definition["description"],
                unlocked=is_unlocked,
                progress_current=progress.get(progress_key, 0)
                if progress_key
                else None,
                progress_target=int(target) if target is not None else None,
            )
            achievements.append(achievement_status)
            if unlocked_now:
                newly_unlocked.append(achievement_status)

        return ProfileResult(
            success=True,
            message="Profile retrieved",
            wallet=user.stars,
            bank=user.bank,
            achievements=achievements,
            newly_unlocked=newly_unlocked,
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

    def get_economy_stats(self):
        """Get total stats of the economy."""
        try:
            total_stars = self.repo.get_all_total_stars()
        except:
            total_stars = 0

        if total_stars == 0:
            return EconomyStats(
                success=False,
                message="The economy has no stars in circulation!",
                total_stars=total_stars,
            )
        else:
            return EconomyStats(
                success=True,
                message="The economy has a total of **{total_stars}** stars in circulation!",
                total_stars=total_stars,
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

    def get_monthly_stars_earned(self, year: int, month: int) -> int:
        """Get stars earned for a specific month."""
        return self.repo.get_monthly_stars_earned(year, month)

    def get_monthly_stars_lost(self, year: int, month: int) -> int:
        """Get stars lost for a specific month."""
        return self.repo.get_monthly_stars_lost(year, month)

    def get_user_gambling_stars_lost(self, user_id: int) -> int:
        """Get total stars a user has lost from gambling actions."""
        return self.repo.get_user_stars_lost_by_source(user_id, "gambling")

    def get_user_gambling_stars_won(self, user_id: int) -> int:
        """Get total stars a user has won from gambling actions."""
        return self.repo.get_user_stars_earned_by_source(user_id, "gambling")

    def get_user_farming_harvest_stars_earned(self, user_id: int) -> int:
        """Get total stars a user has earned from farming harvests."""
        return self.repo.get_user_stars_earned_by_source_reason(
            user_id, "farming", "harvest"
        )

    def get_user_daily_star_activity(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> list[tuple[str, int, int, int, int]]:
        """Get per-day star activity for a user in a time range."""
        return self.repo.get_user_daily_star_activity(user_id, start, end)

    def get_last_month_stars_earned(self) -> tuple[int, int, int]:
        """Get stars earned for the previous calendar month."""
        now = datetime.now()
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1

        earned = self.repo.get_monthly_stars_earned(year, month)
        return earned, year, month

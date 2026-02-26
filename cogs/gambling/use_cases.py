"""Gambling use-cases for games of chance."""

import random
from datetime import datetime, timedelta
from math import ceil
from typing import Optional

from cogs.gambling.constants import (
    COINFLIP_MIN_BET,
    COINFLIP_WIN_MULTIPLIER,
    DUEL_DICE_SIDES,
    DUEL_STAMINA_BASE_COST,
    DUEL_STAMINA_COST_PER_50,
    DUEL_STAMINA_MAX,
    DUEL_STAMINA_REGEN_AMOUNT_DIVISOR,
    DUEL_STAMINA_REGEN_BASE_MINUTES,
    DUEL_STAMINA_REGEN_MAX_EXTRA_MINUTES,
    GAMBLE_DICE_SIDES,
    GAMBLE_MULTIPLIER_CDF,
    GAMBLE_WIN_TARGET,
)
from database.repository import UserRepository
from .dto import CoinflipResult, DuelResult, GambleResult


class GamblingUseCases:
    """Handles all gambling-related business logic."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def _calculate_duel_stamina_cost(self, amount: int) -> int:
        return DUEL_STAMINA_BASE_COST + ceil(amount / DUEL_STAMINA_COST_PER_50)

    def _duel_stamina_regen_interval_minutes(self, last_duel_amount: int) -> int:
        extra = min(
            DUEL_STAMINA_REGEN_MAX_EXTRA_MINUTES,
            last_duel_amount // DUEL_STAMINA_REGEN_AMOUNT_DIVISOR,
        )
        return DUEL_STAMINA_REGEN_BASE_MINUTES + extra

    def _apply_duel_stamina_regen(self, stamina_state: dict, now: datetime) -> dict:
        last_reset = stamina_state.get("stamina_last_reset")
        if last_reset is None or last_reset.date() != now.date():
            stamina_state["stamina"] = DUEL_STAMINA_MAX
            stamina_state["stamina_last_reset"] = now
            stamina_state["stamina_last_updated"] = now

        stamina = stamina_state.get("stamina", 0)
        if stamina >= DUEL_STAMINA_MAX:
            stamina_state["stamina"] = DUEL_STAMINA_MAX
            return stamina_state

        last_updated = stamina_state.get("stamina_last_updated") or now
        interval_minutes = self._duel_stamina_regen_interval_minutes(
            stamina_state.get("last_duel_amount", 0)
        )
        elapsed_intervals = int(
            (now - last_updated).total_seconds() // (interval_minutes * 60)
        )
        if elapsed_intervals > 0:
            regen = min(elapsed_intervals, DUEL_STAMINA_MAX - stamina)
            stamina += regen
            last_updated = last_updated + timedelta(minutes=regen * interval_minutes)

        stamina_state["stamina"] = stamina
        stamina_state["stamina_last_updated"] = last_updated
        return stamina_state

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

    def gamble(self, user_id: int, username: str, amount: int) -> GambleResult:
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

        # Validation
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

        # Select multiplier and roll
        multiplier = self._select_multiplier()
        roll = random.randint(1, GAMBLE_DICE_SIDES)

        # Deduct the bet immediately (consistent behavior)
        deducted_balance = current_stars - amount

        # Check if won
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

    def coinflip(
        self, user_id: int, username: str, amount: int, choice: str
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
            self.repo.update_user_stars(user_id, username, new_balance)

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
            self.repo.update_user_stars(user_id, username, new_balance)

            return CoinflipResult(
                success=True,
                won=False,
                message="LOSE",
                result=result,
                amount_changed=-amount,
                new_balance=new_balance,
            )

    def duel(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        amount: int,
    ) -> DuelResult:
        """
        Execute a duel between two players.

        Args:
            challenger_id: Challenger's Discord user ID
            challenger_name: Challenger's username
            opponent_id: Opponent's Discord user ID
            opponent_name: Opponent's username
            amount: Amount to bet

        Returns:
            DuelResult with outcome
        """
        # Validation
        if opponent_id is None or amount is None:
            return DuelResult(
                success=False,
                message="Please specify an opponent and amount! Usage: `!duel @user <amount>`",
            )

        if opponent_id == challenger_id:
            return DuelResult(
                success=False,
                message="You can't duel yourself!",
            )

        if amount <= 0:
            return DuelResult(
                success=False,
                message="You must bet at least 1 noodle star!",
            )

        # Get both users' stars
        challenger_stars = self.repo.get_user_stars(challenger_id, challenger_name)
        opponent_stars = self.repo.get_user_stars(opponent_id, opponent_name)

        # Check challenger balance
        if challenger_stars <= 0:
            return DuelResult(
                success=False,
                message=f"You need at least 1 noodle star to duel! Current balance: **{challenger_stars}** stars",
            )

        if amount > challenger_stars:
            return DuelResult(
                success=False,
                message=f"You only have **{challenger_stars}** stars! You can't bet **{amount}** stars!",
            )

        # Check opponent balance
        if opponent_stars <= 0:
            return DuelResult(
                success=False,
                message=f"Opponent doesn't have any noodle stars to duel with! Their balance: **{opponent_stars}** stars",
            )

        if amount > opponent_stars:
            return DuelResult(
                success=False,
                message=f"Opponent only has **{opponent_stars}** stars! They can't match a bet of **{amount}** stars!",
            )

        now = datetime.now()
        stamina_state = self.repo.get_duel_stamina_state(challenger_id)
        stamina_state = self._apply_duel_stamina_regen(stamina_state, now)

        stamina_cost = self._calculate_duel_stamina_cost(amount)
        stamina_before = stamina_state["stamina"]

        if stamina_before < stamina_cost:
            return DuelResult(
                success=False,
                message=(
                    "You don't have enough stamina to duel! "
                    f"Required: **{stamina_cost}**, available: **{stamina_before}**."
                ),
                stamina_cost=stamina_cost,
                challenger_stamina_before=stamina_before,
                challenger_stamina_after=stamina_before,
            )

        stamina_after = stamina_before - stamina_cost
        stamina_state["stamina"] = stamina_after
        stamina_state["stamina_last_updated"] = now
        stamina_state["last_duel_amount"] = amount
        stamina_state["last_duel_at"] = now
        if stamina_state.get("stamina_last_reset") is None:
            stamina_state["stamina_last_reset"] = now

        self.repo.update_duel_stamina_state(
            challenger_id,
            stamina=stamina_state["stamina"],
            stamina_last_updated=stamina_state["stamina_last_updated"],
            stamina_last_reset=stamina_state["stamina_last_reset"],
            last_duel_amount=stamina_state["last_duel_amount"],
            last_duel_at=stamina_state["last_duel_at"],
        )

        # Roll the dice
        challenger_roll = random.randint(1, DUEL_DICE_SIDES)
        opponent_roll = random.randint(1, DUEL_DICE_SIDES)

        # Handle ties by re-rolling
        while challenger_roll == opponent_roll:
            challenger_roll = random.randint(1, DUEL_DICE_SIDES)
            opponent_roll = random.randint(1, DUEL_DICE_SIDES)

        # Determine winner
        if challenger_roll > opponent_roll:
            winner_id = challenger_id
            new_challenger_stars = challenger_stars + amount
            new_opponent_stars = opponent_stars - amount
        else:
            winner_id = opponent_id
            new_challenger_stars = challenger_stars - amount
            new_opponent_stars = opponent_stars + amount

        # Update balances
        self.repo.update_user_stars(
            challenger_id, challenger_name, new_challenger_stars
        )
        self.repo.update_user_stars(opponent_id, opponent_name, new_opponent_stars)

        return DuelResult(
            success=True,
            message="DUEL_COMPLETE",
            challenger_roll=challenger_roll,
            opponent_roll=opponent_roll,
            winner_id=winner_id,
            amount=amount,
            challenger_new_balance=new_challenger_stars,
            opponent_new_balance=new_opponent_stars,
            stamina_cost=stamina_cost,
            challenger_stamina_before=stamina_before,
            challenger_stamina_after=stamina_after,
        )

import random
from datetime import datetime, timedelta
from math import ceil
from typing import Optional

from cogs.gambling.constants import (
    PICKPOCKET_DICE_SIDES,
    PICKPOCKET_STAMINA_BASE_COST,
    PICKPOCKET_STAMINA_COST_PER_50,
    PICKPOCKET_STAMINA_MAX,
    PICKPOCKET_STAMINA_REGEN_AMOUNT_DIVISOR,
    PICKPOCKET_STAMINA_REGEN_BASE_MINUTES,
    PICKPOCKET_STAMINA_REGEN_MAX_EXTRA_MINUTES,
)
from cogs.gambling.dto import PickpocketResult
from .base import BaseGamblingUseCase


class PickpocketUseCase(BaseGamblingUseCase):
    """Handles the pickpocket game logic (D20 dice roll)."""

    def _calculate_stamina_cost(self, amount: int) -> int:
        return PICKPOCKET_STAMINA_BASE_COST + ceil(amount / PICKPOCKET_STAMINA_COST_PER_50)

    def _stamina_regen_interval_minutes(self, last_amount: int) -> int:
        extra = min(
            PICKPOCKET_STAMINA_REGEN_MAX_EXTRA_MINUTES,
            last_amount // PICKPOCKET_STAMINA_REGEN_AMOUNT_DIVISOR,
        )
        return PICKPOCKET_STAMINA_REGEN_BASE_MINUTES + extra

    def _apply_stamina_regen(self, stamina_state: dict, now: datetime) -> dict:
        last_reset = stamina_state.get("stamina_last_reset")
        if last_reset is None or last_reset.date() != now.date():
            stamina_state["stamina"] = PICKPOCKET_STAMINA_MAX
            stamina_state["stamina_last_reset"] = now
            stamina_state["stamina_last_updated"] = now

        stamina = stamina_state.get("stamina", 0)
        if stamina >= PICKPOCKET_STAMINA_MAX:
            stamina_state["stamina"] = PICKPOCKET_STAMINA_MAX
            return stamina_state

        last_updated = stamina_state.get("stamina_last_updated") or now
        interval_minutes = self._stamina_regen_interval_minutes(
            stamina_state.get("last_duel_amount", 0)
        )
        elapsed_intervals = int(
            (now - last_updated).total_seconds() // (interval_minutes * 60)
        )
        if elapsed_intervals > 0:
            regen = min(elapsed_intervals, PICKPOCKET_STAMINA_MAX - stamina)
            stamina += regen
            last_updated = last_updated + timedelta(minutes=regen * interval_minutes)

        stamina_state["stamina"] = stamina
        stamina_state["stamina_last_updated"] = last_updated
        return stamina_state

    def execute(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        amount: Optional[int],
    ) -> PickpocketResult:
        """Execute a pickpocket attempt between two players."""
        if opponent_id is None or amount is None:
            return PickpocketResult(
                success=False,
                message="Please specify a target and amount! Usage: `!pickpocket @user <amount>`",
            )

        if opponent_id == challenger_id:
            return PickpocketResult(
                success=False,
                message="You can't pickpocket yourself!",
            )

        if amount <= 0:
            return PickpocketResult(
                success=False,
                message="You must bet at least 1 noodle star!",
            )

        challenger_stars = self.repo.get_user_stars(challenger_id, challenger_name)
        opponent_stars = self.repo.get_user_stars(opponent_id, opponent_name)

        if challenger_stars <= 0:
            return PickpocketResult(
                success=False,
                message=f"You need at least 1 noodle star! Current balance: **{challenger_stars}** stars",
            )

        if amount > challenger_stars:
            return PickpocketResult(
                success=False,
                message=f"You only have **{challenger_stars}** stars! You can't bet **{amount}** stars!",
            )

        if opponent_stars <= 0:
            return PickpocketResult(
                success=False,
                message=f"Your target doesn't have any noodle stars! Their balance: **{opponent_stars}** stars",
            )

        if amount > opponent_stars:
            return PickpocketResult(
                success=False,
                message=f"Your target only has **{opponent_stars}** stars! They can't cover a bet of **{amount}** stars!",
            )

        now = datetime.now()
        stamina_state = self.repo.get_duel_stamina_state(challenger_id)
        stamina_state = self._apply_stamina_regen(stamina_state, now)

        self.repo.update_duel_stamina_state(
            challenger_id,
            stamina=stamina_state["stamina"],
            stamina_last_updated=stamina_state.get("stamina_last_updated") or now,
            stamina_last_reset=stamina_state.get("stamina_last_reset") or now,
            last_duel_amount=stamina_state.get("last_duel_amount", 0),
            last_duel_at=stamina_state.get("last_duel_at"),
        )

        stamina_cost = self._calculate_stamina_cost(amount)
        stamina_before = stamina_state["stamina"]

        if stamina_before < stamina_cost:
            return PickpocketResult(
                success=False,
                message=(
                    "You don't have enough pickpocket stamina! "
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
        challenger_roll = random.randint(1, PICKPOCKET_DICE_SIDES)
        opponent_roll = random.randint(1, PICKPOCKET_DICE_SIDES)

        while challenger_roll == opponent_roll:
            challenger_roll = random.randint(1, PICKPOCKET_DICE_SIDES)
            opponent_roll = random.randint(1, PICKPOCKET_DICE_SIDES)

        if challenger_roll > opponent_roll:
            winner_id = challenger_id
            new_challenger_stars = challenger_stars + amount
            new_opponent_stars = opponent_stars - amount
        else:
            winner_id = opponent_id
            new_challenger_stars = challenger_stars - amount
            new_opponent_stars = opponent_stars + amount

        self.repo.update_user_stars(
            challenger_id,
            challenger_name,
            new_challenger_stars,
            reason="gambling:pickpocket_result",
        )
        self.repo.update_user_stars(
            opponent_id,
            opponent_name,
            new_opponent_stars,
            reason="gambling:pickpocket_result",
        )
        duel_wins = self.repo.increment_achievement_progress(winner_id, "duel_wins", 1)
        unlocked_achievement_keys: list[str] = []
        if duel_wins >= 1 and self.repo.unlock_achievement(winner_id, "duel_first_blood"):
            unlocked_achievement_keys.append("duel_first_blood")
        if duel_wins >= 50 and self.repo.unlock_achievement(winner_id, "duel_warlord"):
            unlocked_achievement_keys.append("duel_warlord")

        return PickpocketResult(
            success=True,
            message="PICKPOCKET_COMPLETE",
            challenger_roll=challenger_roll,
            opponent_roll=opponent_roll,
            winner_id=winner_id,
            amount=amount,
            challenger_new_balance=new_challenger_stars,
            opponent_new_balance=new_opponent_stars,
            stamina_cost=stamina_cost,
            challenger_stamina_before=stamina_before,
            challenger_stamina_after=stamina_after,
            unlocked_achievement_keys=unlocked_achievement_keys,
        )

import random
from datetime import datetime, timedelta
from typing import Optional

from cogs.gambling.constants import ROULETTE_CHAMBERS, ROULETTE_INVITE_TTL_HOURS
from cogs.gambling.dto import RouletteInviteResult, RoulettePvpResult
from .base import BaseGamblingUseCase


class RouletteUseCase(BaseGamblingUseCase):
    """Handles PvP Russian Roulette game logic."""

    def create_pvp_invite(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        amount: Optional[int],
        channel_id: int,
    ) -> RouletteInviteResult:
        """Create a PvP roulette invite with TTL."""
        if amount is None:
            return RouletteInviteResult(
                success=False,
                message="Usage: `!russian @user <amount>`",
            )

        if challenger_id == opponent_id:
            return RouletteInviteResult(
                success=False,
                message="You can't challenge yourself.",
            )

        if amount <= 0:
            return RouletteInviteResult(
                success=False,
                message="You must bet at least 1 noodle star!",
            )

        self.repo.delete_expired_roulette_invites(datetime.now())

        challenger_total = (
            self.repo.get_user_stars(challenger_id, challenger_name)
            + self.repo.get_user_bank(challenger_id)
        )
        if challenger_total < amount:
            return RouletteInviteResult(
                success=False,
                message=(
                    f"You need **{amount}** total stars (wallet + bank). "
                    f"Current total: **{challenger_total}**."
                ),
            )

        existing = self.repo.find_pending_roulette_invite_involving_user(challenger_id)
        if existing is not None:
            return RouletteInviteResult(
                success=False,
                message="You already have a pending roulette invite. Resolve it first.",
            )

        existing = self.repo.find_pending_roulette_invite_involving_user(opponent_id)
        if existing is not None:
            return RouletteInviteResult(
                success=False,
                message="That player already has a pending roulette invite.",
            )

        now = datetime.now()
        expires_at = now + timedelta(hours=ROULETTE_INVITE_TTL_HOURS)
        self.repo.create_roulette_invite(
            challenger_id=challenger_id,
            challenger_name=challenger_name,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            amount=amount,
            channel_id=channel_id,
            created_at=now,
            expires_at=expires_at,
        )

        return RouletteInviteResult(
            success=True,
            message="INVITE_CREATED",
            amount=amount,
            inviter_id=challenger_id,
            opponent_id=opponent_id,
            expires_at=expires_at.isoformat(),
        )

    def cancel_pvp_invite(
        self,
        user_id: int,
        challenger_id: Optional[int] = None,
    ) -> RouletteInviteResult:
        """Cancel a pending PvP invite involving the user."""
        self.repo.delete_expired_roulette_invites(datetime.now())
        invite = self.repo.find_pending_roulette_invite_involving_user(
            user_id=user_id,
            challenger_id=challenger_id,
        )
        if invite is None:
            return RouletteInviteResult(
                success=False,
                message="No matching pending roulette invite found.",
            )

        self.repo.delete_roulette_invite(invite["id"])
        return RouletteInviteResult(
            success=True,
            message="INVITE_CANCELLED",
            amount=invite["amount"],
            inviter_id=invite["challenger_id"],
            opponent_id=invite["opponent_id"],
            expires_at=invite["expires_at"],
        )

    def accept_pvp_invite(
        self,
        opponent_id: int,
        opponent_name: str,
        challenger_id: Optional[int] = None,
    ) -> RoulettePvpResult:
        """Accept a pending invite, run PvP roulette, and settle balances."""
        now = datetime.now()
        self.repo.delete_expired_roulette_invites(now)
        invite = self.repo.find_pending_roulette_invite_for_opponent(
            opponent_id=opponent_id,
            challenger_id=challenger_id,
        )
        if invite is None:
            return RoulettePvpResult(
                success=False,
                message="No pending roulette invite found for you.",
            )

        challenger_id = invite["challenger_id"]
        challenger_name = invite["challenger_name"]
        amount = invite["amount"]

        challenger_total = (
            self.repo.get_user_stars(challenger_id, challenger_name)
            + self.repo.get_user_bank(challenger_id)
        )
        opponent_total = (
            self.repo.get_user_stars(opponent_id, opponent_name)
            + self.repo.get_user_bank(opponent_id)
        )

        if challenger_total < amount:
            self.repo.delete_roulette_invite(invite["id"])
            return RoulettePvpResult(
                success=False,
                message=(
                    f"{challenger_name} no longer has enough total stars to cover **{amount}**. "
                    "Invite cancelled."
                ),
            )

        if opponent_total < amount:
            return RoulettePvpResult(
                success=False,
                message=(
                    f"You need **{amount}** total stars (wallet + bank). "
                    f"Current total: **{opponent_total}**."
                ),
            )

        bullet_chamber = random.randint(1, ROULETTE_CHAMBERS)
        trigger_log: list[int] = []
        loser_id = challenger_id
        winner_id = opponent_id

        for pull in range(1, ROULETTE_CHAMBERS + 1):
            shooter_id = challenger_id if pull % 2 == 1 else opponent_id
            trigger_log.append(shooter_id)
            if pull == bullet_chamber:
                loser_id = shooter_id
                winner_id = opponent_id if shooter_id == challenger_id else challenger_id
                break

        settle_result = self.repo.settle_roulette_pvp_bet(
            challenger_id=challenger_id,
            challenger_name=challenger_name,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            amount=amount,
            winner_id=winner_id,
        )
        if settle_result is None:
            return RoulettePvpResult(
                success=False,
                message="Could not settle roulette game (balance changed during acceptance).",
            )

        self.repo.delete_roulette_invite(invite["id"])
        return RoulettePvpResult(
            success=True,
            message="PVP_COMPLETE",
            winner_id=winner_id,
            loser_id=loser_id,
            amount=amount,
            bullet_chamber=bullet_chamber,
            trigger_log=trigger_log,
            challenger_wallet=settle_result["challenger_wallet"],
            challenger_bank=settle_result["challenger_bank"],
            opponent_wallet=settle_result["opponent_wallet"],
            opponent_bank=settle_result["opponent_bank"],
        )

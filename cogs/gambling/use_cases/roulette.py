import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from cogs.gambling.constants import (
    ROULETTE_CHAMBERS,
    ROULETTE_INVITE_TTL_HOURS,
    RUSSIAN_TURN_TIMEOUT_SECONDS,
)
from cogs.gambling.dto import RouletteInviteResult, RoulettePvpResult
from .base import BaseGamblingUseCase


@dataclass(slots=True)
class _ActivePvpGame:
    challenger_id: int
    challenger_name: str
    opponent_id: int
    opponent_name: str
    amount: int
    pot_amount: int
    channel_id: int
    bullet_chamber: int
    current_turn_user_id: int
    turn_deadline: datetime
    remaining_chambers: set[int] = field(
        default_factory=lambda: set(range(1, ROULETTE_CHAMBERS + 1))
    )
    trigger_log: list[tuple[int, int, bool]] = field(default_factory=list)
    timeout_task: Optional[asyncio.Task] = field(default=None, repr=False)


class RouletteUseCase(BaseGamblingUseCase):
    """Handles PvP Russian Roulette game logic."""

    def __init__(self, repository=None):
        super().__init__(repository)
        self._games_by_user: dict[int, _ActivePvpGame] = {}
        self._event_callback: Optional[
            Callable[[str, int, RoulettePvpResult], Awaitable[None]]
        ] = None

    def set_game_callback(
        self, callback: Callable[[str, int, RoulettePvpResult], Awaitable[None]]
    ) -> None:
        """Set callback for async game events (e.g. timeout losses)."""
        self._event_callback = callback

    def _set_active_game(self, game: _ActivePvpGame) -> None:
        self._games_by_user[game.challenger_id] = game
        self._games_by_user[game.opponent_id] = game

    def _clear_active_game(self, game: _ActivePvpGame) -> None:
        if game.timeout_task and not game.timeout_task.done():
            game.timeout_task.cancel()
        self._games_by_user.pop(game.challenger_id, None)
        self._games_by_user.pop(game.opponent_id, None)

    def _schedule_turn_timeout(self, game: _ActivePvpGame) -> None:
        if game.timeout_task and not game.timeout_task.done():
            game.timeout_task.cancel()
        game.turn_deadline = datetime.now() + timedelta(seconds=RUSSIAN_TURN_TIMEOUT_SECONDS)
        game.timeout_task = asyncio.create_task(
            self._handle_turn_timeout(game, game.current_turn_user_id, game.turn_deadline)
        )

    async def _handle_turn_timeout(
        self,
        game: _ActivePvpGame,
        expected_turn_user_id: int,
        expected_deadline: datetime,
    ) -> None:
        try:
            await asyncio.sleep(RUSSIAN_TURN_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return

        current_game = self._games_by_user.get(expected_turn_user_id)
        if current_game is not game:
            return
        if game.current_turn_user_id != expected_turn_user_id:
            return
        if game.turn_deadline != expected_deadline:
            return

        loser_id = expected_turn_user_id
        winner_id = game.opponent_id if loser_id == game.challenger_id else game.challenger_id

        settle_result = self.repo.payout_roulette_pvp_winner(
            challenger_id=game.challenger_id,
            challenger_name=game.challenger_name,
            opponent_id=game.opponent_id,
            opponent_name=game.opponent_name,
            winner_id=winner_id,
            pot_amount=game.pot_amount,
        )
        if settle_result is None:
            self._clear_active_game(game)
            if self._event_callback:
                try:
                    await self._event_callback(
                        "timeout_error",
                        game.channel_id,
                        RoulettePvpResult(
                            success=False,
                            message="Timeout occurred but payout failed.",
                            game_over=True,
                            loser_id=loser_id,
                            winner_id=winner_id,
                            amount=game.amount,
                        ),
                    )
                except Exception:
                    pass
            return

        result = RoulettePvpResult(
            success=True,
            message="TIMEOUT_LOSS",
            game_over=True,
            fired=False,
            winner_id=winner_id,
            loser_id=loser_id,
            amount=game.amount,
            next_turn_user_id=None,
            trigger_log=list(game.trigger_log),
            challenger_wallet=settle_result["challenger_wallet"],
            challenger_bank=settle_result["challenger_bank"],
            opponent_wallet=settle_result["opponent_wallet"],
            opponent_bank=settle_result["opponent_bank"],
        )
        channel_id = game.channel_id
        self._clear_active_game(game)
        if self._event_callback:
            try:
                await self._event_callback("timeout_loss", channel_id, result)
            except Exception:
                pass

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

        if challenger_id in self._games_by_user:
            return RouletteInviteResult(
                success=False,
                message="You're already in an active russian roulette game.",
            )
        if opponent_id in self._games_by_user:
            return RouletteInviteResult(
                success=False,
                message="That player is already in an active russian roulette game.",
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
        """Accept a pending invite and start a turn-based PvP roulette game."""
        if opponent_id in self._games_by_user:
            return RoulettePvpResult(
                success=False,
                message="You're already in an active russian roulette game.",
            )

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

        if challenger_id in self._games_by_user:
            self.repo.delete_roulette_invite(invite["id"])
            return RoulettePvpResult(
                success=False,
                message=f"{challenger_name} is already in another active game. Invite cancelled.",
            )

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

        game = _ActivePvpGame(
            challenger_id=challenger_id,
            challenger_name=challenger_name,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            amount=amount,
            pot_amount=amount * 2,
            channel_id=invite["channel_id"],
            bullet_chamber=random.randint(1, ROULETTE_CHAMBERS),
            current_turn_user_id=challenger_id,
            turn_deadline=datetime.now() + timedelta(seconds=RUSSIAN_TURN_TIMEOUT_SECONDS),
        )
        lock_result = self.repo.lock_roulette_pvp_bet(
            challenger_id=challenger_id,
            challenger_name=challenger_name,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            amount=amount,
        )
        if lock_result is None:
            self.repo.delete_roulette_invite(invite["id"])
            return RoulettePvpResult(
                success=False,
                message="Could not lock both stakes. Invite cancelled.",
            )
        self._set_active_game(game)
        self._schedule_turn_timeout(game)
        self.repo.delete_roulette_invite(invite["id"])

        return RoulettePvpResult(
            success=True,
            message="PVP_STARTED",
            game_over=False,
            amount=amount,
            next_turn_user_id=challenger_id,
        )

    def fire_pvp_turn(
        self,
        user_id: int,
        username: str,
        chamber_choice: int,
    ) -> RoulettePvpResult:
        """Play one turn by selecting a chamber number to fire."""
        game = self._games_by_user.get(user_id)
        if game is None:
            return RoulettePvpResult(
                success=False,
                message="You're not in an active russian roulette game.",
            )

        if user_id != game.current_turn_user_id:
            return RoulettePvpResult(
                success=False,
                message="It's not your turn.",
                next_turn_user_id=game.current_turn_user_id,
            )

        if chamber_choice < 1 or chamber_choice > ROULETTE_CHAMBERS:
            return RoulettePvpResult(
                success=False,
                message=f"Pick a chamber between 1 and {ROULETTE_CHAMBERS}.",
            )

        if chamber_choice not in game.remaining_chambers:
            return RoulettePvpResult(
                success=False,
                message=f"Chamber **{chamber_choice}** is already used. Pick a remaining one.",
            )

        game.remaining_chambers.remove(chamber_choice)
        fired = chamber_choice == game.bullet_chamber
        game.trigger_log.append((user_id, chamber_choice, fired))

        if fired:
            loser_id = user_id
            winner_id = game.opponent_id if user_id == game.challenger_id else game.challenger_id

            settle_result = self.repo.payout_roulette_pvp_winner(
                challenger_id=game.challenger_id,
                challenger_name=game.challenger_name,
                opponent_id=game.opponent_id,
                opponent_name=game.opponent_name,
                winner_id=winner_id,
                pot_amount=game.pot_amount,
            )
            if settle_result is None:
                self._clear_active_game(game)
                return RoulettePvpResult(
                    success=False,
                    message="Could not settle roulette game (balance changed mid-game).",
                )

            self._clear_active_game(game)
            return RoulettePvpResult(
                success=True,
                message="PVP_COMPLETE",
                game_over=True,
                fired=True,
                winner_id=winner_id,
                loser_id=loser_id,
                amount=game.amount,
                bullet_chamber=game.bullet_chamber,
                selected_chamber=chamber_choice,
                trigger_log=list(game.trigger_log),
                challenger_wallet=settle_result["challenger_wallet"],
                challenger_bank=settle_result["challenger_bank"],
                opponent_wallet=settle_result["opponent_wallet"],
                opponent_bank=settle_result["opponent_bank"],
            )

        next_turn = game.opponent_id if user_id == game.challenger_id else game.challenger_id
        game.current_turn_user_id = next_turn
        self._schedule_turn_timeout(game)
        return RoulettePvpResult(
            success=True,
            message="TURN_SAFE",
            game_over=False,
            fired=False,
            amount=game.amount,
            selected_chamber=chamber_choice,
            next_turn_user_id=next_turn,
            trigger_log=list(game.trigger_log),
        )

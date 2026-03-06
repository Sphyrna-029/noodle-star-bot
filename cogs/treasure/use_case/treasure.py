"""Treasure chest lock-picking use cases."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Callable, Optional

from cogs.treasure.constants import (
    CHEST_ANNOUNCEMENT,
    CHEST_LIFETIME,
    FAIL_MESSAGE,
    LOCK_ATTEMPTS,
    LOCK_INSTRUCTIONS,
    LOCK_OWNER_TIMEOUT,
    LOCK_PIN_COUNT,
    LOCK_PIN_MAX,
    LOCK_PIN_MIN,
    SUCCESS_MESSAGE,
    TIMEOUT_MESSAGE,
    TREASURE_REWARD_MAX,
    TREASURE_REWARD_MIN,
)
from cogs.treasure.dto import (
    ChestState,
    PickResult,
    SpawnResult,
    StartPickResult,
    StatusResult,
    TreasureChest,
)
from database.repository import UserRepository


class TreasureUseCases:
    """Handles treasure chest spawning and lock-picking logic."""

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repo = repository or UserRepository()
        self._chest: Optional[TreasureChest] = None
        self._expire_task: Optional[asyncio.Task] = None
        self._owner_task: Optional[asyncio.Task] = None
        self._event_callback: Optional[Callable] = None

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def set_event_callback(self, callback: Callable) -> None:
        """Set a callback for chest events (expired, owner_timeout, opened)."""
        self._event_callback = callback

    def spawn_chest(self, channel_id: int, force: bool = False) -> SpawnResult:
        """Spawn a new treasure chest in a channel."""
        if self._chest and not force:
            if self._chest.state in (ChestState.AVAILABLE, ChestState.LOCKED):
                return SpawnResult(False, "A chest is already active.", self._chest)

        self._cancel_tasks()

        now = datetime.now()
        reward = random.randint(TREASURE_REWARD_MIN, TREASURE_REWARD_MAX)
        expires_at = now + CHEST_LIFETIME if CHEST_LIFETIME else None

        self._chest = TreasureChest(
            channel_id=channel_id,
            state=ChestState.AVAILABLE,
            reward=reward,
            spawned_at=now,
            expires_at=expires_at,
        )

        if expires_at is not None:
            self._expire_task = asyncio.create_task(self._expire_after(CHEST_LIFETIME))

        return SpawnResult(True, CHEST_ANNOUNCEMENT, self._chest)

    def start_pick(self, user_id: int, channel_id: int) -> StartPickResult:
        """Start a lock-picking session for a user."""
        chest = self._chest
        if chest is None or chest.state == ChestState.IDLE:
            return StartPickResult(False, "There is no active chest right now.", None)

        if chest.channel_id != channel_id:
            return StartPickResult(False, "The chest is in a different channel.", chest)

        if chest.state == ChestState.LOCKED and chest.owner_id == user_id:
            return StartPickResult(
                True,
                LOCK_INSTRUCTIONS.format(
                    pins=LOCK_PIN_COUNT,
                    min_pin=LOCK_PIN_MIN,
                    max_pin=LOCK_PIN_MAX,
                    attempts=chest.attempts_left,
                ),
                chest,
            )

        if chest.state == ChestState.LOCKED and chest.owner_id != user_id:
            if self._owner_lock_expired(chest):
                self._reset_lock(reason="timeout")
            else:
                return StartPickResult(
                    False,
                    "Someone else is picking the lock right now. Try again soon.",
                    chest,
                )

        chest.state = ChestState.LOCKED
        chest.owner_id = user_id
        chest.combo = self._generate_combo()
        chest.attempts_left = LOCK_ATTEMPTS
        chest.owner_expires_at = datetime.now() + LOCK_OWNER_TIMEOUT

        self._cancel_owner_task()
        self._owner_task = asyncio.create_task(self._owner_timeout())

        return StartPickResult(
            True,
            LOCK_INSTRUCTIONS.format(
                pins=LOCK_PIN_COUNT,
                min_pin=LOCK_PIN_MIN,
                max_pin=LOCK_PIN_MAX,
                attempts=LOCK_ATTEMPTS,
            ),
            chest,
        )

    def make_guess(
        self,
        user_id: int,
        username: str,
        channel_id: int,
        guess: list[int],
    ) -> PickResult:
        """Submit a lock-picking guess."""
        chest = self._chest
        if chest is None or chest.state == ChestState.IDLE:
            return PickResult(False, "There is no active chest right now.")

        if chest.channel_id != channel_id:
            return PickResult(False, "The chest is in a different channel.")

        if chest.state != ChestState.LOCKED:
            return PickResult(False, "The chest isn't locked right now. Use `!pick start`.")

        if chest.owner_id != user_id:
            return PickResult(False, "You don't have the lock. Use `!pick start` first.")

        if self._owner_lock_expired(chest):
            self._reset_lock(reason="timeout")
            return PickResult(False, TIMEOUT_MESSAGE)

        if len(guess) != LOCK_PIN_COUNT:
            return PickResult(
                False,
                f"Enter **{LOCK_PIN_COUNT}** numbers between {LOCK_PIN_MIN}-{LOCK_PIN_MAX}.",
                attempts_left=chest.attempts_left,
            )

        for pin in guess:
            if pin < LOCK_PIN_MIN or pin > LOCK_PIN_MAX:
                return PickResult(
                    False,
                    f"Each number must be between {LOCK_PIN_MIN}-{LOCK_PIN_MAX}.",
                    attempts_left=chest.attempts_left,
                )

        exact, misplaced = self._compute_feedback(chest.combo, guess)
        chest.attempts_left -= 1

        if exact == LOCK_PIN_COUNT:
            reward = chest.reward
            current = self.repo.get_user_stars(user_id, username)
            new_balance = current + reward
            self.repo.update_user_stars(user_id, username, new_balance)
            self.repo.update_username(user_id, username)

            message = SUCCESS_MESSAGE.format(mention=f"<@{user_id}>", reward=reward)
            self._mark_opened()

            return PickResult(
                True,
                message,
                opened=True,
                exact=exact,
                misplaced=misplaced,
                attempts_left=chest.attempts_left,
                reward=reward,
                new_balance=new_balance,
            )

        if chest.attempts_left <= 0:
            self._reset_lock(reason="failed")
            return PickResult(
                True,
                "❌ The lock jammed after too many attempts. The chest resets for others.",
                opened=False,
                exact=exact,
                misplaced=misplaced,
                attempts_left=0,
            )

        return PickResult(
            True,
            FAIL_MESSAGE.format(
                exact=exact,
                misplaced=misplaced,
                attempts_left=chest.attempts_left,
            ),
            opened=False,
            exact=exact,
            misplaced=misplaced,
            attempts_left=chest.attempts_left,
        )

    def status(self) -> StatusResult:
        """Get the current chest status."""
        chest = self._chest
        if chest is None or chest.state == ChestState.IDLE:
            return StatusResult(False, "There is no active chest right now.", None)

        if chest.state == ChestState.AVAILABLE:
            return StatusResult(True, "A chest is available to pick.", chest)

        if chest.state == ChestState.LOCKED:
            return StatusResult(
                True,
                f"The chest is being picked by <@{chest.owner_id}>.",
                chest,
            )

        return StatusResult(True, f"Chest status: {chest.state.value}.", chest)

    def end_chest(self) -> StatusResult:
        """Force-remove the current chest."""
        if self._chest is None or self._chest.state == ChestState.IDLE:
            return StatusResult(False, "There is no active chest to end.", None)

        self._cleanup_chest()
        return StatusResult(True, "Chest ended.", None)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _generate_combo(self) -> tuple[int, ...]:
        return tuple(
            random.randint(LOCK_PIN_MIN, LOCK_PIN_MAX) for _ in range(LOCK_PIN_COUNT)
        )

    @staticmethod
    def _compute_feedback(combo: tuple[int, ...], guess: list[int]) -> tuple[int, int]:
        exact = 0
        combo_counts = {}
        guess_counts = {}

        for i, value in enumerate(guess):
            if value == combo[i]:
                exact += 1
            else:
                combo_counts[combo[i]] = combo_counts.get(combo[i], 0) + 1
                guess_counts[value] = guess_counts.get(value, 0) + 1

        misplaced = 0
        for value, count in guess_counts.items():
            misplaced += min(count, combo_counts.get(value, 0))

        return exact, misplaced

    def _owner_lock_expired(self, chest: TreasureChest) -> bool:
        if chest.owner_expires_at is None:
            return False
        return datetime.now() >= chest.owner_expires_at

    def _reset_lock(self, reason: str = "timeout") -> None:
        chest = self._chest
        if chest is None:
            return

        chest.state = ChestState.AVAILABLE
        chest.owner_id = None
        chest.combo = tuple()
        chest.attempts_left = 0
        chest.owner_expires_at = None
        self._cancel_owner_task()

        if self._event_callback and reason == "timeout":
            try:
                asyncio.create_task(self._event_callback("owner_timeout", chest))
            except Exception:
                pass

    def _mark_opened(self) -> None:
        chest = self._chest
        if chest is None:
            return

        chest.state = ChestState.OPENED
        self._cleanup_chest()

        if self._event_callback:
            try:
                asyncio.create_task(self._event_callback("opened", chest))
            except Exception:
                pass

    async def _expire_after(self, duration: timedelta) -> None:
        try:
            await asyncio.sleep(duration.total_seconds())
            chest = self._chest
            if chest and chest.state in (ChestState.AVAILABLE, ChestState.LOCKED):
                chest.state = ChestState.EXPIRED
                self._cleanup_chest()
                if self._event_callback:
                    try:
                        await self._event_callback("expired", chest)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass

    async def _owner_timeout(self) -> None:
        try:
            await asyncio.sleep(LOCK_OWNER_TIMEOUT.total_seconds())
            chest = self._chest
            if chest and chest.state == ChestState.LOCKED and self._owner_lock_expired(chest):
                self._reset_lock(reason="timeout")
        except asyncio.CancelledError:
            pass

    def _cleanup_chest(self) -> None:
        self._cancel_tasks()
        self._chest = None

    def _cancel_tasks(self) -> None:
        self._cancel_owner_task()
        if self._expire_task and not self._expire_task.done():
            self._expire_task.cancel()
        self._expire_task = None

    def _cancel_owner_task(self) -> None:
        if self._owner_task and not self._owner_task.done():
            self._owner_task.cancel()
        self._owner_task = None

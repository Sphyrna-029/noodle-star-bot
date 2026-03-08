"""Treasure chest lock-picking use cases."""

from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import Callable, Optional

from cogs.treasure.constants import (
    CHEST_ITEM_DROP_CHANCE,
    CHEST_ITEM_TIER_CHANCE,
    CHEST_LIFETIME,
    CHEST_RARE_ITEM_DROP_CHANCE,
    FAIL_MESSAGE,
    LOCK_ATTEMPTS,
    LOCK_INSTRUCTIONS,
    LOCK_OWNER_TIMEOUT,
    LOCK_RECLAIM_COOLDOWN,
    LOCK_PIN_COUNT,
    LOCK_PIN_COUNT_ITEM_CHEST,
    LOCK_PIN_MAX,
    LOCK_PIN_MIN,
    LOCK_RETRY_PENALTY_MAX,
    LOCK_RETRY_PENALTY_MIN,
    SUCCESS_MESSAGE,
    TIMEOUT_MESSAGE,
    TREASURE_REWARD_MAX,
    TREASURE_REWARD_MAX_RARE,
    TREASURE_REWARD_MIN,
    TREASURE_REWARD_MIN_RARE,
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
        self._user_reclaim_cooldowns: dict[int, datetime] = {}
        self._common_drop_table = (
            ("helmet", "🪖", "Mining Helmet", 1),
            ("sword", "⚔️", "Sword", 1),
            ("raw_potato", "🥔", "Raw Potato", 3),
            ("bait_worm", "🪱", "Worm Bait", 3),
            ("bait_herring", "🐟", "Herring Bait", 2),
            ("bait_sturgeon", "🐋", "Sturgeon Bait", 1),
            ("bank_insurance", "💸", "Bank Insurance", 1),
        )
        self._rare_drop_table = (
            ("golden_axe", "🪓", "Golden Axe", 25),
            ("mithril_shield", "🛡️", "Mithril Shield", 5),
            ("rune_fragment", "🪨", "Rune Fragment", 10),
            ("fossilized_noodle", "🍜", "Fossilized Noodle", 10),
            ("star_magnet", "🧲", "Star Magnet", 10),
            ("lucky_charm", "🍀", "Lucky Charm", 20),
            ("heart_of_leviathan", "💜", "Heart of Leviathan", 1),
        )

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
        item_tier = random.random() < CHEST_ITEM_TIER_CHANCE
        if item_tier:
            reward = random.randint(TREASURE_REWARD_MIN_RARE, TREASURE_REWARD_MAX_RARE)
        else:
            reward = random.randint(TREASURE_REWARD_MIN, TREASURE_REWARD_MAX)
        expires_at = now + CHEST_LIFETIME if CHEST_LIFETIME else None

        self._chest = TreasureChest(
            channel_id=channel_id,
            state=ChestState.AVAILABLE,
            reward=reward,
            spawned_at=now,
            pin_count=LOCK_PIN_COUNT_ITEM_CHEST if item_tier else LOCK_PIN_COUNT,
            item_drop_chance=CHEST_ITEM_DROP_CHANCE if item_tier else 0.0,
            rare_item_drop_chance=CHEST_RARE_ITEM_DROP_CHANCE if item_tier else 0.0,
            expires_at=expires_at,
        )

        if expires_at is not None:
            self._expire_task = asyncio.create_task(self._expire_after(CHEST_LIFETIME))

        return SpawnResult(True, self._build_spawn_announcement(item_tier), self._chest)

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
                    pins=chest.pin_count,
                    min_pin=LOCK_PIN_MIN,
                    max_pin=LOCK_PIN_MAX,
                    attempts=chest.attempts_left,
                    example_guess=self._build_guess_example(chest.pin_count),
                    compact_example_guess=self._build_compact_guess_example(chest.pin_count),
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

        reclaim_remaining = self._get_reclaim_cooldown_remaining(user_id)
        if reclaim_remaining is not None:
            remaining_seconds = max(1, math.ceil(reclaim_remaining.total_seconds()))
            return StartPickResult(
                False,
                f"You just had a lock attempt. You can try again in **{remaining_seconds}s**.",
                chest,
            )

        chest.state = ChestState.LOCKED
        chest.owner_id = user_id
        chest.combo = self._generate_combo(chest.pin_count)
        chest.guess_history = []
        chest.attempts_left = LOCK_ATTEMPTS
        chest.owner_expires_at = datetime.now() + LOCK_OWNER_TIMEOUT

        self._cancel_owner_task()
        self._owner_task = asyncio.create_task(self._owner_timeout())

        return StartPickResult(
            True,
            LOCK_INSTRUCTIONS.format(
                pins=chest.pin_count,
                min_pin=LOCK_PIN_MIN,
                max_pin=LOCK_PIN_MAX,
                attempts=LOCK_ATTEMPTS,
                example_guess=self._build_guess_example(chest.pin_count),
                compact_example_guess=self._build_compact_guess_example(chest.pin_count),
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

        if len(guess) != chest.pin_count:
            return PickResult(
                False,
                (
                    f"Enter **{chest.pin_count}** digits between {LOCK_PIN_MIN}-{LOCK_PIN_MAX}.\n"
                    f"Examples: `{self._build_guess_example(chest.pin_count)}` or "
                    f"`{self._build_compact_guess_example(chest.pin_count)}`."
                ),
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
        guess_tuple = tuple(guess)

        if exact == chest.pin_count:
            reward = chest.reward
            current = self.repo.get_user_stars(user_id, username)
            new_balance = current + reward
            self.repo.update_user_stars(user_id, username, new_balance)
            self.repo.update_username(user_id, username)

            found_items: list[str] = []
            item_drop = self._roll_item_drop(user_id, chest)
            if item_drop is not None:
                found_items.append(item_drop)

            message = SUCCESS_MESSAGE.format(mention=f"<@{user_id}>", reward=reward)
            if found_items:
                message += "\n\n🎒 **Item drop:** " + "\n".join(found_items)
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
                found_items=found_items,
            )

        chest.guess_history.append((guess_tuple, exact, misplaced))
        chest.guess_history = chest.guess_history[-5:]

        failed_guesses = LOCK_ATTEMPTS - chest.attempts_left
        penalty_notice = (
            "First failed guess is free. "
            f"Further retries cost **{LOCK_RETRY_PENALTY_MIN}-{LOCK_RETRY_PENALTY_MAX}** stars each."
        )
        penalty_loss = 0
        new_balance = 0
        rolled_penalty = 0
        if failed_guesses > 1:
            rolled_penalty = random.randint(LOCK_RETRY_PENALTY_MIN, LOCK_RETRY_PENALTY_MAX)
            current_stars = self.repo.get_user_stars(user_id, username)
            updated_stars = max(0, current_stars - rolled_penalty)
            penalty_loss = current_stars - updated_stars
            if penalty_loss > 0:
                self.repo.update_user_stars(user_id, username, updated_stars)
                self.repo.update_username(user_id, username)
            new_balance = updated_stars
            if penalty_loss > 0:
                penalty_notice = (
                    f"Retry penalty: **-{penalty_loss}** stars. "
                    f"New balance: **{updated_stars}**."
                )
            else:
                penalty_notice = (
                    f"Retry penalty rolled **{rolled_penalty}**, but you had no stars to lose."
                )

        if chest.attempts_left <= 0:
            self._reset_lock(reason="failed")
            jam_message = (
                "❌ The lock jammed after too many attempts. The chest resets for others.\n"
                f"Last guess: {self._format_guess_slots(guess_tuple)}\n"
                f"Feedback: 🟩 Correct pin + slot **{exact}** | "
                f"🟨 Correct pin, wrong slot **{misplaced}**"
            )
            if penalty_loss > 0:
                jam_message += f"\nRetry cost applied: **-{penalty_loss}** stars."
            elif failed_guesses > 1 and rolled_penalty > 0:
                jam_message += "\nRetry cost rolled, but you had no stars to lose."
            return PickResult(
                True,
                jam_message,
                opened=False,
                exact=exact,
                misplaced=misplaced,
                attempts_left=0,
                new_balance=new_balance,
            )

        return PickResult(
            True,
            FAIL_MESSAGE.format(
                guess_slots=self._format_guess_slots(guess_tuple),
                exact=exact,
                misplaced=misplaced,
                attempts_left=chest.attempts_left,
                history_block=self._build_guess_history(chest),
            ),
            opened=False,
            exact=exact,
            misplaced=misplaced,
            attempts_left=chest.attempts_left,
            new_balance=new_balance,
        )

    def status(self) -> StatusResult:
        """Get the current chest status."""
        chest = self._chest
        if chest is None or chest.state == ChestState.IDLE:
            return StatusResult(False, "There is no active chest right now.", None)

        if chest.state == ChestState.AVAILABLE:
            return StatusResult(
                True,
                (
                    "A chest is available to pick.\n"
                    "Use `!pick start` (or the Start button) to claim the lock."
                ),
                chest,
            )

        if chest.state == ChestState.LOCKED:
            attempts_used = LOCK_ATTEMPTS - chest.attempts_left
            return StatusResult(
                True,
                (
                    f"The chest is being picked by <@{chest.owner_id}>.\n"
                    f"Progress: **{attempts_used}/{LOCK_ATTEMPTS}** attempts used."
                ),
                chest,
            )

        return StatusResult(True, f"Chest status: {chest.state.value}.", chest)

    def end_chest(self) -> StatusResult:
        """Force-remove the current chest."""
        if self._chest is None or self._chest.state == ChestState.IDLE:
            return StatusResult(False, "There is no active chest to end.", None)

        self._cleanup_chest()
        return StatusResult(True, "Chest ended.", None)

    def give_up_pick(self, user_id: int, channel_id: int) -> StatusResult:
        """Release the lock if the current owner gives up."""
        chest = self._chest
        if chest is None or chest.state == ChestState.IDLE:
            return StatusResult(False, "There is no active chest right now.", None)

        if chest.channel_id != channel_id:
            return StatusResult(False, "The chest is in a different channel.", chest)

        if chest.state != ChestState.LOCKED:
            return StatusResult(False, "The chest is not currently locked.", chest)

        if chest.owner_id != user_id:
            return StatusResult(False, "Only the current picker can give up the lock.", chest)

        self._reset_lock(reason="give_up")
        return StatusResult(True, "You gave up the lock. The chest is now available to others.", chest)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _generate_combo(self, pin_count: int) -> tuple[int, ...]:
        return tuple(
            random.randint(LOCK_PIN_MIN, LOCK_PIN_MAX) for _ in range(pin_count)
        )

    @staticmethod
    def _build_guess_example(pin_count: int) -> str:
        sample = " ".join(str(random.randint(LOCK_PIN_MIN, LOCK_PIN_MAX)) for _ in range(pin_count))
        return f"!pick {sample}"

    @staticmethod
    def _build_compact_guess_example(pin_count: int) -> str:
        sample = "".join(str(random.randint(LOCK_PIN_MIN, LOCK_PIN_MAX)) for _ in range(pin_count))
        return f"!pick {sample}"

    @staticmethod
    def _format_guess_slots(guess: tuple[int, ...]) -> str:
        return ", ".join(str(pin) for pin in guess)

    def _build_guess_history(self, chest: TreasureChest, limit: int = 3) -> str:
        if not chest.guess_history:
            return "Recent guesses: _none yet_"

        rows = chest.guess_history[-limit:]
        lines = ["Recent guesses:"]
        for guess, exact, misplaced in reversed(rows):
            lines.append(
                f"• {self._format_guess_slots(guess)} -> "
                f"🟩 correct pin+slot: {exact}, 🟨 correct pin wrong slot: {misplaced}"
            )
        return "\n".join(lines)

    @staticmethod
    def _build_spawn_announcement(item_tier: bool) -> str:
        if item_tier:
            return (
                "🧰 A **RARE locked treasure chest** appears! "
                "It has a harder lock, higher star rewards, and rare-drop potential. "
                "Use `!pick start` to begin."
            )
        return (
            "🧰 A **standard locked treasure chest** appears! "
            "Use `!pick start` to begin."
        )

    def _roll_item_drop(self, user_id: int, chest: TreasureChest) -> str | None:
        if chest.item_drop_chance <= 0:
            return None
        if random.random() >= chest.item_drop_chance:
            return None

        use_rare_pool = random.random() < chest.rare_item_drop_chance
        table = self._rare_drop_table if use_rare_pool else self._common_drop_table
        item_key, emoji, item_name, amount = random.choice(table)

        inventory = self.repo.get_user_inventory(user_id)
        current = inventory.get(item_key, 0)
        self.repo.update_user_inventory(user_id, item_key, current + amount)

        rarity_prefix = "RARE " if use_rare_pool else ""
        return f"{emoji} **{rarity_prefix}{item_name}** (x{amount})"

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

    def _get_reclaim_cooldown_remaining(self, user_id: int) -> timedelta | None:
        ready_at = self._user_reclaim_cooldowns.get(user_id)
        if ready_at is None:
            return None

        remaining = ready_at - datetime.now()
        if remaining <= timedelta(0):
            self._user_reclaim_cooldowns.pop(user_id, None)
            return None
        return remaining

    def _set_reclaim_cooldown(self, user_id: int | None) -> None:
        if user_id is None:
            return
        self._user_reclaim_cooldowns[user_id] = datetime.now() + LOCK_RECLAIM_COOLDOWN

    def _reset_lock(self, reason: str = "timeout") -> None:
        chest = self._chest
        if chest is None:
            return

        self._set_reclaim_cooldown(chest.owner_id)
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

        self._set_reclaim_cooldown(chest.owner_id)
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
                if chest.state == ChestState.LOCKED:
                    self._set_reclaim_cooldown(chest.owner_id)
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

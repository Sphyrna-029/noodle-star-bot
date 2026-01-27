"""Fishing service for the fishing minigame."""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from config import (
    FISHING_BAIT_TIERS,
    FISHING_CATCH_TABLE,
    FISHING_COOLDOWN_SECONDS,
)
from database.repository import UserRepository


# =============================================================================
# Enums and Data Classes
# =============================================================================


class FishingState(Enum):
    """States for the fishing state machine."""
    WAITING = "waiting"  # Line cast, waiting for bite
    BITING = "biting"    # Fish is biting, waiting for pull


@dataclass
class FishingSession:
    """Represents an active fishing session for a user."""
    user_id: int
    channel_id: int
    state: FishingState
    bait_type: str
    cast_at: datetime
    bite_at: datetime
    expires_at: datetime
    task: Optional[asyncio.Task] = field(default=None, repr=False)


@dataclass
class CastResult:
    """Result of casting a line."""
    success: bool
    message: str
    bite_wait_seconds: int = 0


@dataclass
class PullResult:
    """Result of pulling the line."""
    success: bool
    message: str
    catch_name: str = ""
    catch_emoji: str = ""
    catch_rarity: str = ""
    stars_earned: int = 0
    new_balance: int = 0


@dataclass
class FishingStatus:
    """Current fishing status for a user."""
    is_fishing: bool
    state: Optional[FishingState] = None
    bait_type: Optional[str] = None
    time_until_bite: Optional[int] = None      # seconds
    time_until_expires: Optional[int] = None   # seconds
    cooldown_remaining: Optional[int] = None   # seconds


@dataclass
class BaitSelectionResult:
    """Result of auto-selecting bait."""
    success: bool
    message: str
    bait_type: Optional[str] = None
    available_baits: Optional[List[Tuple[str, int]]] = None


@dataclass
class Catch:
    """Represents a caught fish/item."""
    name: str
    emoji: str
    stars: int
    rarity: str


# =============================================================================
# Helper Functions
# =============================================================================


def format_cooldown(seconds: int) -> str:
    """Format cooldown seconds as a human-readable string."""
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _get_time_of_day() -> str:
    """
    Get current time period based on UTC hour.

    Returns 'night' (18:00-06:00 UTC) or 'day' (06:00-18:00 UTC).
    """
    from datetime import timezone
    hour = datetime.now(timezone.utc).hour
    if hour >= 18 or hour < 6:
        return "night"
    return "day"


def get_time_multiplier() -> float:
    """
    Get timing multiplier based on time of day.

    Night: 0.75x (25% faster bites, 25% shorter windows)
    Day: 1.25x (25% slower bites, 25% longer windows)
    """
    if _get_time_of_day() == "night":
        return 0.75
    return 1.25


def get_fishing_conditions() -> str:
    """
    Get a vague hint about current fishing conditions.

    Intentionally mysterious - doesn't reveal the UTC timing mechanism.
    """
    if _get_time_of_day() == "night":
        return "The fish are restless... they seem eager to bite."
    return "The waters are calm... patience may be required."


# =============================================================================
# Fishing Service
# =============================================================================


class FishingService:
    """
    Handles all fishing-related business logic.

    Manages the fishing state machine:
    1. User casts line (!fish) -> WAITING state
    2. After random delay, fish bites -> BITING state, notify user
    3. User must !pull within window -> success/fail
    4. Session cleaned up, cooldown applied
    """

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()
        self._sessions: Dict[int, FishingSession] = {}
        self._bite_callback: Optional[Callable] = None

    def set_bite_callback(self, callback: Callable) -> None:
        """Set the callback function for bite notifications."""
        self._bite_callback = callback

    def get_session(self, user_id: int) -> Optional[FishingSession]:
        """Get active fishing session for a user."""
        return self._sessions.get(user_id)

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _cleanup_session(self, user_id: int) -> None:
        """Clean up a fishing session and cancel its async task."""
        session = self._sessions.pop(user_id, None)
        if session and session.task and not session.task.done():
            session.task.cancel()

    def _check_cooldown(self, user_id: int) -> Optional[int]:
        """
        Check if user is on fishing cooldown.

        Returns remaining seconds if on cooldown, None otherwise.
        """
        last_fish = self.repo.get_last_fish(user_id)
        if last_fish is None:
            return None

        cooldown_end = last_fish + timedelta(seconds=FISHING_COOLDOWN_SECONDS)
        now = datetime.now()

        if now < cooldown_end:
            return int((cooldown_end - now).total_seconds())
        return None

    def _roll_catch(self, bait_type: str) -> Catch:
        """
        Roll a catch based on bait tier.

        Bait rare_boost increases odds of rare/legendary catches.
        """
        bait_config = FISHING_BAIT_TIERS[bait_type]
        rare_boost = bait_config["rare_boost"]

        # Calculate adjusted weights
        common_weight = FISHING_CATCH_TABLE["common"]["weight"]
        rare_weight = FISHING_CATCH_TABLE["rare"]["weight"] * rare_boost
        legendary_weight = FISHING_CATCH_TABLE["legendary"]["weight"] * rare_boost
        total_weight = common_weight + rare_weight + legendary_weight

        # Roll for rarity tier
        roll = random.random() * total_weight
        if roll < common_weight:
            rarity = "common"
        elif roll < common_weight + rare_weight:
            rarity = "rare"
        else:
            rarity = "legendary"

        # Roll for specific catch within rarity
        catches = FISHING_CATCH_TABLE[rarity]["catches"]
        catch_weights = [c["weight"] for c in catches]
        catch = random.choices(catches, weights=catch_weights, k=1)[0]

        return Catch(
            name=catch["name"],
            emoji=catch["emoji"],
            stars=catch["stars"],
            rarity=rarity,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_available_baits(self, user_id: int) -> List[Tuple[str, int]]:
        """
        Get list of bait types the user has in inventory.

        Returns list of (bait_type, count) tuples for baits with count > 0.
        """
        bait_inventory = self.repo.get_bait_inventory(user_id)
        return [
            (bait_type, bait_inventory.get(bait_type, 0))
            for bait_type in FISHING_BAIT_TIERS
            if bait_inventory.get(bait_type, 0) > 0
        ]

    def select_bait(
        self,
        user_id: int,
        username: str,
        requested_bait: Optional[str] = None,
    ) -> BaitSelectionResult:
        """
        Select bait for fishing, with auto-selection if only one type available.

        Args:
            user_id: Discord user ID
            username: Discord username
            requested_bait: Specific bait type requested, or None for auto-select

        Returns:
            BaitSelectionResult with selected bait or error message
        """
        self.repo.get_user(user_id, username)
        available_baits = self.get_available_baits(user_id)

        # No bait at all
        if not available_baits:
            return BaitSelectionResult(
                success=False,
                message="You don't have any bait! Buy some from the `!store`.",
                available_baits=[],
            )

        # User specified a bait type
        if requested_bait:
            requested_bait = requested_bait.lower().strip()

            if requested_bait not in FISHING_BAIT_TIERS:
                valid_types = ", ".join(FISHING_BAIT_TIERS.keys())
                return BaitSelectionResult(
                    success=False,
                    message=f"Invalid bait type! Valid types: {valid_types}",
                    available_baits=available_baits,
                )

            # Check if user has this bait (use available_baits to avoid extra DB call)
            bait_counts = dict(available_baits)
            if bait_counts.get(requested_bait, 0) <= 0:
                bait_info = FISHING_BAIT_TIERS[requested_bait]
                return BaitSelectionResult(
                    success=False,
                    message=f"You don't have any {bait_info['emoji']} **{bait_info['display_name']}** bait!",
                    available_baits=available_baits,
                )

            return BaitSelectionResult(
                success=True,
                message="",
                bait_type=requested_bait,
                available_baits=available_baits,
            )

        # Auto-select: only one bait type available
        if len(available_baits) == 1:
            return BaitSelectionResult(
                success=True,
                message="",
                bait_type=available_baits[0][0],
                available_baits=available_baits,
            )

        # Multiple bait types available - ask user to specify
        return BaitSelectionResult(
            success=False,
            message="You have multiple bait types! Please specify which to use: `!fish <bait>`",
            available_baits=available_baits,
        )

    def get_status(self, user_id: int, username: str) -> FishingStatus:
        """Get the current fishing status for a user."""
        self.repo.get_user(user_id, username)

        session = self.get_session(user_id)
        cooldown = self._check_cooldown(user_id)

        if session is None:
            return FishingStatus(
                is_fishing=False,
                cooldown_remaining=cooldown,
            )

        now = datetime.now()

        if session.state == FishingState.WAITING:
            time_until_bite = max(0, int((session.bite_at - now).total_seconds()))
            return FishingStatus(
                is_fishing=True,
                state=session.state,
                bait_type=session.bait_type,
                time_until_bite=time_until_bite,
            )

        if session.state == FishingState.BITING:
            time_until_expires = max(0, int((session.expires_at - now).total_seconds()))
            return FishingStatus(
                is_fishing=True,
                state=session.state,
                bait_type=session.bait_type,
                time_until_expires=time_until_expires,
            )

        return FishingStatus(
            is_fishing=False,
            cooldown_remaining=cooldown,
        )

    async def cast_line(
        self,
        user_id: int,
        username: str,
        channel_id: int,
        bait_type: Optional[str] = None,
    ) -> CastResult:
        """
        Cast a fishing line.

        Validates:
        - User not already fishing
        - User not on cooldown
        - User has bait (auto-selects if only one type, asks if multiple)

        Creates a session and schedules the bite notification.
        """
        self.repo.get_user(user_id, username)

        # Check if already fishing
        if user_id in self._sessions:
            session = self._sessions[user_id]
            if session.state == FishingState.BITING:
                return CastResult(
                    success=False,
                    message="You already have a fish on the line! Use `!pull` to reel it in!",
                )
            return CastResult(
                success=False,
                message="You're already fishing! Wait for a bite or use `!fishing` to check status.",
            )

        # Check cooldown
        cooldown = self._check_cooldown(user_id)
        if cooldown is not None:
            return CastResult(
                success=False,
                message=f"You're too tired to fish! Wait **{format_cooldown(cooldown)}** before fishing again.",
            )

        # Select bait
        bait_selection = self.select_bait(user_id, username, bait_type)
        if not bait_selection.success:
            if bait_selection.available_baits:
                bait_list = ", ".join(
                    f"{FISHING_BAIT_TIERS[bt]['emoji']} {bt} (x{count})"
                    for bt, count in bait_selection.available_baits
                )
                return CastResult(
                    success=False,
                    message=f"{bait_selection.message}\nYour bait: {bait_list}",
                )
            return CastResult(success=False, message=bait_selection.message)

        selected_bait = bait_selection.bait_type

        # Consume the bait
        self.repo.consume_bait(user_id, selected_bait)

        # Calculate bite timing with time-of-day multiplier
        bait_config = FISHING_BAIT_TIERS[selected_bait]
        time_mult = get_time_multiplier()

        min_wait, max_wait = bait_config["bite_wait"]
        bite_wait = int(random.randint(min_wait, max_wait) * time_mult)

        pull_window = int(bait_config["pull_window"] * time_mult)

        now = datetime.now()
        bite_at = now + timedelta(seconds=bite_wait)
        expires_at = bite_at + timedelta(seconds=pull_window)

        # Create session
        session = FishingSession(
            user_id=user_id,
            channel_id=channel_id,
            state=FishingState.WAITING,
            bait_type=selected_bait,
            cast_at=now,
            bite_at=bite_at,
            expires_at=expires_at,
        )
        self._sessions[user_id] = session

        # Schedule bite notification
        session.task = asyncio.create_task(
            self._schedule_bite(user_id, bite_wait, pull_window)
        )

        bait_info = FISHING_BAIT_TIERS[selected_bait]
        return CastResult(
            success=True,
            message=f"You cast your line with {bait_info['emoji']} **{bait_info['display_name']}** bait... "
                    f"waiting for a bite.",
            bite_wait_seconds=bite_wait,
        )

    async def _schedule_bite(
        self,
        user_id: int,
        bite_wait: int,
        pull_window: int,
    ) -> None:
        """Schedule the bite notification and handle expiry."""
        try:
            await asyncio.sleep(bite_wait)

            session = self._sessions.get(user_id)
            if session is None:
                return

            # Transition to BITING state
            session.state = FishingState.BITING
            session.expires_at = datetime.now() + timedelta(seconds=pull_window)

            # Send bite notification
            if self._bite_callback:
                try:
                    await self._bite_callback(user_id, session.channel_id, pull_window)
                except Exception:
                    pass  # Don't let callback errors crash the scheduler

            # Wait for pull window to expire
            await asyncio.sleep(pull_window)

            # Check if still biting (user didn't pull)
            session = self._sessions.get(user_id)
            if session and session.state == FishingState.BITING:
                channel_id = session.channel_id
                self._cleanup_session(user_id)
                self.repo.update_last_fish(user_id)

                # Send escape notification
                if self._bite_callback:
                    try:
                        await self._bite_callback(user_id, channel_id, -1)
                    except Exception:
                        pass

        except asyncio.CancelledError:
            pass  # Session was cancelled (user pulled or cleaned up)

    def pull_line(self, user_id: int, username: str) -> PullResult:
        """
        Attempt to pull the fishing line.

        Outcomes:
        - Too early (WAITING): fail, apply cooldown
        - In window (BITING): success, roll catch, award stars
        - No session: fail message
        """
        session = self._sessions.get(user_id)

        # No active session
        if session is None:
            if self._check_cooldown(user_id):
                return PullResult(
                    success=False,
                    message="The fish got away! You pulled too late.",
                )
            return PullResult(
                success=False,
                message="You're not fishing! Use `!fish` to cast your line.",
            )

        # Too early - still waiting for bite
        if session.state == FishingState.WAITING:
            self._cleanup_session(user_id)
            self.repo.update_last_fish(user_id)
            return PullResult(
                success=False,
                message="You pulled too early! The fish wasn't biting yet. "
                        "Your line snapped and you lost your bait.",
            )

        # In the window - success!
        if session.state == FishingState.BITING:
            bait_type = session.bait_type
            self._cleanup_session(user_id)
            self.repo.update_last_fish(user_id)

            catch = self._roll_catch(bait_type)

            current_stars = self.repo.get_user_stars(user_id, username)
            new_stars = current_stars + catch.stars
            self.repo.update_user_stars(user_id, username, new_stars)

            return PullResult(
                success=True,
                message=f"You caught a {catch.emoji} **{catch.name}**!",
                catch_name=catch.name,
                catch_emoji=catch.emoji,
                catch_rarity=catch.rarity,
                stars_earned=catch.stars,
                new_balance=new_stars,
            )

        # Unknown state (shouldn't happen)
        self._cleanup_session(user_id)
        return PullResult(
            success=False,
            message="Something went wrong with your fishing session.",
        )

    def cancel_session(self, user_id: int) -> bool:
        """Cancel an active fishing session. Returns True if one existed."""
        if user_id in self._sessions:
            self._cleanup_session(user_id)
            return True
        return False

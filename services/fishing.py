"""Fishing service for the fishing minigame."""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, Optional

from config import (
    FISHING_BAIT_TIERS,
    FISHING_CATCH_TABLE,
    FISHING_COOLDOWN_SECONDS,
)
from database.repository import UserRepository


class FishingState(Enum):
    """States for the fishing state machine."""
    IDLE = "idle"
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
    time_until_bite: Optional[int] = None  # seconds
    time_until_expires: Optional[int] = None  # seconds
    cooldown_remaining: Optional[int] = None  # seconds
    equipped_bait: Optional[str] = None


@dataclass
class EquipResult:
    """Result of equipping bait."""
    success: bool
    message: str


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
        # In-memory session storage: user_id -> FishingSession
        self._sessions: Dict[int, FishingSession] = {}
        # Callback for sending bite notifications
        self._bite_callback: Optional[Callable] = None

    def set_bite_callback(self, callback: Callable) -> None:
        """Set the callback function for bite notifications."""
        self._bite_callback = callback

    def get_session(self, user_id: int) -> Optional[FishingSession]:
        """Get active fishing session for a user."""
        return self._sessions.get(user_id)

    def _cleanup_session(self, user_id: int) -> None:
        """Clean up a fishing session."""
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

    def get_status(self, user_id: int, username: str) -> FishingStatus:
        """Get the current fishing status for a user."""
        # Ensure user exists
        self.repo.get_user(user_id, username)

        session = self.get_session(user_id)
        cooldown = self._check_cooldown(user_id)
        equipped = self.repo.get_equipped_bait(user_id)

        if session is None:
            return FishingStatus(
                is_fishing=False,
                cooldown_remaining=cooldown,
                equipped_bait=equipped,
            )

        now = datetime.now()

        if session.state == FishingState.WAITING:
            time_until_bite = max(0, int((session.bite_at - now).total_seconds()))
            return FishingStatus(
                is_fishing=True,
                state=session.state,
                bait_type=session.bait_type,
                time_until_bite=time_until_bite,
                equipped_bait=equipped,
            )

        elif session.state == FishingState.BITING:
            time_until_expires = max(0, int((session.expires_at - now).total_seconds()))
            return FishingStatus(
                is_fishing=True,
                state=session.state,
                bait_type=session.bait_type,
                time_until_expires=time_until_expires,
                equipped_bait=equipped,
            )

        return FishingStatus(
            is_fishing=False,
            cooldown_remaining=cooldown,
            equipped_bait=equipped,
        )

    def equip_bait(self, user_id: int, username: str, bait_type: str) -> EquipResult:
        """Equip a bait type for the next fishing attempt."""
        # Ensure user exists
        self.repo.get_user(user_id, username)

        # Validate bait type
        bait_type = bait_type.lower().strip()
        if bait_type not in FISHING_BAIT_TIERS:
            valid_types = ", ".join(FISHING_BAIT_TIERS.keys())
            return EquipResult(
                success=False,
                message=f"Invalid bait type! Valid types: {valid_types}",
            )

        # Check if user has this bait
        bait_inventory = self.repo.get_bait_inventory(user_id)
        if bait_inventory.get(bait_type, 0) <= 0:
            bait_info = FISHING_BAIT_TIERS[bait_type]
            return EquipResult(
                success=False,
                message=f"You don't have any {bait_info['emoji']} **{bait_info['display_name']}** bait! "
                        f"Buy some from the `!store`.",
            )

        # Equip the bait
        self.repo.set_equipped_bait(user_id, bait_type)
        bait_info = FISHING_BAIT_TIERS[bait_type]

        return EquipResult(
            success=True,
            message=f"Equipped {bait_info['emoji']} **{bait_info['display_name']}** bait!\n"
                    f"Bite wait: {bait_info['bite_wait'][0]}-{bait_info['bite_wait'][1]}s | "
                    f"Pull window: {bait_info['pull_window']}s | "
                    f"Rare boost: {bait_info['rare_boost']}x",
        )

    async def cast_line(
        self,
        user_id: int,
        username: str,
        channel_id: int,
    ) -> CastResult:
        """
        Cast a fishing line.

        Validates:
        - User not already fishing
        - User not on cooldown
        - User has equipped bait (or defaults to worm)

        Creates a session and schedules the bite notification.
        """
        # Ensure user exists
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
            minutes = cooldown // 60
            seconds = cooldown % 60
            if minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"
            return CastResult(
                success=False,
                message=f"You're too tired to fish! Wait **{time_str}** before fishing again.",
            )

        # Get equipped bait (default to worm if none equipped)
        equipped_bait = self.repo.get_equipped_bait(user_id)
        if equipped_bait is None:
            equipped_bait = "worm"

        # Check if user has the bait
        bait_inventory = self.repo.get_bait_inventory(user_id)
        if bait_inventory.get(equipped_bait, 0) <= 0:
            bait_info = FISHING_BAIT_TIERS[equipped_bait]
            return CastResult(
                success=False,
                message=f"You don't have any {bait_info['emoji']} **{bait_info['display_name']}** bait! "
                        f"Buy some from the `!store` or equip different bait with `!use bait <type>`.",
            )

        # Consume the bait
        self.repo.consume_bait(user_id, equipped_bait)

        # Calculate bite timing
        bait_config = FISHING_BAIT_TIERS[equipped_bait]
        min_wait, max_wait = bait_config["bite_wait"]
        bite_wait = random.randint(min_wait, max_wait)

        now = datetime.now()
        bite_at = now + timedelta(seconds=bite_wait)
        # expires_at will be set when bite occurs
        expires_at = bite_at + timedelta(seconds=bait_config["pull_window"])

        # Create session
        session = FishingSession(
            user_id=user_id,
            channel_id=channel_id,
            state=FishingState.WAITING,
            bait_type=equipped_bait,
            cast_at=now,
            bite_at=bite_at,
            expires_at=expires_at,
        )
        self._sessions[user_id] = session

        # Schedule bite notification
        session.task = asyncio.create_task(
            self._schedule_bite(user_id, bite_wait, bait_config["pull_window"])
        )

        bait_info = FISHING_BAIT_TIERS[equipped_bait]
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
        """Schedule the bite notification and expiry."""
        try:
            # Wait for bite
            await asyncio.sleep(bite_wait)

            session = self._sessions.get(user_id)
            if session is None:
                return  # Session was cleaned up

            # Transition to BITING state
            session.state = FishingState.BITING
            now = datetime.now()
            session.expires_at = now + timedelta(seconds=pull_window)

            # Send bite notification (isolate callback errors so scheduling continues)
            if self._bite_callback:
                try:
                    await self._bite_callback(
                        user_id,
                        session.channel_id,
                        pull_window,
                    )
                except Exception:
                    # Swallow callback exceptions to avoid cancelling the schedule
                    pass

            # Wait for pull window to expire
            await asyncio.sleep(pull_window)

            # Check if still in BITING state (not pulled)
            session = self._sessions.get(user_id)
            if session and session.state == FishingState.BITING:
                # Fish escaped - clean up and apply cooldown
                self._cleanup_session(user_id)
                self.repo.update_last_fish(user_id)

                # Send escape notification (isolate callback errors)
                if self._bite_callback:
                    try:
                        await self._bite_callback(
                            user_id,
                            session.channel_id,
                            -1,  # -1 indicates escape
                        )
                    except Exception:
                        pass

        except asyncio.CancelledError:
            # Session was cancelled (user pulled or session cleaned up)
            pass

    def pull_line(self, user_id: int, username: str) -> PullResult:
        """
        Attempt to pull the fishing line.

        Outcomes:
        - Too early (WAITING state): penalty cooldown, end attempt
        - In window (BITING state): success, roll catch
        - Too late (no session): fail message
        """
        session = self._sessions.get(user_id)

        # No active session
        if session is None:
            # Check if on cooldown (meaning they missed the window)
            cooldown = self._check_cooldown(user_id)
            if cooldown:
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
            # Apply a short penalty cooldown (half the normal cooldown)
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

            # Roll the catch
            catch = self._roll_catch(bait_type)

            # Award stars
            current_stars = self.repo.get_user_stars(user_id, username)
            new_stars = current_stars + catch["stars"]
            self.repo.update_user_stars(user_id, username, new_stars)

            return PullResult(
                success=True,
                message=f"You caught a {catch['emoji']} **{catch['name']}**!",
                catch_name=catch["name"],
                catch_emoji=catch["emoji"],
                catch_rarity=catch["rarity"],
                stars_earned=catch["stars"],
                new_balance=new_stars,
            )

        # Unknown state
        self._cleanup_session(user_id)
        return PullResult(
            success=False,
            message="Something went wrong with your fishing session.",
        )

    def _roll_catch(self, bait_type: str) -> dict:
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

        # Roll for rarity
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

        return {
            "name": catch["name"],
            "emoji": catch["emoji"],
            "stars": catch["stars"],
            "rarity": rarity,
        }

    def cancel_session(self, user_id: int) -> bool:
        """Cancel an active fishing session. Returns True if there was one."""
        if user_id in self._sessions:
            self._cleanup_session(user_id)
            return True
        return False

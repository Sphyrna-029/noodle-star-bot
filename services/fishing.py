"""Fishing service for the fishing minigame."""

import asyncio
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional

from config import (
    FISH_LEVELS,
    FISHING_BAIT_TIERS,
    FISHING_CATCH_TABLE,
    FISHING_COOLDOWN,
)
from config.models import MineHazard
from database.repository import UserRepository


class FishingState(Enum):
    """States for the fishing state machine."""

    IDLE = "idle"
    WAITING = "waiting"  # Line cast, waiting for bite
    BITING = "biting"  # Fish is biting, waiting for pull


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
    active_level: int = 1
    jig_active: bool = False
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
    # Disaster fields (mirrors MineResult pattern)
    disaster: Optional[str] = None
    disaster_protected: bool = False
    disaster_header: str = ""
    disaster_protected_msg: str = ""
    disaster_unprotected_msg: str = ""
    stars_lost: int = 0
    bank_lost: int = 0
    items_destroyed: bool = False
    level_name: str = ""
    level_emoji: str = ""
    found_items: List[str] = field(default_factory=list)
    extra_messages: List[str] = field(default_factory=list)


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


@dataclass
class FishLevelInfo:
    """Info about a user's fishing levels."""

    unlocked_level: int
    active_level: int
    levels: dict  # reference to FISH_LEVELS


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

        cooldown_end = last_fish + timedelta(seconds=FISHING_COOLDOWN)
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
                message=f"You don't have any {bait_info.emoji} **{bait_info.display_name}** bait! "
                f"Buy some from the `!store`.",
            )

        # Equip the bait
        self.repo.set_equipped_bait(user_id, bait_type)
        bait_info = FISHING_BAIT_TIERS[bait_type]

        return EquipResult(
            success=True,
            message=f"Equipped {bait_info.emoji} **{bait_info.display_name}** bait!\n"
            f"Bite wait: {bait_info.bite_wait_min}-{bait_info.bite_wait_max}s | "
            f"Pull window: {bait_info.pull_window}s | "
            f"Rare boost: {bait_info.rare_boost}x",
        )

    def activate_jig(self, user_id: int, username: str) -> tuple[bool, str]:
        """Activate a bucktail jig for the next cast. Returns (success, message)."""
        self.repo.get_user(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)

        if inventory["bucktail_jig"] <= 0:
            return False, "You don't have any bucktail jigs!"

        if inventory["jig_active"]:
            return False, "You already have a jig active! It will apply to your next cast."

        self.repo.update_user_inventory(user_id, "bucktail_jig", inventory["bucktail_jig"] - 1)
        self.repo.update_user_inventory(user_id, "jig_active", 1)
        return True, "🎣 **Bucktail Jig activated!** Your next cast has a **20% legendary catch chance**!"

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
                message=f"You don't have any {bait_info.emoji} **{bait_info.display_name}** bait! "
                f"Buy some from the `!store` or equip different bait with `!use bait <type>`.",
            )

        # Consume the bait
        self.repo.consume_bait(user_id, equipped_bait)

        # Get the user's active fishing level
        active_level = self.repo.get_active_fish_level(user_id)

        # Check and consume jig_active flag
        inventory = self.repo.get_user_inventory(user_id)
        jig_active = bool(inventory["jig_active"])
        if jig_active:
            self.repo.update_user_inventory(user_id, "jig_active", 0)

        # Calculate bite timing
        bait_config = FISHING_BAIT_TIERS[equipped_bait]
        min_wait, max_wait = bait_config.bite_wait_min, bait_config.bite_wait_max
        bite_wait = random.randint(min_wait, max_wait)

        now = datetime.now()
        bite_at = now + timedelta(seconds=bite_wait)
        # expires_at will be set when bite occurs
        expires_at = bite_at + timedelta(seconds=bait_config.pull_window)

        # Create session
        session = FishingSession(
            user_id=user_id,
            channel_id=channel_id,
            state=FishingState.WAITING,
            bait_type=equipped_bait,
            cast_at=now,
            bite_at=bite_at,
            expires_at=expires_at,
            active_level=active_level,
            jig_active=jig_active,
        )
        self._sessions[user_id] = session

        # Schedule bite notification
        session.task = asyncio.create_task(
            self._schedule_bite(user_id, bite_wait, bait_config.pull_window)
        )

        bait_info = FISHING_BAIT_TIERS[equipped_bait]
        level_config = FISH_LEVELS[active_level]
        jig_msg = " 🎣 *Bucktail Jig active!*" if jig_active else ""
        return CastResult(
            success=True,
            message=f"You cast your line with {bait_info.emoji} **{bait_info.display_name}** bait "
            f"at {level_config['emoji']} **{level_config['name']}**... waiting for a bite.{jig_msg}",
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
        - In window (BITING state): success, roll catch, then roll disaster
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
            active_level = session.active_level
            jig_active = session.jig_active
            self._cleanup_session(user_id)
            self.repo.update_last_fish(user_id)

            level_config = FISH_LEVELS[active_level]

            # Roll the catch using level-specific table
            catch = self._roll_catch(bait_type, active_level, jig_active)

            # Read inventory for item effects
            inventory = self.repo.get_user_inventory(user_id)

            # Star magnet: +15% stars boost
            reward = catch["stars"]
            star_magnet_uses = inventory["star_magnet"]
            if star_magnet_uses > 0 and reward > 0:
                reward = math.ceil(reward * 1.15)
                self.repo.update_user_inventory(user_id, "star_magnet", star_magnet_uses - 1)

            # Award stars
            current_stars = self.repo.get_user_stars(user_id, username)
            new_stars = current_stars + reward
            self.repo.update_user_stars(user_id, username, new_stars)

            result = PullResult(
                success=True,
                message=f"You caught a {catch['emoji']} **{catch['name']}**!",
                catch_name=catch["name"],
                catch_emoji=catch["emoji"],
                catch_rarity=catch["rarity"],
                stars_earned=reward,
                new_balance=new_stars,
                level_name=level_config["name"],
                level_emoji=level_config["emoji"],
            )

            # Roll for disaster (after catch, matching mining pattern)
            disaster_chance = level_config["disaster_chance"]

            # Lucky charm halves disaster chance
            lucky_charm_uses = inventory["lucky_charm"]
            used_lucky_charm = False
            if lucky_charm_uses > 0:
                disaster_chance *= 0.5
                used_lucky_charm = True

            if disaster_chance > 0 and random.random() < disaster_chance:
                # Consume lucky charm use (it was active but disaster still happened)
                if used_lucky_charm:
                    self.repo.update_user_inventory(user_id, "lucky_charm", lucky_charm_uses - 1)

                hazard: MineHazard = random.choice(level_config["hazards"])
                result.disaster = hazard.name
                result.disaster_header = hazard.header

                # Re-read inventory in case star_magnet was consumed
                inv = self.repo.get_user_inventory(user_id)
                has_helmet = inv["helmet"] > 0
                has_sword = inv["sword"] > 0
                golden_axe_uses = inv["golden_axe"]
                mithril_shield_uses = inv["mithril_shield"]

                # Siren and Leviathan require special items only
                requires_special = hazard.name in ("siren", "leviathan")

                protected = False
                protection_msg = ""

                if hazard.protection_item == "helmet":
                    if not requires_special and has_helmet:
                        protected = True
                        protection_msg = hazard.protected_msg
                        self.repo.update_user_inventory(user_id, "helmet", 0)
                    elif mithril_shield_uses > 0:
                        protected = True
                        remaining = mithril_shield_uses - 1
                        self.repo.update_user_inventory(user_id, "mithril_shield", remaining)
                        protection_msg = (
                            f"🛡️ Your mithril shield absorbed the blow!\n"
                            f"*Your shield took a dent.* ({remaining} uses remaining)"
                        )
                elif hazard.protection_item == "sword":
                    if not requires_special and has_sword:
                        protected = True
                        protection_msg = hazard.protected_msg
                        self.repo.update_user_inventory(user_id, "sword", 0)
                    elif golden_axe_uses > 0:
                        protected = True
                        remaining = golden_axe_uses - 1
                        self.repo.update_user_inventory(user_id, "golden_axe", remaining)
                        protection_msg = (
                            f"🪓 Your golden axe fended off the attack!\n"
                            f"*Your golden axe took a hit.* ({remaining} uses remaining)"
                        )

                if protected:
                    result.disaster_protected = True
                    result.disaster_protected_msg = protection_msg
                else:
                    # Calculate wallet loss
                    stars_lost = int(new_stars * hazard.wallet_loss_pct)
                    new_stars = new_stars - stars_lost
                    self.repo.update_user_stars(user_id, username, new_stars)

                    # Calculate bank loss (heart of leviathan provides 100% protection)
                    bank_lost = 0
                    if hazard.bank_loss_pct > 0:
                        heart_uses = inv["heart_of_leviathan"]
                        if heart_uses > 0:
                            self.repo.update_user_inventory(user_id, "heart_of_leviathan", heart_uses - 1)
                            result.extra_messages.append(
                                "💜 Your **Heart of Leviathan** shielded your bank! *It crumbles to dust.*"
                            )
                        else:
                            current_bank = self.repo.get_user_bank(user_id)
                            bank_lost = int(current_bank * hazard.bank_loss_pct)
                            if bank_lost > 0:
                                self.repo.update_user_bank(user_id, username, current_bank - bank_lost)

                    self.repo.clear_user_inventory(user_id)
                    result.stars_lost = stars_lost
                    result.bank_lost = bank_lost
                    result.items_destroyed = True
                    result.new_balance = new_stars
                    result.disaster_unprotected_msg = hazard.unprotected_msg.format(
                        stars_lost=stars_lost, bank_lost=bank_lost
                    )
            else:
                # Lucky charm was active but no disaster — still consume a use
                if used_lucky_charm:
                    self.repo.update_user_inventory(user_id, "lucky_charm", lucky_charm_uses - 1)

            # ---------------------------------------------------------------
            # Roll for item drops (after disaster resolution)
            # ---------------------------------------------------------------

            # 1% golden axe on legendary catches
            if catch["rarity"] == "legendary" and random.random() < 0.01:
                self.repo.update_user_inventory(user_id, "golden_axe", 50)
                result.found_items.append(
                    "🪓 **Golden Axe** found! Protects against sword-type hazards (50 uses)."
                )

            # 0.1% mithril shield on any catch
            if random.random() < 0.001:
                self.repo.update_user_inventory(user_id, "mithril_shield", 10)
                result.found_items.append(
                    "🛡️ **Mithril Shield** found! Protects against helmet-type hazards (10 uses)."
                )

            # 0.3% bucktail jig on any catch
            if random.random() < 0.003:
                cur_jig = self.repo.get_user_inventory(user_id)["bucktail_jig"]
                self.repo.update_user_inventory(user_id, "bucktail_jig", cur_jig + 1)
                result.found_items.append(
                    "🎣 **Bucktail Jig** found! Use `!use jig` for 20% legendary chance on next cast."
                )

            # 0.35% ray-gun on any catch
            if random.random() < 0.0035:
                self.repo.update_user_inventory(user_id, "ray_gun", 2)
                result.found_items.append(
                    "🔫 **Ray-Gun** found! Protects your items from alien abduction (2 uses)."
                )

            # 1% star magnet on rare or legendary catches
            if catch["rarity"] in ("rare", "legendary") and random.random() < 0.01:
                self.repo.update_user_inventory(user_id, "star_magnet", 20)
                result.found_items.append(
                    "🧲 **Star Magnet** found! +15% stars on mining and fishing (20 uses)."
                )

            # 0.05% lucky charm on any catch
            if random.random() < 0.0005:
                self.repo.update_user_inventory(user_id, "lucky_charm", 50)
                result.found_items.append(
                    "🍀 **Lucky Charm** found! Reduces disaster chance by 50% (50 uses)."
                )

            # 25% heart of leviathan on "Leviathan Scale" catch
            if catch["name"] == "Leviathan Scale" and random.random() < 0.25:
                self.repo.update_user_inventory(user_id, "heart_of_leviathan", 1)
                result.found_items.append(
                    "💜 **Heart of Leviathan** found! Fully protects your bank from one disaster."
                )

            return result

        # Unknown state
        self._cleanup_session(user_id)
        return PullResult(
            success=False,
            message="Something went wrong with your fishing session.",
        )

    def _roll_catch(self, bait_type: str, level: int = 1, jig_active: bool = False) -> dict:
        """
        Roll a catch based on bait tier, fishing level, and jig status.

        Bait rare_boost increases odds of rare/legendary catches.
        Jig active gives a flat 20% legendary chance.
        """
        bait_config = FISHING_BAIT_TIERS[bait_type]
        rare_boost = bait_config.rare_boost

        # Look up catch table from level config
        catch_table = FISH_LEVELS[level]["catches"]

        # Calculate adjusted weights
        common_weight = catch_table["common"].weight
        rare_weight = catch_table["rare"].weight * rare_boost
        legendary_weight = catch_table["legendary"].weight * rare_boost

        if jig_active:
            # Jig overrides to 20% legendary chance
            total = common_weight + rare_weight + legendary_weight
            legendary_weight = total * 0.20
            # Split remaining 80% proportionally between common and rare
            remaining = total * 0.80
            orig_non_leg = common_weight + rare_weight
            if orig_non_leg > 0:
                common_weight = remaining * (common_weight / orig_non_leg)
                rare_weight = remaining * (rare_weight / orig_non_leg)
            else:
                common_weight = remaining * 0.5
                rare_weight = remaining * 0.5

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
        catches = catch_table[rarity].catches
        catch_weights = [c.weight for c in catches]
        catch = random.choices(catches, weights=catch_weights, k=1)[0]

        return {
            "name": catch.name,
            "emoji": catch.emoji,
            "stars": catch.stars,
            "rarity": rarity,
        }

    def get_fish_level_info(self, user_id: int) -> FishLevelInfo:
        """Get level info for a user's fishing."""
        return FishLevelInfo(
            unlocked_level=self.repo.get_mine_level(user_id),
            active_level=self.repo.get_active_fish_level(user_id),
            levels=FISH_LEVELS,
        )

    def set_active_fish_level(self, user_id: int, level: int) -> tuple[bool, str]:
        """Switch active fishing level. Returns (success, message)."""
        if level < 1 or level > 5:
            return False, "Fishing levels range from 1 to 5."

        unlocked = self.repo.get_mine_level(user_id)
        if level > unlocked:
            return False, f"You haven't unlocked level {level} yet! Your highest unlocked level is {unlocked}. Unlock it with `!unlock {level}` in the mine."

        self.repo.set_active_fish_level(user_id, level)
        level_config = FISH_LEVELS[level]
        return True, f"Switched to **{level_config['emoji']} {level_config['name']}** (Level {level})!"

    def cancel_session(self, user_id: int) -> bool:
        """Cancel an active fishing session. Returns True if there was one."""
        if user_id in self._sessions:
            self._cleanup_session(user_id)
            return True
        return False

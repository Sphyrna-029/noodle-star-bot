"""Fishing use-cases for the fishing minigame.

Average Returns (per fish, varies by bait):
    Level 1 (Stream):    Worm: 35 | Herring: 45 | Sturgeon: 52 stars
    Level 2 (River):     Worm: 83 | Herring: 106 | Sturgeon: 123 stars
    Level 3 (Coral):     Worm: 158 | Herring: 201 | Sturgeon: 235 stars
    Level 4 (Shipwreck): Worm: 269 | Herring: 342 | Sturgeon: 399 stars  Bank risk: 10%
    Level 5 (Abyss):     Worm: 408 | Herring: 521 | Sturgeon: 607 stars  Bank risk: 20%

Bait Effects:
    - Worm (33 stars):     Base odds (1.0x rare boost)
    - Herring (79 stars):  1.5x rare/legendary boost
    - Sturgeon (110 stars): 2.0x rare/legendary boost

Ambush encounters trigger after catching with level-scaled chance (halved by Lucky Charm).

Rare Effect Items (dropped from fishing):
    - Golden Axe: 3% on rare/legendary catches, permanent Tier 3 weapon
    - Mithril Shield: 0.4% on any catch, permanent Tier 3 shield
    - Bucktail Jig: 0.3% on any catch, 20% legendary on next cast
    - Ray-Gun: 0.35% on any catch, 3 uses, alien abduction combat chance
    - Star Magnet: 1% on rare/legendary, 20 uses, +15% stars
    - Lucky Charm: 0.05% on any catch, 50 uses, 50% ambush chance reduction
    - Heart of Leviathan: 25% on Leviathan Scale catch, 1 use, bank protection
"""

import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from cogs.fishing.constants import (
    CATCH_TABLES,
    FISH_LEVELS,
    FISHING_BAIT_TIERS,
    FISHING_COOLDOWN,
)
from database.repository import UserRepository


from ..dto import (
    CastResult,
    EquipResult,
    FishLevelInfo,
    FishingSession,
    FishingState,
    FishingStatus,
    PullResult,
)


class FishingUseCases:
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

        cooldown_seconds = (
            int(FISHING_COOLDOWN.total_seconds())
            if isinstance(FISHING_COOLDOWN, timedelta)
            else int(FISHING_COOLDOWN)
        )
        cooldown_end = last_fish + timedelta(seconds=cooldown_seconds)
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

        bite_wait_min = int(bait_info.bite_wait_min.total_seconds())
        bite_wait_max = int(bait_info.bite_wait_max.total_seconds())
        pull_window = int(bait_info.pull_window.total_seconds())

        return EquipResult(
            success=True,
            message=f"Equipped {bait_info.emoji} **{bait_info.display_name}** bait!\n"
            f"Bite wait: {bite_wait_min}-{bite_wait_max}s | "
            f"Pull window: {pull_window}s | "
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
        return True, "**Bucktail Jig activated!** Your next cast has a **20% legendary catch chance**!"

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

        # Check inventory space before consuming bait
        bag_count = self.repo.get_inventory_count(user_id)
        bag_capacity = self.repo.get_inventory_capacity(user_id)
        if bag_count >= bag_capacity:
            return CastResult(
                success=False,
                message=f"Your inventory is full ({bag_count}/{bag_capacity})! Use `!sell` to make room before fishing.",
                inventory_full=True,
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
        min_wait = int(bait_config.bite_wait_min.total_seconds())
        max_wait = int(bait_config.bite_wait_max.total_seconds())
        pull_window = int(bait_config.pull_window.total_seconds())
        bite_wait = random.randint(min_wait, max_wait)

        now = datetime.now()
        bite_at = now + timedelta(seconds=bite_wait)
        # expires_at will be set when bite occurs
        expires_at = bite_at + timedelta(seconds=pull_window)

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
            self._schedule_bite(user_id, bite_wait, pull_window)
        )

        bait_info = FISHING_BAIT_TIERS[equipped_bait]
        level_config = FISH_LEVELS[active_level]
        jig_msg = " *Bucktail Jig active!*" if jig_active else ""
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
            early_pulls = self.repo.increment_achievement_progress(
                user_id, "fish_early_pulls", 1
            )
            unlocked_too_eager = False
            if early_pulls >= 1:
                unlocked_too_eager = self.repo.unlock_achievement(
                    user_id, "fish_too_early"
                )

            result = PullResult(
                success=False,
                message="You pulled too early! The fish wasn't biting yet. "
                "Your line snapped and you lost your bait.",
            )
            if unlocked_too_eager:
                result.extra_messages.append(
                    "🏆 **Achievement unlocked:** 🎣 **Too Eager**"
                )
            return result

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

            # Calculate reward value (keep Star Magnet boost)
            reward = catch["stars"]
            star_magnet_uses = inventory["star_magnet"]
            if star_magnet_uses > 0 and reward > 0:
                reward = math.ceil(reward * 1.15)
                self.repo.update_user_inventory(user_id, "star_magnet", star_magnet_uses - 1)

            # Add catch to inventory instead of awarding stars
            catch_key = catch["name"].lower().replace(" ", "_").replace("'", "")
            self.repo.add_item(user_id, catch_key, "fish", reward)
            bag_count = self.repo.get_inventory_count(user_id)
            bag_capacity = self.repo.get_inventory_capacity(user_id)

            current_stars = self.repo.get_user_stars(user_id, username)
            new_stars = current_stars  # No star change from fishing
            fish_catches = self.repo.increment_achievement_progress(
                user_id, "fish_catches", 1
            )
            unlocked_fish_10 = False
            unlocked_fish_100 = False
            if fish_catches >= 10:
                unlocked_fish_10 = self.repo.unlock_achievement(user_id, "fish_10")
            if fish_catches >= 100:
                unlocked_fish_100 = self.repo.unlock_achievement(user_id, "fish_100")

            result = PullResult(
                success=True,
                message=f"You caught a {catch['emoji']} **{catch['name']}**!",
                catch_name=catch["name"],
                catch_emoji=catch["emoji"],
                catch_rarity=catch["rarity"],
                stars_earned=reward,
                new_balance=new_stars,
                item_sell_value=reward,
                bag_count=bag_count,
                bag_capacity=bag_capacity,
                level_name=level_config["name"],
                level_emoji=level_config["emoji"],
            )
            if unlocked_fish_10:
                result.extra_messages.append(
                    "🏆 **Achievement unlocked:** 🐟 **Lake Regular**"
                )
            if unlocked_fish_100:
                result.extra_messages.append(
                    "🏆 **Achievement unlocked:** 🐠 **Ocean Veteran**"
                )

            # Check for ambush (chance varies by level, halved by lucky charm)
            ambush_chance = level_config.get("disaster_chance", 0)
            if ambush_chance > 0:
                lucky_charm_uses = inventory.get("lucky_charm", 0)
                used_lucky_charm = False
                if lucky_charm_uses > 0:
                    ambush_chance *= 0.5
                    used_lucky_charm = True

                if random.random() < ambush_chance:
                    if used_lucky_charm:
                        self.repo.update_user_inventory(user_id, "lucky_charm", lucky_charm_uses - 1)

                    from cogs.combat.ambush_constants import FISHING_AMBUSH_MOBS
                    mobs = FISHING_AMBUSH_MOBS.get(active_level, [])
                    if mobs:
                        mob = random.choice(mobs)
                        result.ambush_mob_key = mob.key
                        result.ambush_mob_name = mob.name
                        result.ambush_mob_emoji = mob.emoji
                        result.ambush_activity = "fishing"
                        result.ambush_level = active_level

            # ---------------------------------------------------------------
            # Roll for item drops (after disaster resolution)
            # ---------------------------------------------------------------

            # 3% golden axe on rare/legendary catches (permanent combat weapon)
            if catch["rarity"] in ("rare", "legendary") and random.random() < 0.03:
                cur_axe = self.repo.get_user_inventory(user_id)["golden_axe"]
                if cur_axe <= 0:
                    self.repo.update_user_inventory(user_id, "golden_axe", 1)
                    result.found_items.append(
                        "🪓 **Golden Axe** found! A Tier 3 combat weapon — equip with `!equip golden axe`."
                    )
                else:
                    # Already owns one — grant 250 stars instead
                    bonus = 250
                    new_stars = result.new_balance + bonus
                    self.repo.update_user_stars(user_id, username, new_stars)
                    result.new_balance = new_stars
                    result.found_items.append(
                        f"🪓 **Golden Axe** found! You already own one, sold for **{bonus}** stars."
                    )

            # 0.4% mithril shield on any catch (permanent combat shield)
            if random.random() < 0.004:
                cur_shield = self.repo.get_user_inventory(user_id)["mithril_shield"]
                if cur_shield <= 0:
                    self.repo.update_user_inventory(user_id, "mithril_shield", 1)
                    result.found_items.append(
                        "🛡️ **Mithril Shield** found! A Tier 3 combat shield — equip with `!equip mithril shield`."
                    )
                else:
                    bonus = 250
                    new_stars = result.new_balance + bonus
                    self.repo.update_user_stars(user_id, username, new_stars)
                    result.new_balance = new_stars
                    result.found_items.append(
                        f"🛡️ **Mithril Shield** found! You already own one, sold for **{bonus}** stars."
                    )

            # 0.3% bucktail jig on any catch
            if random.random() < 0.003:
                cur_jig = self.repo.get_user_inventory(user_id)["bucktail_jig"]
                self.repo.update_user_inventory(user_id, "bucktail_jig", cur_jig + 1)
                result.found_items.append(
                    "**Bucktail Jig** found! Use `!use jig` for 20% legendary chance on next cast."
                )

            # 0.35% ray-gun on any catch
            if random.random() < 0.0035:
                cur_gun = self.repo.get_user_inventory(user_id)["ray_gun"]
                self.repo.update_user_inventory(user_id, "ray_gun", cur_gun + 3)
                result.found_items.append(
                    "**Ray-Gun** found! Protects your items from alien abduction (3 uses)."
                )

            # 1% star magnet on rare or legendary catches
            if catch["rarity"] in ("rare", "legendary") and random.random() < 0.01:
                cur_magnet = self.repo.get_user_inventory(user_id)["star_magnet"]
                self.repo.update_user_inventory(user_id, "star_magnet", cur_magnet + 20)
                result.found_items.append(
                    "**Star Magnet** found! +15% stars on mining and fishing (20 uses)."
                )

            # 0.05% lucky charm on any catch
            if random.random() < 0.0005:
                cur_charm = self.repo.get_user_inventory(user_id)["lucky_charm"]
                self.repo.update_user_inventory(user_id, "lucky_charm", cur_charm + 50)
                result.found_items.append(
                    "**Lucky Charm** found! Reduces disaster chance by 50% (50 uses)."
                )

            # 25% heart of leviathan on "Leviathan Scale" catch
            if catch["name"] == "Leviathan Scale" and random.random() < 0.25:
                cur_heart = self.repo.get_user_inventory(user_id)["heart_of_leviathan"]
                self.repo.update_user_inventory(user_id, "heart_of_leviathan", cur_heart + 1)
                result.found_items.append(
                    "**Heart of Leviathan** found! Fully protects your bank from one disaster."
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

        # Look up catch table from CATCH_TABLES
        catch_table = CATCH_TABLES[level]

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

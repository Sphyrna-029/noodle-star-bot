"""Mining service with cooldowns, disasters, and mine levels."""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from config import (
    MINE_LEVELS,
    MINERALS_GOLD_PICKAXE,
    MINERALS_NORMAL,
    MINING_BASE_COOLDOWN,
    MINING_NOODLE_COOLDOWN,
    MINING_NOODLE_RUNE_COOLDOWN,
    MINING_POTATO_COOLDOWN,
    MINING_RUNE_COOLDOWN,
    MINING_RUNE_POTATO_COOLDOWN,
)
from config.models import MineHazard
from database.repository import UserRepository
from utils.formatters import format_time_remaining

# Gold pickaxe shop price (for auto-sell at half)
_GOLD_PICKAXE_PRICE = 500


@dataclass
class MineResult:
    """Result of a mining operation."""

    success: bool
    message: str
    mineral_name: str = ""
    mineral_emoji: str = ""
    stars_earned: int = 0
    new_balance: int = 0
    disaster: Optional[str] = None
    disaster_protected: bool = False
    disaster_header: str = ""
    disaster_protected_msg: str = ""
    disaster_unprotected_msg: str = ""
    stars_lost: int = 0
    bank_lost: int = 0
    items_destroyed: bool = False
    extra_messages: List[str] = field(default_factory=list)
    level_name: str = ""
    level_emoji: str = ""
    found_items: List[str] = field(default_factory=list)


@dataclass
class UnlockResult:
    """Result of unlocking a mine level."""

    success: bool
    message: str
    level: int = 0
    cost: int = 0


@dataclass
class LevelInfo:
    """Info about a user's mine levels."""

    unlocked_level: int
    active_level: int
    levels: dict  # reference to MINE_LEVELS


class MiningService:
    """Handles all mining-related business logic."""

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repo = repository or UserRepository()

    def can_mine(self, user_id: int) -> bool:
        """Check if user can mine (cooldown expired)."""
        last_mine = self.repo.get_last_mine(user_id)
        if last_mine is None:
            return True

        time_since = datetime.now() - last_mine
        return time_since >= MINING_BASE_COOLDOWN

    def get_cooldown_remaining(self, user_id: int) -> Optional[timedelta]:
        """Get time remaining on cooldown, or None if can mine."""
        last_mine = self.repo.get_last_mine(user_id)
        if last_mine is None:
            return None

        time_since = datetime.now() - last_mine
        cooldown = MINING_BASE_COOLDOWN

        if time_since >= cooldown:
            return None

        return cooldown - time_since

    def get_potato_cooldown_remaining(self, user_id: int) -> Optional[timedelta]:
        """Get time remaining for potato-reduced cooldown."""
        last_mine = self.repo.get_last_mine(user_id)
        if last_mine is None:
            return None

        time_since = datetime.now() - last_mine
        cooldown = MINING_POTATO_COOLDOWN

        if time_since >= cooldown:
            return None

        return cooldown - time_since

    def mine(self, user_id: int, username: str, use_item: str = "") -> MineResult:
        """
        Execute mining with all logic.

        Args:
            user_id: Discord user ID
            username: Discord username
            use_item: Optional item to use ("potato", "mushroom", or "noodle")

        Returns:
            MineResult with outcome
        """
        inventory = self.repo.get_user_inventory(user_id)
        has_rune = inventory["rune_fragment"] > 0

        # Check if using golden mushroom
        using_mushroom = False
        if use_item and use_item.lower() in [
            "mushroom",
            "golden mushroom",
            "goldenmushroom",
        ]:
            if inventory["golden_mushroom"] <= 0:
                return MineResult(
                    success=False,
                    message="You don't have any golden mushrooms!",
                )
            using_mushroom = True
            # Remove mushroom from inventory
            self.repo.update_user_inventory(
                user_id, "golden_mushroom", inventory["golden_mushroom"] - 1
            )

        # Get last mine time
        last_mine = self.repo.get_last_mine(user_id)
        now = datetime.now()

        # Check cooldown (skip if using mushroom)
        if not using_mushroom and last_mine is not None:
            time_since = now - last_mine

            use_lower = use_item.lower() if use_item else ""

            # Check if using fossilized noodle
            if use_lower in ["noodle", "fossilized noodle", "fossilizednoodle"]:
                if inventory["fossilized_noodle"] <= 0:
                    return MineResult(
                        success=False,
                        message="You don't have any fossilized noodles!",
                    )

                noodle_cd = MINING_NOODLE_RUNE_COOLDOWN if has_rune else MINING_NOODLE_COOLDOWN
                if time_since < noodle_cd:
                    remaining = noodle_cd - time_since
                    return MineResult(
                        success=False,
                        message=f"Even with a fossilized noodle, you need to wait!\nCome back in **{format_time_remaining(remaining)}** to mine again!",
                    )

                # Consume noodle (and rune use if applicable)
                self.repo.update_user_inventory(
                    user_id, "fossilized_noodle", inventory["fossilized_noodle"] - 1
                )
                if has_rune:
                    self.repo.update_user_inventory(
                        user_id, "rune_fragment", inventory["rune_fragment"] - 1
                    )

            # Check if using potato
            elif use_lower in ["potato", "raw potato", "rawpotato"]:
                if inventory["raw_potato"] <= 0:
                    return MineResult(
                        success=False,
                        message="You don't have any raw potatoes!",
                    )

                potato_cd = MINING_RUNE_POTATO_COOLDOWN if has_rune else MINING_POTATO_COOLDOWN
                if time_since < potato_cd:
                    remaining = potato_cd - time_since
                    return MineResult(
                        success=False,
                        message=f"Even with a raw potato, you need to wait!\nCome back in **{format_time_remaining(remaining)}** to mine again!",
                    )

                # Remove potato from inventory (and rune use if applicable)
                self.repo.update_user_inventory(
                    user_id, "raw_potato", inventory["raw_potato"] - 1
                )
                if has_rune:
                    self.repo.update_user_inventory(
                        user_id, "rune_fragment", inventory["rune_fragment"] - 1
                    )

            else:
                # Normal cooldown (reduced by rune fragment)
                base_cd = MINING_RUNE_COOLDOWN if has_rune else MINING_BASE_COOLDOWN
                if time_since < base_cd:
                    remaining = base_cd - time_since
                    rune_hint = ""
                    if not has_rune:
                        rune_hint = ""
                    return MineResult(
                        success=False,
                        message=f"You're too tired to mine right now!\nCome back in **{format_time_remaining(remaining)}** to mine again!\n💡 *Use `!mine potato` to reduce cooldown or `!mine mushroom` to mine instantly!*",
                    )

                # Consume rune use for standard mine
                if has_rune:
                    self.repo.update_user_inventory(
                        user_id, "rune_fragment", inventory["rune_fragment"] - 1
                    )

        # Get active mine level config
        active_level = self.repo.get_active_mine_level(user_id)
        level_config = MINE_LEVELS[active_level]

        has_gold_pickaxe = inventory["gold_pickaxe"] > 0
        has_helmet = inventory["helmet"] > 0
        has_sword = inventory["sword"] > 0

        # Select minerals based on pickaxe and level
        minerals = level_config["minerals_gold"] if has_gold_pickaxe else level_config["minerals_normal"]

        # Select random mineral based on weights
        mineral = random.choices(minerals, weights=[m.weight for m in minerals])[0]

        # Give reward (star magnet boosts by 15%)
        reward = mineral.stars
        star_magnet_uses = inventory["star_magnet"]
        if star_magnet_uses > 0 and reward > 0:
            reward = math.ceil(reward * 1.15)
            self.repo.update_user_inventory(user_id, "star_magnet", star_magnet_uses - 1)

        current_stars = self.repo.get_user_stars(user_id, username)
        new_stars = current_stars + reward

        # Update stars and last mine time
        self.repo.update_user_stars(user_id, username, new_stars)
        self.repo.update_last_mine(user_id)

        result = MineResult(
            success=True,
            message="Mining complete",
            mineral_name=mineral.name,
            mineral_emoji=mineral.emoji,
            stars_earned=reward,
            new_balance=new_stars,
            level_name=level_config["name"],
            level_emoji=level_config["emoji"],
        )

        # Check for disaster (chance varies by level, halved by lucky charm)
        disaster_chance = level_config["disaster_chance"]
        lucky_charm_uses = inventory["lucky_charm"]
        used_lucky_charm = False
        if lucky_charm_uses > 0:
            disaster_chance *= 0.5
            used_lucky_charm = True

        if random.random() < disaster_chance:
            # Consume lucky charm use (it was active but disaster still happened)
            if used_lucky_charm:
                self.repo.update_user_inventory(user_id, "lucky_charm", lucky_charm_uses - 1)

            hazard: MineHazard = random.choice(level_config["hazards"])
            result.disaster = hazard.name
            result.disaster_header = hazard.header

            # Re-read inventory in case rune was consumed above
            inv = self.repo.get_user_inventory(user_id)
            golden_axe_uses = inv["golden_axe"]
            mithril_shield_uses = inv["mithril_shield"]
            has_helmet = inv["helmet"] > 0
            has_sword = inv["sword"] > 0

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

        # 0.5% rune fragment
        if random.random() < 0.005:
            self.repo.update_user_inventory(user_id, "rune_fragment", 5)
            result.found_items.append(
                "🪨 **Rune Fragment** — Reduces mining cooldowns for 5 uses!"
            )

        # 0.5% fossilized noodle
        if random.random() < 0.005:
            self.repo.update_user_inventory(user_id, "fossilized_noodle", 5)
            result.found_items.append(
                "🍜 **Fossilized Noodle** — Use `!mine noodle` for a 1 min cooldown! (5 uses)"
            )

        # 0.2% golden pickaxe
        if random.random() < 0.002:
            if inventory["gold_pickaxe"] > 0:
                # Auto-sell for half price
                sell_price = _GOLD_PICKAXE_PRICE // 2
                new_stars = result.new_balance + sell_price
                self.repo.update_user_stars(user_id, username, new_stars)
                result.new_balance = new_stars
                result.found_items.append(
                    f"⛏️ **Gold Pickaxe** found! You already have one, so it sold for **{sell_price}** stars."
                )
            else:
                self.repo.update_user_inventory(user_id, "gold_pickaxe", 1)
                result.found_items.append(
                    "⛏️ **Gold Pickaxe** found! Permanently increases mining luck!"
                )

        # 1% sword
        if random.random() < 0.01:
            cur_sword = self.repo.get_user_inventory(user_id)["sword"]
            self.repo.update_user_inventory(user_id, "sword", cur_sword + 1)
            result.found_items.append(
                "⚔️ **Sword** found! Protects against one sword-type hazard."
            )

        # 1% helmet
        if random.random() < 0.01:
            cur_helmet = self.repo.get_user_inventory(user_id)["helmet"]
            self.repo.update_user_inventory(user_id, "helmet", cur_helmet + 1)
            result.found_items.append(
                "🪖 **Mining Helmet** found! Protects against one helmet-type hazard."
            )

        return result

    def unlock_level(self, user_id: int, username: str, level: int) -> UnlockResult:
        """Unlock a new mine level."""
        if level < 2 or level > 5:
            return UnlockResult(
                success=False,
                message="Mine levels range from 1 to 5. You can unlock levels 2-5.",
            )

        current_unlocked = self.repo.get_mine_level(user_id)

        if level <= current_unlocked:
            return UnlockResult(
                success=False,
                message=f"You've already unlocked level {level}!",
            )

        if level != current_unlocked + 1:
            return UnlockResult(
                success=False,
                message=f"You need to unlock level {current_unlocked + 1} first!",
            )

        cost = MINE_LEVELS[level]["cost"]
        current_stars = self.repo.get_user_stars(user_id, username)

        if current_stars < cost:
            return UnlockResult(
                success=False,
                message=f"You need **{cost}** stars to unlock level {level}, but you only have **{current_stars}**!",
            )

        # Deduct cost and unlock
        self.repo.update_user_stars(user_id, username, current_stars - cost)
        self.repo.set_mine_level(user_id, level)
        self.repo.set_active_mine_level(user_id, level)

        level_config = MINE_LEVELS[level]
        return UnlockResult(
            success=True,
            message=f"You unlocked **{level_config['emoji']} {level_config['name']}** (Level {level})!",
            level=level,
            cost=cost,
        )

    def get_level_info(self, user_id: int) -> LevelInfo:
        """Get level info for a user."""
        return LevelInfo(
            unlocked_level=self.repo.get_mine_level(user_id),
            active_level=self.repo.get_active_mine_level(user_id),
            levels=MINE_LEVELS,
        )

    def set_active_level(self, user_id: int, level: int) -> tuple[bool, str]:
        """Switch active mine level. Returns (success, message)."""
        if level < 1 or level > 5:
            return False, "Mine levels range from 1 to 5."

        unlocked = self.repo.get_mine_level(user_id)
        if level > unlocked:
            return False, f"You haven't unlocked level {level} yet! Your highest unlocked level is {unlocked}."

        self.repo.set_active_mine_level(user_id, level)
        level_config = MINE_LEVELS[level]
        return True, f"Switched to **{level_config['emoji']} {level_config['name']}** (Level {level})!"

    def use_potato(self, user_id: int) -> bool:
        """
        Use a potato for reduced cooldown.

        Returns True if potato was available and used.
        """
        inventory = self.repo.get_user_inventory(user_id)
        if inventory["raw_potato"] <= 0:
            return False

        self.repo.update_user_inventory(
            user_id, "raw_potato", inventory["raw_potato"] - 1
        )
        return True

    def use_mushroom(self, user_id: int) -> bool:
        """
        Use a mushroom for instant mine.

        Returns True if mushroom was available and used.
        """
        inventory = self.repo.get_user_inventory(user_id)
        if inventory["golden_mushroom"] <= 0:
            return False

        self.repo.update_user_inventory(
            user_id, "golden_mushroom", inventory["golden_mushroom"] - 1
        )
        return True

"""Mining service with cooldowns, ambush encounters, and mine levels.

Average Returns (per mine):
    Level 1 (Normal):        17.00 stars | (Gold Pickaxe): 21.50 stars
    Level 2 (Normal):        34.50 stars | (Gold Pickaxe): 44.00 stars
    Level 3 (Normal):        52.00 stars | (Gold Pickaxe): 67.50 stars
    Level 4 (Normal):        63.50 stars | (Gold Pickaxe): 88.00 stars  Bank risk: 10%
    Level 5 (Normal):        93.00 stars | (Gold Pickaxe): 128.00 stars Bank risk: 25%

Ambush encounters trigger after mining with level-scaled chance (halved by Lucky Charm).

Rare Effect Items (dropped from mining):
    - Rune Fragment: 0.5% drop, 30 uses, halves all mining cooldowns
    - Fossilized Noodle: 0.5% drop, 30 uses, 1 min cooldown (!mine noodle)
    - Golden Pickaxe: 0.2% drop, auto-sells for half if already owned

Shared Effect Items (from fishing drops, active in mining too):
    - Star Magnet: +15% stars on mine/fish
    - Lucky Charm: 50% ambush chance reduction
"""

import math
import random
from datetime import datetime
from typing import Optional

from cogs.mining.constants import (
    MINE_LEVELS,
    MINERAL_TABLES,
    MINING_BASE_COOLDOWN,
    MINING_NOODLE_COOLDOWN,
    MINING_NOODLE_RUNE_COOLDOWN,
    MINING_POTATO_COOLDOWN,
    MINING_RUNE_COOLDOWN,
    MINING_RUNE_POTATO_COOLDOWN,
)
from database.repository import UserRepository
from utils.formatters import format_time_remaining
from ..dto import LevelInfo, MineResult, UnlockResult

# Gold pickaxe shop price (for auto-sell at half)
_GOLD_PICKAXE_PRICE = 500


class MiningUseCases:
    """Handles all mining-related business logic."""

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repo = repository or UserRepository()

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

        # Check inventory space before consuming cooldown items
        bag_count = self.repo.get_inventory_count(user_id)
        bag_capacity = self.repo.get_inventory_capacity(user_id)
        if bag_count >= bag_capacity:
            return MineResult(
                success=False,
                message=f"your inventory is full ({bag_count}/{bag_capacity})! Use `!sell` to make room before mining.",
            )

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
                    return MineResult(
                        success=False,
                        message=f"You're too tired to mine right now!\nCome back in **{format_time_remaining(remaining)}** to mine again!\n*Use `!mine potato` to reduce cooldown or `!mine mushroom` (from farming harvests) to mine instantly!*",
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

        # Select minerals based on pickaxe and level
        mineral_table = MINERAL_TABLES[active_level]
        minerals = mineral_table["gold"] if has_gold_pickaxe else mineral_table["normal"]

        # Select random mineral based on weights
        mineral = random.choices(minerals, weights=[m.weight for m in minerals])[0]

        # Calculate reward value (Star Magnet still boosts the stored sell value)
        reward = mineral.stars
        star_magnet_uses = inventory["star_magnet"]
        if star_magnet_uses > 0 and reward > 0:
            reward = math.ceil(reward * 1.15)
            self.repo.update_user_inventory(user_id, "star_magnet", star_magnet_uses - 1)

        # Add resource to inventory instead of awarding stars directly
        self.repo.add_item(user_id, mineral.name.lower().replace(" ", "_"), "mineral", reward)
        bag_count = self.repo.get_inventory_count(user_id)
        bag_capacity = self.repo.get_inventory_capacity(user_id)

        current_stars = self.repo.get_user_stars(user_id, username)
        new_stars = current_stars  # No star change from mining itself

        self.repo.update_last_mine(user_id)
        mine_runs = self.repo.increment_achievement_progress(user_id, "mine_runs", 1)
        unlocked_mine_100 = False
        unlocked_mine_1000 = False
        if mine_runs >= 100:
            unlocked_mine_100 = self.repo.unlock_achievement(user_id, "mine_100")
        if mine_runs >= 1000:
            unlocked_mine_1000 = self.repo.unlock_achievement(user_id, "mine_1000")

        result = MineResult(
            success=True,
            message="Mining complete",
            mineral_name=mineral.name,
            mineral_emoji=mineral.emoji,
            stars_earned=reward,
            new_balance=new_stars,
            level_name=level_config["name"],
            level_emoji=level_config["emoji"],
            item_sell_value=reward,
            bag_count=bag_count,
            bag_capacity=bag_capacity,
        )
        if unlocked_mine_100:
            result.extra_messages.append(
                "🏆 **Achievement unlocked:** 💎 **Centurion Miner**"
            )
        if unlocked_mine_1000:
            result.extra_messages.append(
                "🏆 **Achievement unlocked:** 👑 **Mining Legend**"
            )

        # Check for ambush (chance varies by level, halved by lucky charm)
        ambush_chance = level_config["disaster_chance"]
        lucky_charm_uses = inventory["lucky_charm"]
        used_lucky_charm = False
        if lucky_charm_uses > 0:
            ambush_chance *= 0.5
            used_lucky_charm = True

        if random.random() < ambush_chance:
            if used_lucky_charm:
                self.repo.update_user_inventory(user_id, "lucky_charm", lucky_charm_uses - 1)

            from cogs.combat.ambush_constants import MINING_AMBUSH_MOBS
            mobs = MINING_AMBUSH_MOBS.get(active_level, [])
            if mobs:
                mob = random.choice(mobs)
                result.ambush_mob_key = mob.key
                result.ambush_mob_name = mob.name
                result.ambush_mob_emoji = mob.emoji
                result.ambush_activity = "mining"
                result.ambush_level = active_level

        # ---------------------------------------------------------------
        # Roll for item drops (after disaster resolution)
        # ---------------------------------------------------------------

        # 0.5% rune fragment
        if random.random() < 0.005:
            cur_rune = self.repo.get_user_inventory(user_id)["rune_fragment"]
            self.repo.update_user_inventory(user_id, "rune_fragment", cur_rune + 30)
            result.found_items.append(
                "**Rune Fragment** -- Reduces mining cooldowns for 30 uses!"
            )

        # 0.5% fossilized noodle
        if random.random() < 0.005:
            cur_noodle = self.repo.get_user_inventory(user_id)["fossilized_noodle"]
            self.repo.update_user_inventory(user_id, "fossilized_noodle", cur_noodle + 30)
            result.found_items.append(
                "**Fossilized Noodle** -- Use `!mine noodle` for a 1 min cooldown! (30 uses)"
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
                    f"**Gold Pickaxe** found! You already have one, so it sold for **{sell_price}** stars."
                )
            else:
                self.repo.update_user_inventory(user_id, "gold_pickaxe", 1)
                result.found_items.append(
                    "**Gold Pickaxe** found! Permanently increases mining luck!"
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


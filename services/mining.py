"""Mining service with cooldowns and disasters."""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from config import (
    MINERALS_GOLD_PICKAXE,
    MINERALS_NORMAL,
    MINING_BASE_COOLDOWN,
    MINING_COLLAPSE_LOSS_PERCENT,
    MINING_DISASTER_CHANCE,
    MINING_GOBLIN_LOSS_PERCENT,
    MINING_POTATO_COOLDOWN,
)
from database.repository import UserRepository
from utils.formatters import format_time_remaining


@dataclass
class MineResult:
    """Result of a mining operation."""

    success: bool
    message: str
    mineral_name: str = ""
    mineral_emoji: str = ""
    stars_earned: int = 0
    new_balance: int = 0
    disaster: Optional[str] = None  # "collapse" or "goblin" or None
    disaster_protected: bool = False
    stars_lost: int = 0
    items_destroyed: bool = False
    extra_messages: List[str] = field(default_factory=list)


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
        return time_since >= timedelta(minutes=MINING_BASE_COOLDOWN)

    def get_cooldown_remaining(self, user_id: int) -> Optional[timedelta]:
        """Get time remaining on cooldown, or None if can mine."""
        last_mine = self.repo.get_last_mine(user_id)
        if last_mine is None:
            return None

        time_since = datetime.now() - last_mine
        cooldown = timedelta(minutes=MINING_BASE_COOLDOWN)

        if time_since >= cooldown:
            return None

        return cooldown - time_since

    def get_potato_cooldown_remaining(self, user_id: int) -> Optional[timedelta]:
        """Get time remaining for potato-reduced cooldown."""
        last_mine = self.repo.get_last_mine(user_id)
        if last_mine is None:
            return None

        time_since = datetime.now() - last_mine
        cooldown = timedelta(minutes=MINING_POTATO_COOLDOWN)

        if time_since >= cooldown:
            return None

        return cooldown - time_since

    def mine(self, user_id: int, username: str, use_item: str = "") -> MineResult:
        """
        Execute mining with all logic.

        Args:
            user_id: Discord user ID
            username: Discord username
            use_item: Optional item to use ("potato" or "mushroom")

        Returns:
            MineResult with outcome
        """
        inventory = self.repo.get_user_inventory(user_id)

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

            # Check if using potato
            if use_item and use_item.lower() in ["potato", "raw potato", "rawpotato"]:
                if inventory["raw_potato"] <= 0:
                    return MineResult(
                        success=False,
                        message="You don't have any raw potatoes!",
                    )

                # Potato reduces cooldown to 5 minutes
                if time_since < timedelta(minutes=MINING_POTATO_COOLDOWN):
                    remaining = (
                        timedelta(minutes=MINING_POTATO_COOLDOWN) - time_since
                    )
                    return MineResult(
                        success=False,
                        message=f"Even with a raw potato, you need to wait!\nCome back in **{format_time_remaining(remaining)}** to mine again!",
                    )

                # Remove potato from inventory
                self.repo.update_user_inventory(
                    user_id, "raw_potato", inventory["raw_potato"] - 1
                )
            else:
                # Normal 30 minute cooldown
                if time_since < timedelta(minutes=MINING_BASE_COOLDOWN):
                    remaining = (
                        timedelta(minutes=MINING_BASE_COOLDOWN) - time_since
                    )
                    return MineResult(
                        success=False,
                        message=f"You're too tired to mine right now!\nCome back in **{format_time_remaining(remaining)}** to mine again!\n💡 *Use `!mine potato` to reduce cooldown or `!mine mushroom` to mine instantly!*",
                    )

        has_gold_pickaxe = inventory["gold_pickaxe"] > 0
        has_helmet = inventory["helmet"] > 0
        has_sword = inventory["sword"] > 0

        # Select minerals based on pickaxe
        minerals = MINERALS_GOLD_PICKAXE if has_gold_pickaxe else MINERALS_NORMAL

        # Select random mineral based on weights
        mineral = random.choices(minerals, weights=[m.weight for m in minerals])[0]

        # Give reward
        reward = mineral.stars
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
        )

        # Check for disaster (10% chance)
        if random.random() < MINING_DISASTER_CHANCE:
            disaster_type = random.choice(["collapse", "goblin"])

            if disaster_type == "collapse":
                result.disaster = "collapse"
                if has_helmet:
                    result.disaster_protected = True
                    # Remove helmet
                    self.repo.update_user_inventory(user_id, "helmet", 0)
                else:
                    # Lose 50% of wallet and all items
                    stars_lost = new_stars // 2
                    new_stars = new_stars - stars_lost
                    self.repo.update_user_stars(user_id, username, new_stars)
                    self.repo.clear_user_inventory(user_id)
                    result.stars_lost = stars_lost
                    result.items_destroyed = True
                    result.new_balance = new_stars

            else:  # goblin
                result.disaster = "goblin"
                if has_sword:
                    result.disaster_protected = True
                    # Remove sword
                    self.repo.update_user_inventory(user_id, "sword", 0)
                else:
                    # Lose 75% of wallet and all items
                    stars_lost = int(new_stars * MINING_GOBLIN_LOSS_PERCENT)
                    new_stars = new_stars - stars_lost
                    self.repo.update_user_stars(user_id, username, new_stars)
                    self.repo.clear_user_inventory(user_id)
                    result.stars_lost = stars_lost
                    result.items_destroyed = True
                    result.new_balance = new_stars

        return result

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

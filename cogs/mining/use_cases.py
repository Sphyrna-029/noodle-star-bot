"""Mining service with cooldowns, disasters, and mine levels.

Average Returns (per mine):
    Level 1 (Normal):        17.00 stars | (Gold Pickaxe): 21.50 stars
    Level 2 (Normal):        34.50 stars | (Gold Pickaxe): 44.00 stars
    Level 3 (Normal):        52.00 stars | (Gold Pickaxe): 67.50 stars
    Level 4 (Normal):        63.50 stars | (Gold Pickaxe): 88.00 stars  ⚠️ Bank risk: 10%
    Level 5 (Normal):        93.00 stars | (Gold Pickaxe): 128.00 stars ⚠️ Bank risk: 25%

Disaster Chances:
    Levels 1-3: 3% chance
    Level 4:    5% chance (Lava Flow - 10% bank loss)
    Level 5:    8% chance (Shadow Wraith - 25% bank loss)

Protection:
    - Helmet: Protects from mine collapse and lava flow
    - Sword: Protects from goblin raids and shadow wraith
    - Mithril Shield: 10 uses, protects from helmet-type disasters
    - Golden Axe: 50 uses, protects from sword-type disasters
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from cogs.mining.constants import (
    MINE_LEVELS,
    MINERAL_TABLES,
    MINING_BASE_COOLDOWN,
    MINING_POTATO_COOLDOWN,
)
from config.models import MineHazard
from database.repository import UserRepository
from utils.formatters import format_time_remaining
from .dto import LevelInfo, MineResult, UnlockResult


class MiningUseCases:
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
                if time_since < MINING_POTATO_COOLDOWN:
                    remaining = MINING_POTATO_COOLDOWN - time_since
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
                if time_since < MINING_BASE_COOLDOWN:
                    remaining = MINING_BASE_COOLDOWN - time_since
                    return MineResult(
                        success=False,
                        message=f"You're too tired to mine right now!\nCome back in **{format_time_remaining(remaining)}** to mine again!\n💡 *Use `!mine potato` to reduce cooldown or `!mine mushroom` (from farming harvests) to mine instantly!*",
                    )

        # Get active mine level config
        active_level = self.repo.get_active_mine_level(user_id)
        level_config = MINE_LEVELS[active_level]

        has_gold_pickaxe = inventory["gold_pickaxe"] > 0
        has_helmet = inventory["helmet"] > 0
        has_sword = inventory["sword"] > 0

        # Select minerals based on pickaxe and level
        mineral_table = MINERAL_TABLES[active_level]
        minerals = mineral_table["gold"] if has_gold_pickaxe else mineral_table["normal"]

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
            level_name=level_config["name"],
            level_emoji=level_config["emoji"],
        )

        # Check for disaster (chance varies by level)
        if random.random() < level_config["disaster_chance"]:
            hazard: MineHazard = random.choice(level_config["hazards"])
            result.disaster = hazard.name
            result.disaster_header = hazard.header

            golden_axe_uses = inventory["golden_axe"]
            mithril_shield_uses = inventory["mithril_shield"]

            # Siren and Leviathan require special items only
            requires_special = hazard.name in ("siren", "leviathan")

            # Determine protection
            # Regular items are consumed first; special items are fallback
            # Siren/Leviathan ignore regular helmet/sword entirely
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

                # Calculate bank loss if applicable
                bank_lost = 0
                bank_insurance_used = False
                if hazard.bank_loss_pct > 0:
                    current_bank = self.repo.get_user_bank(user_id)
                    potential_bank_loss = int(current_bank * hazard.bank_loss_pct)

                    # Check if user has bank insurance
                    inventory = self.repo.get_user_inventory(user_id)
                    bank_insurance_uses = inventory.get("bank_insurance", 0)
                    if bank_insurance_uses > 0 and potential_bank_loss > 0:
                        # Bank insurance protects the bank
                        bank_insurance_used = True
                        self.repo.update_user_inventory(user_id, "bank_insurance", bank_insurance_uses - 1)
                        bank_lost = 0  # Bank is protected
                    else:
                        # No insurance, apply bank loss
                        bank_lost = potential_bank_loss
                        if bank_lost > 0:
                            self.repo.update_user_bank(user_id, username, current_bank - bank_lost)

                self.repo.clear_user_inventory(user_id)
                result.stars_lost = stars_lost
                result.bank_lost = bank_lost
                result.items_destroyed = True
                result.new_balance = new_stars

                # Update disaster message to indicate bank insurance usage
                disaster_msg = hazard.unprotected_msg.format(
                    stars_lost=stars_lost, bank_lost=bank_lost
                )
                if bank_insurance_used:
                    remaining_insurance = bank_insurance_uses - 1
                    disaster_msg += f"\n\n🛡️ **Bank Insurance activated!** Your bank was protected from losing {potential_bank_loss} stars.\n*({remaining_insurance} uses remaining)*"

                result.disaster_unprotected_msg = disaster_msg

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

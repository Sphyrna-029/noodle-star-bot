"""Space mining service with planets, disasters, and space ores.

Average Returns (per mine, normal pickaxe):
    Moon (Planet 1):   ~132 stars
    Mars (Planet 2):   ~190 stars
    Saturn (Planet 3): ~264 stars
    Uranus (Planet 4): ~366 stars
    Pluto (Planet 5):  ~511 stars

Disaster Chances:
    Moon:   12%
    Mars:   14%
    Saturn: 16% (Solar Flare - 10% bank, Black Hole - 15% bank)
    Uranus: 18% (Solar Flare - 10% bank, Black Hole - 15% bank)
    Pluto:  22% (Void Entity - 30% bank)

Protection:
    - Helmet: Protects from meteor strikes and solar flares
    - Sword: Protects from space pirates, black hole rifts, and void entities
    - Mithril Shield: Multi-use helmet protection
    - Golden Axe: Multi-use sword protection
"""

import random
from datetime import datetime
from typing import Optional

from cogs.mining.constants import MINING_BASE_COOLDOWN, MINING_POTATO_COOLDOWN
from cogs.space.constants import SPACE_MINERAL_TABLES, SPACE_PLANETS
from config.models import MineHazard
from database.repository import UserRepository
from utils.formatters import format_time_remaining
from ..dto import LaunchResult, PlanetInfo, PlanetUnlockResult, SpaceMineResult


class SpaceUseCases:
    """Handles all space mining business logic."""

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repo = repository or UserRepository()

    def has_launched(self, user_id: int) -> bool:
        """Check if user has launched into space."""
        return self.repo.get_space_planet_level(user_id) > 0

    def launch(self, user_id: int, username: str) -> LaunchResult:
        """Launch into space. Requires rocket ship and mine level 5."""
        inventory = self.repo.get_user_inventory(user_id)

        if inventory.get("rocket_ship", 0) <= 0:
            return LaunchResult(
                success=False,
                message="You don't have a rocket ship! Buy one from the `!store` first.",
            )

        mine_level = self.repo.get_mine_level(user_id)
        if mine_level < 5:
            return LaunchResult(
                success=False,
                message=f"You need mine level 5 to launch into space! You're at level {mine_level}.",
            )

        if self.has_launched(user_id):
            return LaunchResult(
                success=False,
                message="You've already launched into space! Use `!spacemine` to mine and `!planets` to view planets.",
            )

        # Set space planet level to 1 (Moon unlocked) and active planet to 1
        self.repo.set_space_planet_level(user_id, 1)
        self.repo.set_active_space_planet(user_id, 1)

        return LaunchResult(
            success=True,
            message="You've launched into space! The Moon is now available for mining.",
        )

    def mine(self, user_id: int, username: str, use_item: str = "") -> SpaceMineResult:
        """Mine on the active space planet. Shares cooldown with regular mining."""
        if not self.has_launched(user_id):
            return SpaceMineResult(
                success=False,
                message="You haven't launched into space yet! Use `!launch` first.",
            )

        inventory = self.repo.get_user_inventory(user_id)

        # Check inventory space
        bag_count = self.repo.get_inventory_count(user_id)
        bag_capacity = self.repo.get_inventory_capacity(user_id)
        if bag_count >= bag_capacity:
            return SpaceMineResult(
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
                return SpaceMineResult(
                    success=False,
                    message="You don't have any golden mushrooms!",
                )
            using_mushroom = True
            self.repo.update_user_inventory(
                user_id, "golden_mushroom", inventory["golden_mushroom"] - 1
            )

        # Get last mine time (shared cooldown)
        last_mine = self.repo.get_last_mine(user_id)
        now = datetime.now()

        # Check cooldown (skip if using mushroom)
        if not using_mushroom and last_mine is not None:
            time_since = now - last_mine

            # Check if using potato
            if use_item and use_item.lower() in ["potato", "raw potato", "rawpotato"]:
                if inventory["raw_potato"] <= 0:
                    return SpaceMineResult(
                        success=False,
                        message="You don't have any raw potatoes!",
                    )

                if time_since < MINING_POTATO_COOLDOWN:
                    remaining = MINING_POTATO_COOLDOWN - time_since
                    return SpaceMineResult(
                        success=False,
                        message=f"Even with a raw potato, you need to wait!\nCome back in **{format_time_remaining(remaining)}** to mine again!",
                    )

                self.repo.update_user_inventory(
                    user_id, "raw_potato", inventory["raw_potato"] - 1
                )
            else:
                if time_since < MINING_BASE_COOLDOWN:
                    remaining = MINING_BASE_COOLDOWN - time_since
                    return SpaceMineResult(
                        success=False,
                        message=f"You're too tired to mine right now!\nCome back in **{format_time_remaining(remaining)}** to mine again!\n💡 *Use `!spacemine potato` to reduce cooldown or `!spacemine mushroom` (from farming harvests) to mine instantly!*",
                    )

        # Get active planet config
        active_planet = self.repo.get_active_space_planet(user_id)
        planet_config = SPACE_PLANETS[active_planet]

        has_gold_pickaxe = inventory["gold_pickaxe"] > 0
        has_helmet = inventory["helmet"] > 0
        has_sword = inventory["sword"] > 0

        # Select minerals based on pickaxe and planet
        mineral_table = SPACE_MINERAL_TABLES[active_planet]
        minerals = mineral_table["gold"] if has_gold_pickaxe else mineral_table["normal"]

        # Select random mineral based on weights
        mineral = random.choices(minerals, weights=[m.weight for m in minerals])[0]

        # Give reward
        reward = mineral.stars
        # Add ore to inventory instead of awarding stars
        ore_key = mineral.name.lower().replace(" ", "_").replace("-", "_")
        self.repo.add_item(user_id, ore_key, "ore", reward)
        bag_count = self.repo.get_inventory_count(user_id)
        bag_capacity = self.repo.get_inventory_capacity(user_id)

        current_stars = self.repo.get_user_stars(user_id, username)
        new_stars = current_stars  # No star change from space mining
        self.repo.update_last_mine(user_id)

        result = SpaceMineResult(
            success=True,
            message="Space mining complete",
            mineral_name=mineral.name,
            mineral_emoji=mineral.emoji,
            stars_earned=reward,
            new_balance=new_stars,
            planet_name=planet_config["name"],
            planet_emoji=planet_config["emoji"],
            item_sell_value=reward,
            bag_count=bag_count,
            bag_capacity=bag_capacity,
        )

        # Check for disaster
        if random.random() < planet_config["disaster_chance"]:
            hazard: MineHazard = random.choice(planet_config["hazards"])
            result.disaster = hazard.name
            result.disaster_header = hazard.header

            golden_axe_uses = inventory["golden_axe"]
            mithril_shield_uses = inventory["mithril_shield"]
            fail_chance = planet_config["protection_fail_chance"]

            protected = False
            protection_msg = ""

            if hazard.protection_item == "helmet":
                if has_helmet:
                    self.repo.update_user_inventory(user_id, "helmet", inventory["helmet"] - 1)
                    if random.random() < fail_chance:
                        protection_msg = planet_config["helmet_fail_msg"]
                    else:
                        protected = True
                        protection_msg = hazard.protected_msg
                elif mithril_shield_uses > 0:
                    protected = True
                    remaining = mithril_shield_uses - 1
                    self.repo.update_user_inventory(user_id, "mithril_shield", remaining)
                    protection_msg = (
                        f"Your mithril shield absorbed the blow!\n"
                        f"*Your shield took a dent.* ({remaining} uses remaining)"
                    )
            elif hazard.protection_item == "sword":
                if has_sword:
                    self.repo.update_user_inventory(user_id, "sword", inventory["sword"] - 1)
                    if random.random() < fail_chance:
                        protection_msg = planet_config["sword_fail_msg"]
                    else:
                        protected = True
                        protection_msg = hazard.protected_msg
                elif golden_axe_uses > 0:
                    protected = True
                    remaining = golden_axe_uses - 1
                    self.repo.update_user_inventory(user_id, "golden_axe", remaining)
                    protection_msg = (
                        f"Your golden axe fended off the attack!\n"
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
                    # Re-read inventory since helmet/sword may have been consumed
                    inventory = self.repo.get_user_inventory(user_id)
                    heart_uses = inventory.get("heart_of_leviathan", 0)
                    if heart_uses > 0:
                        self.repo.update_user_inventory(user_id, "heart_of_leviathan", heart_uses - 1)
                        result.extra_messages.append(
                            "Your **Heart of Leviathan** shielded your bank! *It crumbles to dust.*"
                        )
                    else:
                        current_bank = self.repo.get_user_bank(user_id)
                        potential_bank_loss = int(current_bank * hazard.bank_loss_pct)

                        bank_insurance_uses = inventory.get("bank_insurance", 0)
                        if bank_insurance_uses > 0 and potential_bank_loss > 0:
                            bank_insurance_used = True
                            self.repo.update_user_inventory(user_id, "bank_insurance", bank_insurance_uses - 1)
                            bank_lost = 0
                        else:
                            bank_lost = potential_bank_loss
                            if bank_lost > 0:
                                self.repo.update_user_bank(user_id, username, current_bank - bank_lost)

                self.repo.clear_user_inventory(user_id)
                result.stars_lost = stars_lost
                result.bank_lost = bank_lost
                result.items_destroyed = True
                result.new_balance = new_stars

                disaster_msg = ""
                if protection_msg:
                    disaster_msg += protection_msg + "\n\n"
                disaster_msg += hazard.unprotected_msg.format(
                    stars_lost=stars_lost, bank_lost=bank_lost
                )
                if bank_insurance_used:
                    remaining_insurance = bank_insurance_uses - 1
                    disaster_msg += f"\n\n**Bank Insurance activated!** Your bank was protected from losing {potential_bank_loss} stars.\n*({remaining_insurance} uses remaining)*"

                result.disaster_unprotected_msg = disaster_msg

        return result

    def unlock_planet(self, user_id: int, username: str, planet: int) -> PlanetUnlockResult:
        """Unlock a new space planet."""
        if not self.has_launched(user_id):
            return PlanetUnlockResult(
                success=False,
                message="You haven't launched into space yet! Use `!launch` first.",
            )

        if planet < 2 or planet > 5:
            return PlanetUnlockResult(
                success=False,
                message="Planets range from 1 to 5. You can unlock planets 2-5.",
            )

        current_unlocked = self.repo.get_space_planet_level(user_id)

        if planet <= current_unlocked:
            return PlanetUnlockResult(
                success=False,
                message=f"You've already unlocked planet {planet}!",
            )

        if planet != current_unlocked + 1:
            return PlanetUnlockResult(
                success=False,
                message=f"You need to unlock planet {current_unlocked + 1} first!",
            )

        cost = SPACE_PLANETS[planet]["cost"]
        current_stars = self.repo.get_user_stars(user_id, username)

        if current_stars < cost:
            return PlanetUnlockResult(
                success=False,
                message=f"You need **{cost}** stars to unlock planet {planet}, but you only have **{current_stars}**!",
            )

        # Deduct cost and unlock
        self.repo.update_user_stars(user_id, username, current_stars - cost)
        self.repo.set_space_planet_level(user_id, planet)
        self.repo.set_active_space_planet(user_id, planet)

        planet_config = SPACE_PLANETS[planet]
        return PlanetUnlockResult(
            success=True,
            message=f"You unlocked **{planet_config['emoji']} {planet_config['name']}** (Planet {planet})!",
            planet=planet,
            cost=cost,
        )

    def get_planet_info(self, user_id: int) -> PlanetInfo:
        """Get planet info for a user."""
        return PlanetInfo(
            unlocked_planet=self.repo.get_space_planet_level(user_id),
            active_planet=self.repo.get_active_space_planet(user_id),
            planets=SPACE_PLANETS,
        )

    def set_active_planet(self, user_id: int, planet: int) -> tuple[bool, str]:
        """Switch active space planet. Returns (success, message)."""
        if not self.has_launched(user_id):
            return False, "You haven't launched into space yet! Use `!launch` first."

        if planet < 1 or planet > 5:
            return False, "Planets range from 1 to 5."

        unlocked = self.repo.get_space_planet_level(user_id)
        if planet > unlocked:
            return False, f"You haven't unlocked planet {planet} yet! Your highest unlocked planet is {unlocked}."

        self.repo.set_active_space_planet(user_id, planet)
        planet_config = SPACE_PLANETS[planet]
        return True, f"Switched to **{planet_config['emoji']} {planet_config['name']}** (Planet {planet})!"

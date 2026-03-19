"""Space mining service with planets, ambush encounters, and space ores.

Average Returns (per mine, normal pickaxe):
    Moon (Planet 1):   ~132 stars
    Mars (Planet 2):   ~190 stars
    Saturn (Planet 3): ~264 stars
    Uranus (Planet 4): ~366 stars
    Pluto (Planet 5):  ~511 stars

Ambush Chances (halved by lucky charm):
    Moon:   12%
    Mars:   14%
    Saturn: 16%
    Uranus: 18%
    Pluto:  22%
"""

import math
import random
from typing import Optional

from cogs.space.constants import SPACE_MINERAL_TABLES, SPACE_PLANETS, SPACE_STAMINA_COST
from database.repository import UserRepository
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

    def mine(self, user_id: int, username: str) -> SpaceMineResult:
        """Mine on the active space planet. Costs stamina."""
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

        # Get active planet and stamina cost
        active_planet = self.repo.get_active_space_planet(user_id)
        stamina_cost = SPACE_STAMINA_COST[active_planet]

        # Jackhammer halves stamina cost (only if golden pickaxe NOT owned)
        has_jackhammer = inventory.get("jackhammer", 0) > 0
        has_gold_pickaxe = inventory["gold_pickaxe"] > 0
        if has_jackhammer and not has_gold_pickaxe:
            stamina_cost = max(1, stamina_cost // 2)

        # Apply passive regen then check stamina
        from cogs.combat.use_case.health import HealthUseCases
        health_uc = HealthUseCases(self.repo)
        status = health_uc.get_status(user_id)

        if status.current_stamina < stamina_cost:
            return SpaceMineResult(
                success=False,
                message=f"You need **{stamina_cost}** stamina to mine here, but you only have **{status.current_stamina}**! Use `!consume` to restore stamina.",
            )
        # Deduct stamina
        self.repo.update_stamina(user_id, status.current_stamina - stamina_cost)

        planet_config = SPACE_PLANETS[active_planet]

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

        # Star Magnet: 15% chance to get a second copy of the same ore
        star_magnet_uses = inventory["star_magnet"]
        doubled = False
        if star_magnet_uses > 0:
            self.repo.update_user_inventory(user_id, "star_magnet", star_magnet_uses - 1)
            if random.random() < 0.15:
                self.repo.add_item(user_id, ore_key, "ore", reward)
                doubled = True
        bag_count = self.repo.get_inventory_count(user_id)
        bag_capacity = self.repo.get_inventory_capacity(user_id)

        current_stars = self.repo.get_user_stars(user_id, username)
        new_stars = current_stars  # No star change from space mining

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
        if doubled:
            result.extra_messages.append(
                "🧲 **Star Magnet** activated! You found a second "
                f"{mineral.emoji} **{mineral.name}**!"
            )

        # Check for ambush (chance varies by planet, halved by lucky charm)
        ambush_chance = planet_config["disaster_chance"]
        lucky_charm_uses = inventory["lucky_charm"]
        used_lucky_charm = False
        if lucky_charm_uses > 0:
            ambush_chance *= 0.5
            used_lucky_charm = True

        if random.random() < ambush_chance:
            if used_lucky_charm:
                self.repo.update_user_inventory(user_id, "lucky_charm", lucky_charm_uses - 1)

            from cogs.combat.ambush_constants import SPACE_AMBUSH_MOBS
            mobs = SPACE_AMBUSH_MOBS.get(active_planet, [])
            if mobs:
                mob = random.choice(mobs)
                result.ambush_mob_key = mob.key
                result.ambush_mob_name = mob.name
                result.ambush_mob_emoji = mob.emoji
                result.ambush_activity = "space"
                result.ambush_level = active_planet

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

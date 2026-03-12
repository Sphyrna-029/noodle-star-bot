"""Health and stamina management use cases."""

from datetime import datetime

from cogs.combat.constants import (
    BASE_HP, BASE_STAMINA, CROP_HEAL_VALUES, FISH_HEAL_VALUES,
    STAMINA_RECOVERY, HP_REGEN_PER_MINUTE, STAMINA_REGEN_PER_MINUTE,
    COMBAT_ITEMS,
)
from cogs.combat.dto import DrinkResult, EatResult, HealthStatus
from database.repository import UserRepository

# Health potion HP value (sold in shop)
HEALTH_POTION_HP: int = 20


class HealthUseCases:
    """Manages HP, stamina, passive regen, eating, and drinking."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def _apply_regen(self, user_id: int) -> dict:
        """Apply passive HP and stamina regeneration based on elapsed time.
        Returns the updated combat stats dict."""
        stats = self.repo.get_combat_stats(user_id)
        now = datetime.utcnow()
        hp_changed = False
        stamina_changed = False

        # Initialize timestamps for first-time users so regen can start
        if stats["current_hp"] is not None and stats["hp_updated_at"] is None:
            self.repo.update_hp(user_id, stats["current_hp"])
            stats["hp_updated_at"] = now.isoformat()

        # HP regen
        if stats["current_hp"] < stats["max_hp"] and stats["hp_updated_at"]:
            last = datetime.fromisoformat(stats["hp_updated_at"])
            minutes = (now - last).total_seconds() / 60
            regen = int(minutes * HP_REGEN_PER_MINUTE)
            if regen > 0:
                stats["current_hp"] = min(stats["max_hp"], stats["current_hp"] + regen)
                hp_changed = True

        # Initialize timestamps for first-time users so regen can start
        if stats["current_stamina"] is not None and stats["stamina_updated_at"] is None:
            self.repo.update_stamina(user_id, stats["current_stamina"])
            stats["stamina_updated_at"] = now.isoformat()

        # Stamina regen
        if stats["current_stamina"] < stats["max_stamina"] and stats["stamina_updated_at"]:
            last = datetime.fromisoformat(stats["stamina_updated_at"])
            minutes = (now - last).total_seconds() / 60
            regen = int(minutes * STAMINA_REGEN_PER_MINUTE)
            if regen > 0:
                stats["current_stamina"] = min(stats["max_stamina"], stats["current_stamina"] + regen)
                stamina_changed = True

        if hp_changed:
            self.repo.update_hp(user_id, stats["current_hp"])
        if stamina_changed:
            self.repo.update_stamina(user_id, stats["current_stamina"])

        return stats

    def _calc_max_hp(self, user_id: int) -> int:
        """Calculate max HP from base + armor/shield bonuses."""
        stats = self.repo.get_combat_stats(user_id)
        bonus = 0
        for slot_key in (stats["equipped_weapon"], stats["equipped_shield"], stats["equipped_armor"]):
            if slot_key and slot_key in COMBAT_ITEMS:
                bonus += COMBAT_ITEMS[slot_key].hp_bonus
        return BASE_HP + bonus

    def get_status(self, user_id: int) -> HealthStatus:
        """Get current HP and stamina after applying passive regen."""
        stats = self._apply_regen(user_id)
        max_hp = self._calc_max_hp(user_id)
        # Update max_hp if it changed due to equipment
        if stats["max_hp"] != max_hp:
            stats["max_hp"] = max_hp
            stats["current_hp"] = min(stats["current_hp"], max_hp)
            self.repo.update_hp(user_id, stats["current_hp"], max_hp)
        return HealthStatus(
            current_hp=stats["current_hp"],
            max_hp=stats["max_hp"],
            current_stamina=stats["current_stamina"],
            max_stamina=stats["max_stamina"],
        )

    def get_hp_value(self, item_key: str) -> int | None:
        """Return HP restored by an item, or None if it's not an HP item."""
        if item_key in FISH_HEAL_VALUES:
            return FISH_HEAL_VALUES[item_key]
        if item_key in CROP_HEAL_VALUES:
            return CROP_HEAL_VALUES[item_key]
        if item_key == "health_potion":
            return HEALTH_POTION_HP
        return None

    def _find_and_remove(self, user_id: int, item_key: str) -> bool:
        """Find one item in inventory and remove it. Returns False if not found."""
        items = self.repo.get_inventory_items(user_id)
        for item in items:
            if item["item_key"] == item_key:
                self.repo.remove_items_by_ids(user_id, [item["id"]])
                return True
        return False

    def eat_fish(self, user_id: int, item_name: str) -> EatResult:
        """Consume an HP item (fish, crop, or health potion) from inventory."""
        item_key = item_name.lower().replace(" ", "_").replace("'", "")
        heal = self.get_hp_value(item_key)
        if heal is None:
            return EatResult(
                success=False,
                message=f"**{item_name}** can't be consumed for healing!",
            )

        # Check if user has the item
        items = self.repo.get_inventory_items(user_id)
        item_row = None
        for item in items:
            if item["item_key"] == item_key:
                item_row = item
                break

        if not item_row:
            display = item_key.replace("_", " ").title()
            return EatResult(
                success=False,
                message=f"You don't have any **{display}** in your inventory!",
            )

        stats = self._apply_regen(user_id)
        max_hp = self._calc_max_hp(user_id)
        if stats["current_hp"] >= max_hp:
            return EatResult(
                success=False,
                message="You're already at full HP!",
                current_hp=max_hp,
                max_hp=max_hp,
            )

        self.repo.remove_items_by_ids(user_id, [item_row["id"]])

        old_hp = stats["current_hp"]
        new_hp = min(max_hp, old_hp + heal)
        actual_heal = new_hp - old_hp
        self.repo.update_hp(user_id, new_hp, max_hp)

        display = item_key.replace("_", " ").title()
        return EatResult(
            success=True,
            message=f"You consumed **{display}** and restored **{actual_heal} HP**!",
            hp_restored=actual_heal,
            current_hp=new_hp,
            max_hp=max_hp,
        )

    def drink(self, user_id: int, item_name: str) -> DrinkResult:
        """Consume a stamina item from inventory to restore stamina."""
        item_key = item_name.lower().replace(" ", "_").replace("'", "")
        recovery = STAMINA_RECOVERY.get(item_key)
        if recovery is None:
            return DrinkResult(
                success=False,
                message=f"**{item_name}** doesn't restore stamina!",
            )

        # Check if user has the item
        items = self.repo.get_inventory_items(user_id)
        item_row = None
        for item in items:
            if item["item_key"] == item_key:
                item_row = item
                break

        if not item_row:
            display = item_key.replace("_", " ").title()
            return DrinkResult(
                success=False,
                message=f"You don't have any **{display}** in your inventory!",
            )

        stats = self._apply_regen(user_id)
        max_stam = stats["max_stamina"]
        if stats["current_stamina"] >= max_stam:
            return DrinkResult(
                success=False,
                message="You're already at full stamina!",
                current_stamina=max_stam,
                max_stamina=max_stam,
            )

        self.repo.remove_items_by_ids(user_id, [item_row["id"]])

        old_stam = stats["current_stamina"]
        new_stam = min(max_stam, old_stam + recovery)
        actual = new_stam - old_stam
        self.repo.update_stamina(user_id, new_stam)

        display = item_key.replace("_", " ").title()
        return DrinkResult(
            success=True,
            message=f"You consumed **{display}** and restored **{actual} stamina**!",
            stamina_restored=actual,
            current_stamina=new_stam,
            max_stamina=max_stam,
        )

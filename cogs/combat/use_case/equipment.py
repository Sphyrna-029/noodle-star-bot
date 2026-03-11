"""Equipment management use cases — equip, unequip, gear check."""

from cogs.combat.constants import COMBAT_ITEMS, BASE_HP
from cogs.combat.dto import EquipResult, GearResult
from database.repository import UserRepository


class EquipmentUseCases:
    """Manages equipping, unequipping, and viewing combat gear."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def equip(self, user_id: int, item_key: str) -> EquipResult:
        """Equip a combat item from the user's equipment table."""
        item_def = COMBAT_ITEMS.get(item_key)
        if not item_def:
            return EquipResult(success=False, message=f"Unknown combat item: `{item_key}`")

        # Check ownership
        if not self.repo.has_equipment(user_id, item_key):
            return EquipResult(
                success=False,
                message=f"You don't own **{item_def.name}** {item_def.emoji}!",
            )

        slot = item_def.slot
        stats = self.repo.get_combat_stats(user_id)
        slot_col = f"equipped_{slot}"
        current = stats.get(slot_col)

        if current == item_key:
            return EquipResult(
                success=False,
                message=f"**{item_def.name}** is already equipped!",
            )

        self.repo.set_equipped_combat_item(user_id, slot, item_key)

        # Recalculate max HP
        new_max_hp = self._calc_max_hp(user_id)
        current_hp = stats["current_hp"]
        if current_hp > new_max_hp:
            current_hp = new_max_hp
        self.repo.update_hp(user_id, current_hp, new_max_hp)

        msg = f"Equipped **{item_def.name}** {item_def.emoji} in your **{slot}** slot!"
        if current:
            old_def = COMBAT_ITEMS.get(current)
            if old_def:
                msg += f"\n(Replaced {old_def.name} {old_def.emoji})"
        return EquipResult(success=True, message=msg, slot=slot, item_name=item_def.name)

    def unequip(self, user_id: int, slot: str) -> EquipResult:
        """Unequip item from a slot (weapon/shield/armor)."""
        if slot not in ("weapon", "shield", "armor"):
            return EquipResult(success=False, message="Invalid slot! Use: `weapon`, `shield`, or `armor`.")

        stats = self.repo.get_combat_stats(user_id)
        current = stats.get(f"equipped_{slot}")
        if not current:
            return EquipResult(success=False, message=f"Nothing is equipped in your **{slot}** slot!")

        item_def = COMBAT_ITEMS.get(current)
        self.repo.set_equipped_combat_item(user_id, slot, None)

        # Recalculate max HP
        new_max_hp = self._calc_max_hp(user_id)
        current_hp = min(stats["current_hp"], new_max_hp)
        self.repo.update_hp(user_id, current_hp, new_max_hp)

        name = item_def.name if item_def else current
        emoji = item_def.emoji if item_def else ""
        return EquipResult(success=True, message=f"Unequipped **{name}** {emoji} from your **{slot}** slot.")

    def get_gear(self, user_id: int) -> GearResult:
        """Get current equipped gear summary."""
        stats = self.repo.get_combat_stats(user_id)
        total_atk = 0
        total_def = 0
        total_hp = 0

        weapon_name = None
        shield_name = None
        armor_name = None

        for slot in ("weapon", "shield", "armor"):
            key = stats.get(f"equipped_{slot}")
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                total_atk += item.attack
                total_def += item.defense
                total_hp += item.hp_bonus
                display = f"{item.emoji} {item.name} (T{item.tier})"
                if slot == "weapon":
                    weapon_name = display
                elif slot == "shield":
                    shield_name = display
                else:
                    armor_name = display

        return GearResult(
            success=True,
            message="Gear retrieved",
            weapon=weapon_name,
            shield=shield_name,
            armor=armor_name,
            total_attack=total_atk,
            total_defense=total_def,
            total_hp_bonus=total_hp,
        )

    def _calc_max_hp(self, user_id: int) -> int:
        """Calculate max HP from base + equipped items."""
        stats = self.repo.get_combat_stats(user_id)
        bonus = 0
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = stats.get(slot)
            if key and key in COMBAT_ITEMS:
                bonus += COMBAT_ITEMS[key].hp_bonus
        return BASE_HP + bonus

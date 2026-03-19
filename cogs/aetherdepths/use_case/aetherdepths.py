"""Core Aetherdepths use cases — dungeon entry, fighting, drops, gates, hazards."""

import random
from datetime import datetime
from typing import Optional

from cogs.aetherdepths.constants import (
    AETHER_BOSS_BONUS_DROPS,
    AETHER_DAILY_MODIFIERS,
    AETHER_DEATH_PENALTIES,
    AETHER_DROPS,
    AETHER_HAZARDS,
    AETHER_KEY_MATERIALS,
    AETHER_LEVELS,
    AETHER_MATERIALS,
    AETHER_MOBS,
    AETHER_MOBS_BY_LEVEL,
    AETHER_UNLOCK,
    ELITE_CHANCE,
    ELITE_KEY_MATERIAL_CHANCE,
    ELITE_STAT_BONUS,
    HAZARD_BASE_CHANCE,
    KEY_MATERIAL_DROPS,
    WINS_PER_AETHER_LEVEL,
)
from cogs.aetherdepths.dto import AetherState, DailyModifier, HazardResult
from cogs.combat.constants import BASE_HP, BASE_STAMINA, COMBAT_ITEMS, STAMINA_PER_ATTACK
from cogs.combat.dto import BattleState, BattleTurn
from cogs.shop.resources import get_resource
from database.repository import UserRepository


class AetherdepthsUseCases:
    """Business logic for the Aetherdepths dungeon."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    # ── Dungeon entry ────────────────────────────────────────

    def enter_dungeon(self, user_id: int, username: str, level: int) -> tuple[bool, str]:
        """Attempt to enter/unlock an Aether level.

        Returns (success, message).
        """
        if level not in AETHER_LEVELS:
            return False, "Invalid Aether level! Valid: 1-5"

        stats = self.repo.get_combat_stats(user_id)
        aether = self.repo.get_aether_stats(user_id)

        unlock = AETHER_UNLOCK[level]

        # Check combat level prerequisite
        if stats["combat_level"] < unlock["required_combat_level"]:
            return False, (
                f"You need **Combat Level {unlock['required_combat_level']}** to enter "
                f"The Aetherdepths! Complete the Noodle Colosseum first."
            )

        # Check if they've already unlocked this level
        if aether["aether_level"] >= level:
            # Already unlocked — just set active level
            self.repo.update_active_aether_level(user_id, level)
            self.repo.set_aether_active(user_id, 1)
            floor = AETHER_LEVELS[level]
            return True, (
                f"Entered **{floor['name']}** {floor['emoji']} (Level {level})!"
            )

        # Must unlock sequentially
        if level > 1 and aether["aether_level"] < level - 1:
            return False, f"You must unlock Level {level - 1} first!"

        # Check cost
        cost = unlock["cost"]
        current_stars = self.repo.get_user_stars(user_id, username)
        if current_stars < cost:
            return False, (
                f"Unlocking **{AETHER_LEVELS[level]['name']}** costs "
                f"**{cost:,}** stars. You have **{current_stars:,}**."
            )

        # Pay and unlock
        self.repo.update_user_stars(user_id, username, current_stars - cost)
        self.repo.update_aether_level(user_id, level)
        self.repo.update_active_aether_level(user_id, level)
        self.repo.set_aether_active(user_id, 1)

        floor = AETHER_LEVELS[level]
        return True, (
            f"Unlocked **{floor['name']}** {floor['emoji']}! "
            f"Cost: **{cost:,}** stars."
        )

    def exit_dungeon(self, user_id: int) -> str:
        """Exit the Aetherdepths and return stashed items."""
        self.repo.set_aether_active(user_id, 0)
        returned = self.repo.return_stashed_items(user_id)
        msg = "You've exited The Aetherdepths."
        if returned > 0:
            msg += f" **{returned}** stashed item(s) returned to your inventory."
        return msg

    # ── Fight initialization ─────────────────────────────────

    def start_fight(
        self, user_id: int, username: str, level: int, modifier: dict | None = None
    ) -> tuple[Optional[BattleState], str, bool]:
        """Start an Aether fight.

        Returns (BattleState, error_msg, is_elite).
        """
        stats = self.repo.get_combat_stats(user_id)

        # Check HP
        current_hp = stats["current_hp"] if stats["current_hp"] is not None else BASE_HP
        max_hp = stats["max_hp"] if stats["max_hp"] is not None else BASE_HP
        if current_hp <= 0:
            return None, "You're out of HP! Use `!consume` to recover.", False

        # Check stamina
        current_stamina = stats["current_stamina"] if stats["current_stamina"] is not None else BASE_STAMINA
        max_stamina = stats["max_stamina"] if stats["max_stamina"] is not None else BASE_STAMINA
        if current_stamina < STAMINA_PER_ATTACK:
            return None, (
                f"You need at least **{STAMINA_PER_ATTACK} stamina** to fight! "
                f"Current: **{current_stamina}/{max_stamina}**."
            ), False

        # Pick mob
        level_mobs = AETHER_MOBS_BY_LEVEL.get(level, [])
        if not level_mobs:
            return None, "No mobs found for this level!", False

        mob = random.choice(level_mobs)

        # Elite roll (non-boss only)
        is_elite = False
        mob_hp = mob.hp
        mob_atk = mob.attack
        mob_def = mob.defense
        mob_stam = mob.stamina
        mob_name = mob.name
        mob_emoji = mob.emoji

        if not mob.is_boss and random.random() < ELITE_CHANCE:
            is_elite = True
            mob_hp = int(mob_hp * (1 + ELITE_STAT_BONUS))
            mob_atk = int(mob_atk * (1 + ELITE_STAT_BONUS))
            mob_def = int(mob_def * (1 + ELITE_STAT_BONUS))
            mob_name = f"Elite {mob.name}"
            mob_emoji = "🔥"

        # Apply daily modifier
        if modifier:
            hp_mult = modifier.get("mob_hp_mult", 1.0)
            mob_hp = int(mob_hp * hp_mult)

        # Calculate player stats
        player_atk = 5
        player_def = 2
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = stats.get(slot)
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                player_atk += item.attack
                player_def += item.defense

        battle = BattleState(
            mob_key=mob.key,
            mob_name=mob_name,
            mob_emoji=mob_emoji,
            dungeon_level=level,
            player_hp=current_hp,
            player_max_hp=max_hp,
            player_stamina=current_stamina,
            player_max_stamina=max_stamina,
            player_attack=player_atk,
            player_defense=player_def,
            mob_hp=mob_hp,
            mob_max_hp=mob_hp,
            mob_attack=mob_atk,
            mob_defense=mob_def,
            mob_stamina=mob_stam,
            mob_max_stamina=mob_stam,
        )
        return battle, "", is_elite

    # ── Drop rolling ─────────────────────────────────────────

    def roll_drops(
        self, level: int, mob_key: str, is_elite: bool, modifier: dict | None = None
    ) -> list[tuple[str, str, int, str]]:
        """Roll loot for a defeated Aether mob.

        Returns list of (item_key, category, sell_value, display_name).
        """
        drops: list[tuple[str, str, int, str]] = []
        drop_table = list(AETHER_DROPS.get(level, []))

        # Boss bonus
        mob = AETHER_MOBS.get(mob_key)
        if mob and mob.is_boss:
            drop_table.extend(AETHER_BOSS_BONUS_DROPS)
            drop_table.extend(KEY_MATERIAL_DROPS.get(level, []))

        # Elite bonus — guaranteed uncommon material + key material chance
        if is_elite:
            # Guaranteed uncommon material from this level
            level_mats = [
                k for k, v in AETHER_MATERIALS.items()
                if v["level"] == level and k not in AETHER_KEY_MATERIALS
            ]
            if level_mats:
                mat_key = random.choice(level_mats)
                mat = AETHER_MATERIALS[mat_key]
                drops.append((mat_key, "mineral", mat["sell"], mat["name"]))

            # Key material chance
            key_mats = KEY_MATERIAL_DROPS.get(level, [])
            for item_key, category, sell_value, chance in key_mats:
                if random.random() < ELITE_KEY_MATERIAL_CHANCE:
                    mat = AETHER_MATERIALS.get(item_key, {})
                    display = mat.get("name", item_key.replace("_", " ").title())
                    drops.append((item_key, category, sell_value, display))

        # Apply modifier multipliers
        drop_mult = 1.0
        key_drop_mult = 1.0
        if modifier:
            drop_mult = modifier.get("drop_mult", 1.0)
            key_drop_mult = modifier.get("key_drop_mult", 1.0)

        for item_key, category, sell_value, chance in drop_table:
            effective_chance = chance
            if item_key in AETHER_KEY_MATERIALS:
                effective_chance *= key_drop_mult
            elif item_key in AETHER_MATERIALS:
                effective_chance = min(1.0, chance * drop_mult)

            if random.random() < effective_chance:
                mat = AETHER_MATERIALS.get(item_key)
                res = get_resource(item_key)
                if mat:
                    display = mat["name"]
                elif res:
                    display = res.display_name
                else:
                    display = item_key.replace("_", " ").title()
                drops.append((item_key, category, sell_value, display))

        return drops

    def grant_drops(self, user_id: int, drops: list[tuple[str, str, int, str]]) -> list[tuple[str, str]]:
        """Add dropped items to inventory. Returns list of (item_key, display_name)."""
        granted: list[tuple[str, str]] = []
        for item_key, category, sell_value, display in drops:
            if category == "equipment":
                inv = self.repo.get_user_inventory(user_id)
                current = inv.get(item_key, 0)
                if item_key in ("golden_axe", "mithril_shield"):
                    if current > 0:
                        continue
                    self.repo.update_user_inventory(user_id, item_key, 1)
                else:
                    self.repo.update_user_inventory(user_id, item_key, current + 20)
                granted.append((item_key, display))
            else:
                if self.repo.add_item(user_id, item_key, category, sell_value):
                    granted.append((item_key, display))
        return granted

    # ── Victory / Defeat ─────────────────────────────────────

    def resolve_victory(
        self, user_id: int, username: str, battle: BattleState,
        is_elite: bool, modifier: dict | None = None,
    ) -> dict:
        """Handle Aether victory — stars, drops, level progression."""
        # Save HP/stamina
        self.repo.update_hp(user_id, battle.player_hp)
        self.repo.update_stamina(user_id, battle.player_stamina)

        # Stars
        mob = AETHER_MOBS.get(battle.mob_key)
        star_reward = mob.star_reward if mob else 200
        current_stars = self.repo.get_user_stars(user_id, username)
        self.repo.update_user_stars(user_id, username, current_stars + star_reward)

        # Drops
        raw_drops = self.roll_drops(battle.dungeon_level, battle.mob_key, is_elite, modifier)
        granted = self.grant_drops(user_id, raw_drops)

        # Log combat
        self.repo.log_combat(
            user_id=user_id,
            dungeon_level=battle.dungeon_level,
            mob_key=battle.mob_key,
            result="win",
            stars_change=star_reward,
        )

        boss_text = " **BOSS DEFEATED!**" if (mob and mob.is_boss) else ""
        elite_text = " 🔥 **ELITE SLAIN!**" if is_elite else ""

        return {
            "message": f"Victory!{boss_text}{elite_text} You earned **{star_reward}** stars!",
            "stars_earned": star_reward,
            "drops": granted,
            "turns": battle.turns,
        }

    def resolve_defeat(
        self, user_id: int, username: str, battle: BattleState,
        modifier: dict | None = None,
    ) -> dict:
        """Handle Aether defeat — apply death penalties."""
        level = battle.dungeon_level

        # Check if modifier makes penalty harsher
        effective_level = level
        if modifier and modifier.get("harsher_penalty"):
            effective_level = min(5, level + 1)

        penalty = AETHER_DEATH_PENALTIES.get(effective_level, AETHER_DEATH_PENALTIES[1])

        stars_lost = 0
        items_lost = []
        equipment_lost = []
        bank_loss = 0

        # Heart of Leviathan protection
        inv = self.repo.get_user_inventory(user_id)
        heart_uses = inv.get("heart_of_leviathan", 0)
        heart_saved = False

        if heart_uses > 0:
            self.repo.update_user_inventory(user_id, "heart_of_leviathan", heart_uses - 1)
            heart_saved = True
        else:
            # Wallet loss
            current_stars = self.repo.get_user_stars(user_id, username)
            if penalty["wallet_loss_pct"] > 0:
                stars_lost = int(current_stars * penalty["wallet_loss_pct"])
                self.repo.update_user_stars(user_id, username, max(0, current_stars - stars_lost))

            # Bank loss
            if penalty["bank_loss_pct"] > 0:
                current_bank = self.repo.get_user_bank(user_id)
                bank_loss = int(current_bank * penalty["bank_loss_pct"])
                if bank_loss > 0:
                    bank_ins = inv.get("bank_insurance", 0)
                    if bank_ins > 0:
                        self.repo.update_user_inventory(user_id, "bank_insurance", bank_ins - 1)
                        bank_loss = 0
                    else:
                        self.repo.update_user_bank(user_id, username, max(0, current_bank - bank_loss))

            # Item losses
            if penalty["lose_all_items"]:
                inv_items = self.repo.get_inventory_items(user_id)
                for item in inv_items:
                    items_lost.append(item["item_key"])
                self.repo.clear_inventory(user_id)
            elif penalty["lose_random_items_pct"] > 0:
                inv_items = self.repo.get_inventory_items(user_id)
                count_to_lose = max(1, int(len(inv_items) * penalty["lose_random_items_pct"]))
                to_remove = random.sample(inv_items, min(count_to_lose, len(inv_items)))
                for item in to_remove:
                    items_lost.append(item["item_key"])
                    self.repo.remove_items_by_ids(user_id, [item["id"]])

            # Equipment losses
            if penalty["lose_all_equipment"]:
                equip = self.repo.get_user_equipment(user_id)
                equipment_lost = list(equip.keys())
                self.repo.clear_all_equipment(user_id)
                for slot in ("weapon", "shield", "armor"):
                    self.repo.set_equipped_combat_item(user_id, slot, None)
            elif penalty["lose_random_equipment"] > 0:
                equip = self.repo.get_user_equipment(user_id)
                equip_keys = list(equip.keys())
                count = min(penalty["lose_random_equipment"], len(equip_keys))
                if count > 0:
                    to_remove = random.sample(equip_keys, count)
                    cstats = self.repo.get_combat_stats(user_id)
                    for key in to_remove:
                        equipment_lost.append(key)
                        self.repo.set_equipment(user_id, key, 0)
                        for slot in ("weapon", "shield", "armor"):
                            if cstats.get(f"equipped_{slot}") == key:
                                self.repo.set_equipped_combat_item(user_id, slot, None)

        # Set HP to 1
        self.repo.update_hp(user_id, 1)
        self.repo.update_stamina(user_id, battle.player_stamina)

        # Recalculate max HP
        max_hp = BASE_HP
        new_stats = self.repo.get_combat_stats(user_id)
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = new_stats.get(slot)
            if key and key in COMBAT_ITEMS:
                max_hp += COMBAT_ITEMS[key].hp_bonus
        self.repo.update_hp(user_id, 1, max_hp)

        # Log
        self.repo.log_combat(
            user_id=user_id,
            dungeon_level=battle.dungeon_level,
            mob_key=battle.mob_key,
            result="loss",
            stars_change=-stars_lost,
            items_lost=items_lost if items_lost else None,
            equipment_lost=equipment_lost if equipment_lost else None,
            bank_loss=bank_loss,
        )

        penalty_desc = penalty["description"]
        if heart_saved:
            defeat_msg = (
                f"Defeated by **{battle.mob_name}**! "
                f"But your 💚 **Heart of Leviathan** shielded you from all penalties!"
            )
        else:
            defeat_msg = f"Defeated by **{battle.mob_name}**! {penalty_desc}"

        return {
            "message": defeat_msg,
            "stars_lost": stars_lost,
            "items_lost": items_lost,
            "equipment_lost": equipment_lost,
            "bank_loss": bank_loss,
            "turns": battle.turns,
        }

    # ── Floor hazards ────────────────────────────────────────

    def roll_hazard(
        self, user_id: int, username: str, level: int, modifier: dict | None = None,
    ) -> HazardResult:
        """Roll for a floor hazard after victory."""
        # Check if modifier disables hazards
        if modifier and modifier.get("no_hazards"):
            return HazardResult(triggered=False)

        # Check for Lucky Charm (halves hazard chance)
        inv = self.repo.get_user_inventory(user_id)
        lucky_charm = inv.get("lucky_charm", 0)
        base_chance = HAZARD_BASE_CHANCE.get(level, 0.15)
        if lucky_charm > 0:
            base_chance *= 0.5
            self.repo.update_user_inventory(user_id, "lucky_charm", lucky_charm - 1)

        if random.random() >= base_chance:
            return HazardResult(triggered=False)

        # Pick a random hazard from this level
        hazards = AETHER_HAZARDS.get(level, [])
        if not hazards:
            return HazardResult(triggered=False)

        hazard = random.choice(hazards)
        result = HazardResult(
            triggered=True,
            hazard_name=hazard["name"],
            hazard_emoji=hazard["emoji"],
        )

        # Apply effects
        stars_lost = 0
        items_lost = []

        if hazard.get("wallet_loss_pct", 0) > 0:
            current_stars = self.repo.get_user_stars(user_id, username)
            stars_lost = int(current_stars * hazard["wallet_loss_pct"])
            self.repo.update_user_stars(user_id, username, max(0, current_stars - stars_lost))
            result.stars_lost = stars_lost

        if hazard.get("lose_items", 0) > 0:
            inv_items = self.repo.get_inventory_items(user_id)
            count = min(hazard["lose_items"], len(inv_items))
            if count > 0:
                to_remove = random.sample(inv_items, count)
                for item in to_remove:
                    items_lost.append(item["item_key"])
                    self.repo.remove_items_by_ids(user_id, [item["id"]])
            result.items_lost = items_lost

        if hazard.get("lose_lowest_items"):
            inv_items = self.repo.get_inventory_items(user_id)
            if inv_items:
                min_val = min(i.get("base_sell_value", 0) for i in inv_items)
                to_remove = [i for i in inv_items if i.get("base_sell_value", 0) == min_val]
                for item in to_remove:
                    items_lost.append(item["item_key"])
                    self.repo.remove_items_by_ids(user_id, [item["id"]])
            result.items_lost = items_lost

        if hazard.get("hp_loss", 0) > 0:
            result.hp_loss = hazard["hp_loss"]

        if hazard.get("halve_stamina"):
            stats = self.repo.get_combat_stats(user_id)
            current_stam = stats.get("current_stamina", BASE_STAMINA)
            self.repo.update_stamina(user_id, current_stam // 2)
            result.stamina_halved = True

        if hazard.get("max_hp_reduction", 0) > 0:
            result.max_hp_reduction = hazard["max_hp_reduction"]

        if hazard.get("trigger_fight"):
            result.trigger_fight = True

        # Format description
        desc = hazard["description"]
        desc = desc.replace("{loss}", f"{stars_lost:,}")
        desc = desc.replace("{count}", str(len(items_lost)))
        result.description = desc

        return result

    # ── Gate mechanic ────────────────────────────────────────

    def check_gate(self, kills: int, target_level: int) -> tuple[bool, str]:
        """Check if the player can advance to the next level.

        On L2+, requires at least 1 kill on current level.
        """
        if target_level <= 1:
            return True, ""
        if kills < 1:
            return False, (
                f"You need at least **1 kill** on your current level before "
                f"advancing to Level {target_level}!"
            )
        return True, ""

    # ── Daily modifier ───────────────────────────────────────

    def get_active_modifier(self) -> dict | None:
        """Get the currently active daily modifier, if any."""
        row = self.repo.get_daily_modifier()
        if not row or not row["modifier_key"]:
            return None

        today = datetime.utcnow().strftime("%Y-%m-%d")
        if row["active_date"] != today:
            return None

        for mod in AETHER_DAILY_MODIFIERS:
            if mod["key"] == row["modifier_key"]:
                return mod
        return None

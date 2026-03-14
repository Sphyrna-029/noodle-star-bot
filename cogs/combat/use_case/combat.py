"""Core combat use cases — fighting mobs, death penalties, level progression."""

import random
from typing import Optional

from cogs.combat.ambush_constants import AMBUSH_MOB_BONUS_DROPS
from cogs.combat.constants import (
    ALIEN_AMBUSH_DROPS, BASE_HP, BASE_STAMINA, BOSS_BONUS_DROPS,
    COMBAT_ITEMS, COMBAT_LEVEL_UNLOCK,
    DAMAGE_FLOOR, DEATH_PENALTIES, DUNGEON_DROPS, DUNGEON_LEVELS,
    FISHING_AMBUSH_DROPS, MINING_AMBUSH_DROPS, MOBS, MOBS_BY_LEVEL,
    SPACE_AMBUSH_DROPS, STAMINA_PER_ATTACK, STAMINA_PER_DEFEND,
    WINS_PER_COMBAT_LEVEL,
)
from cogs.combat.dto import AmbushContext, BattleResult, BattleState, BattleTurn, DungeonUnlockResult
from cogs.shop.resources import get_resource
from database.repository import UserRepository


class CombatUseCases:
    """Core combat business logic — fights, death penalties, level management."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    # ── Drop rolling ──────────────────────────────────────────

    def roll_drops(self, battle: BattleState) -> list[tuple[str, str, int, str]]:
        """Roll the loot table for a defeated mob.

        Returns list of (item_key, category, sell_value, display_name) for items
        that passed their drop chance.
        """
        drops: list[tuple[str, str, int, str]] = []
        drop_table: list[tuple[str, str, int, float]] = []

        if battle.ambush:
            activity = battle.ambush.activity
            level = battle.ambush.activity_level
            if activity == "mining":
                drop_table = list(MINING_AMBUSH_DROPS.get(level, []))
            elif activity == "fishing":
                drop_table = list(FISHING_AMBUSH_DROPS.get(level, []))
            elif activity == "space":
                drop_table = list(SPACE_AMBUSH_DROPS.get(level, []))
            elif activity == "alien":
                drop_table = list(ALIEN_AMBUSH_DROPS)
            # Per-mob bonus drops (rare resources / effect items)
            drop_table.extend(AMBUSH_MOB_BONUS_DROPS.get(battle.mob_key, []))
        else:
            drop_table = list(DUNGEON_DROPS.get(battle.dungeon_level, []))
            # Boss bonus
            mob = MOBS.get(battle.mob_key)
            if mob and mob.is_boss:
                drop_table.extend(BOSS_BONUS_DROPS)

        for item_key, category, sell_value, chance in drop_table:
            if random.random() < chance:
                res = get_resource(item_key)
                display = res.display_name if res else item_key.replace("_", " ").title()
                drops.append((item_key, category, sell_value, display))

        return drops

    def grant_drops(self, user_id: int, drops: list[tuple[str, str, int, str]]) -> list[tuple[str, str]]:
        """Add dropped items to player inventory.

        Returns list of (item_key, display_name) for items actually granted.
        Equipment items use update_user_inventory; others use add_item.
        """
        granted: list[tuple[str, str]] = []
        for item_key, category, sell_value, display in drops:
            if category == "equipment":
                # Rare items stored in user_equipment table
                inv = self.repo.get_user_inventory(user_id)
                current = inv.get(item_key, 0)
                if item_key in ("golden_axe", "mithril_shield"):
                    # Permanent equipment — only grant if not owned
                    if current > 0:
                        continue
                    self.repo.update_user_inventory(user_id, item_key, 1)
                else:
                    # Stacking equipment (star_magnet, lucky_charm, etc.)
                    self.repo.update_user_inventory(user_id, item_key, current + 20)
                granted.append((item_key, display))
            else:
                if self.repo.add_item(user_id, item_key, category, sell_value):
                    granted.append((item_key, display))
        return granted

    # ── Battle initialization ─────────────────────────────────

    def start_fight(self, user_id: int, username: str) -> tuple[Optional[BattleState], str]:
        """Initialize a fight with a random mob at the user's active combat level.

        Returns (BattleState, "") on success, or (None, error_message) on failure.
        """
        stats = self.repo.get_combat_stats(user_id)

        # Check if user has unlocked combat
        if stats["combat_level"] < 0:
            return None, "You haven't unlocked the Noodle Colosseum yet!"

        active_level = stats["active_combat_level"]
        if active_level < 1 or active_level > 5:
            active_level = 1

        # Check combat level requirement
        unlock = COMBAT_LEVEL_UNLOCK.get(active_level, {})
        if stats["combat_level"] < unlock.get("required_combat_level", 0):
            return None, (
                f"You need **Combat Level {unlock['required_combat_level']}** "
                f"to fight in **{DUNGEON_LEVELS[active_level]['name']}**!"
            )

        # Check HP
        current_hp = stats["current_hp"] or BASE_HP
        max_hp = stats["max_hp"] or BASE_HP
        if current_hp <= 0:
            return None, "You're out of HP! Eat some fish with `!eat` to recover."

        # Check stamina
        current_stamina = stats["current_stamina"] or BASE_STAMINA
        max_stamina = stats["max_stamina"] or BASE_STAMINA
        if current_stamina < STAMINA_PER_ATTACK:
            return None, (
                f"You need at least **{STAMINA_PER_ATTACK} stamina** to fight! "
                f"Current: **{current_stamina}/{max_stamina}**. "
                "Use `!consume` to restore stamina."
            )

        # Pick a random mob
        level_mobs = MOBS_BY_LEVEL.get(active_level, [])
        if not level_mobs:
            return None, "No mobs found for this dungeon level!"

        mob = random.choice(level_mobs)

        # Calculate player stats from equipment
        player_atk = 5  # base attack
        player_def = 2  # base defense
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = stats.get(slot)
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                player_atk += item.attack
                player_def += item.defense

        battle = BattleState(
            mob_key=mob.key,
            mob_name=mob.name,
            mob_emoji=mob.emoji,
            dungeon_level=active_level,
            player_hp=current_hp,
            player_max_hp=max_hp,
            player_stamina=current_stamina,
            player_max_stamina=max_stamina,
            player_attack=player_atk,
            player_defense=player_def,
            mob_hp=mob.hp,
            mob_max_hp=mob.hp,
            mob_attack=mob.attack,
            mob_defense=mob.defense,
            mob_stamina=mob.stamina,
            mob_max_stamina=mob.stamina,
        )
        return battle, ""

    # ── Ambush initialization ──────────────────────────────────

    def start_ambush(
        self,
        user_id: int,
        username: str,
        mob,
        activity: str,
        activity_level: int,
        penalty: dict,
        flee_lockout_turns: int,
        atk_bonus: int = 0,
    ) -> tuple[Optional[BattleState], str]:
        """Initialize an ambush fight triggered by mining/fishing/space.

        Returns (BattleState, "") on success, or (None, error_message) on failure.
        If player has 0 HP or insufficient stamina, returns an error so the
        handler can apply auto-loss penalties.
        """
        stats = self.repo.get_combat_stats(user_id)
        current_hp = stats["current_hp"] or BASE_HP
        max_hp = stats["max_hp"] or BASE_HP
        current_stamina = stats["current_stamina"] or BASE_STAMINA
        max_stamina = stats["max_stamina"] or BASE_STAMINA

        if current_hp <= 0:
            return None, "You were too weak to fight back!"

        # Calculate player stats from equipment
        player_atk = 5 + atk_bonus
        player_def = 2
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = stats.get(slot)
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                player_atk += item.attack
                player_def += item.defense

        ambush_ctx = AmbushContext(
            activity=activity,
            activity_level=activity_level,
            penalty=penalty,
            flee_lockout_turns=flee_lockout_turns,
        )

        battle = BattleState(
            mob_key=mob.key,
            mob_name=mob.name,
            mob_emoji=mob.emoji,
            dungeon_level=activity_level,
            player_hp=current_hp,
            player_max_hp=max_hp,
            player_stamina=current_stamina,
            player_max_stamina=max_stamina,
            player_attack=player_atk,
            player_defense=player_def,
            mob_hp=mob.hp,
            mob_max_hp=mob.hp,
            mob_attack=mob.attack + atk_bonus,
            mob_defense=mob.defense,
            mob_stamina=mob.stamina,
            mob_max_stamina=mob.stamina,
            ambush=ambush_ctx,
        )
        return battle, ""

    # ── Turn execution ────────────────────────────────────────

    def execute_player_attack(self, battle: BattleState) -> BattleTurn:
        """Player attacks the mob. Returns the turn result."""
        battle.turn += 1

        # Stamina-scaled damage
        stam_ratio = max(DAMAGE_FLOOR, battle.player_stamina / battle.player_max_stamina)
        base_dmg = max(1, battle.player_attack - battle.mob_defense // 2)
        damage = max(1, int(base_dmg * stam_ratio * random.uniform(0.85, 1.15)))

        # Consume stamina
        battle.player_stamina = max(0, battle.player_stamina - STAMINA_PER_ATTACK)

        battle.mob_hp = max(0, battle.mob_hp - damage)

        turn = BattleTurn(
            turn_number=battle.turn,
            actor="player",
            action="attack",
            damage_dealt=damage,
            actor_hp=battle.player_hp,
            target_hp=battle.mob_hp,
            actor_stamina=battle.player_stamina,
            message=f"You slash at **{battle.mob_name}** for **{damage}** damage!",
        )
        battle.turns.append(turn)

        if battle.mob_hp <= 0:
            battle.finished = True
            battle.player_won = True

        return turn

    def execute_player_defend(self, battle: BattleState) -> BattleTurn:
        """Player defends (reduced stamina cost, blocks some damage next mob turn)."""
        battle.turn += 1
        battle.player_stamina = max(0, battle.player_stamina - STAMINA_PER_DEFEND)

        turn = BattleTurn(
            turn_number=battle.turn,
            actor="player",
            action="defend",
            damage_blocked=battle.player_defense,
            actor_hp=battle.player_hp,
            target_hp=battle.mob_hp,
            actor_stamina=battle.player_stamina,
            message="You raise your guard! 🛡️",
        )
        battle.turns.append(turn)
        return turn

    def execute_mob_turn(self, battle: BattleState, player_defended: bool = False) -> BattleTurn:
        """Mob attacks the player. Returns the turn result."""
        battle.turn += 1

        # Mob stamina scaling
        mob_stam_ratio = max(DAMAGE_FLOOR, battle.mob_stamina / battle.mob_max_stamina)
        base_dmg = max(1, battle.mob_attack - battle.player_defense // 2)
        damage = max(1, int(base_dmg * mob_stam_ratio * random.uniform(0.85, 1.15)))

        # If player defended, additional defense reduction
        if player_defended:
            damage = max(1, damage - battle.player_defense)

        # Mob loses stamina on attack
        battle.mob_stamina = max(0, battle.mob_stamina - 5)

        battle.player_hp = max(0, battle.player_hp - damage)

        turn = BattleTurn(
            turn_number=battle.turn,
            actor=battle.mob_name,
            action="attack",
            damage_dealt=damage,
            actor_hp=battle.mob_hp,
            target_hp=battle.player_hp,
            actor_stamina=battle.mob_stamina,
            message=f"{battle.mob_emoji} **{battle.mob_name}** attacks you for **{damage}** damage!",
        )
        battle.turns.append(turn)

        if battle.player_hp <= 0:
            battle.finished = True
            battle.player_won = False

        return turn

    # ── Flee ───────────────────────────────────────────────────

    def calc_flee_chance(self, battle: BattleState) -> float:
        """Calculate the probability of a successful flee.

        At full stamina the player has a 90% chance regardless of stats.
        At zero stamina the floor depends on defence vs mob attack:
          • def >= mob_atk  → 75%
          • def == 0        → 50%
          • in between      → linear interpolation (50-75%)
        The final chance is linearly interpolated between the floor and 90%
        using the player's current stamina ratio.
        """
        stam_ratio = (
            battle.player_stamina / battle.player_max_stamina
            if battle.player_max_stamina > 0
            else 0.0
        )

        # Defence ratio: how close player def is to mob atk (capped at 1.0)
        def_ratio = (
            min(1.0, battle.player_defense / battle.mob_attack)
            if battle.mob_attack > 0
            else 1.0
        )

        floor = 0.50 + 0.25 * def_ratio   # 50% → 75%
        ceiling = 0.90

        return floor + (ceiling - floor) * stam_ratio

    def attempt_flee(self, battle: BattleState) -> tuple[bool, float]:
        """Roll for flee. Returns (success, chance_used)."""
        chance = self.calc_flee_chance(battle)
        return random.random() < chance, chance

    # ── Battle resolution ─────────────────────────────────────

    def resolve_victory(self, user_id: int, username: str, battle: BattleState) -> BattleResult:
        """Handle victory — award stars, roll drops, check level up, save state."""
        # Save HP/stamina
        self.repo.update_hp(user_id, battle.player_hp)
        self.repo.update_stamina(user_id, battle.player_stamina)

        # Roll and grant drops (for all victory types)
        raw_drops = self.roll_drops(battle)
        granted = self.grant_drops(user_id, raw_drops)

        # Ambush victory: no star reward, just survival + drops
        if battle.ambush:
            return BattleResult(
                success=True,
                won=True,
                message=f"You fought off the **{battle.mob_name}**! Your loot is safe.",
                mob_name=battle.mob_name,
                mob_emoji=battle.mob_emoji,
                turns=battle.turns,
                drops=granted,
            )

        # Dungeon victory: award stars and check level up
        mob = MOBS.get(battle.mob_key)
        star_reward = mob.star_reward if mob else 50

        current_stars = self.repo.get_user_stars(user_id, username)
        self.repo.update_user_stars(user_id, username, current_stars + star_reward)

        stats = self.repo.get_combat_stats(user_id)
        combat_level = stats["combat_level"]
        wins_at_level = self.repo.get_combat_wins_at_level(user_id, battle.dungeon_level) + 1
        level_up = False
        new_level = combat_level

        if wins_at_level >= WINS_PER_COMBAT_LEVEL and combat_level == battle.dungeon_level - 1:
            new_level = combat_level + 1
            self.repo.update_combat_level(user_id, new_level)
            level_up = True

        self.repo.log_combat(
            user_id=user_id,
            dungeon_level=battle.dungeon_level,
            mob_key=battle.mob_key,
            result="win",
            stars_change=star_reward,
        )

        boss_text = " **BOSS DEFEATED!**" if (mob and mob.is_boss) else ""

        return BattleResult(
            success=True,
            won=True,
            message=f"Victory!{boss_text} You earned **{star_reward}** stars!",
            mob_name=battle.mob_name,
            mob_emoji=battle.mob_emoji,
            stars_earned=star_reward,
            combat_level_up=level_up,
            new_combat_level=new_level,
            turns=battle.turns,
            drops=granted,
        )

    def resolve_defeat(self, user_id: int, username: str, battle: BattleState) -> BattleResult:
        """Handle defeat — apply death penalties based on dungeon level or ambush context."""
        if battle.ambush:
            penalty = battle.ambush.penalty
        else:
            penalty = DEATH_PENALTIES.get(battle.dungeon_level, DEATH_PENALTIES[1])

        stars_lost = 0
        items_lost = []
        equipment_lost = []
        bank_loss = 0

        # Heart of Leviathan: full protection from ALL defeat penalties (1 use)
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

            # Bank loss (Bank Insurance can still protect)
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
                # Unequip combat slots
                for slot in ("weapon", "shield", "armor"):
                    self.repo.set_equipped_combat_item(user_id, slot, None)
            elif penalty["lose_random_equipment"] > 0:
                equip = self.repo.get_user_equipment(user_id)
                equip_keys = list(equip.keys())
                count = min(penalty["lose_random_equipment"], len(equip_keys))
                if count > 0:
                    to_remove = random.sample(equip_keys, count)
                    stats = self.repo.get_combat_stats(user_id)
                    for key in to_remove:
                        equipment_lost.append(key)
                        self.repo.set_equipment(user_id, key, 0)
                        # Unequip if it was equipped
                        for slot in ("weapon", "shield", "armor"):
                            if stats.get(f"equipped_{slot}") == key:
                                self.repo.set_equipped_combat_item(user_id, slot, None)

        # Save HP (player is at 0) — set to 1 so they can recover
        self.repo.update_hp(user_id, 1)
        self.repo.update_stamina(user_id, battle.player_stamina)

        # Recalculate max HP after equipment loss
        max_hp = BASE_HP
        new_stats = self.repo.get_combat_stats(user_id)
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = new_stats.get(slot)
            if key and key in COMBAT_ITEMS:
                max_hp += COMBAT_ITEMS[key].hp_bonus
        self.repo.update_hp(user_id, 1, max_hp)

        # Log combat
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
        return BattleResult(
            success=True,
            won=False,
            message=defeat_msg,
            mob_name=battle.mob_name,
            mob_emoji=battle.mob_emoji,
            stars_lost=stars_lost,
            items_lost=items_lost,
            equipment_lost=equipment_lost,
            bank_loss=bank_loss,
            turns=battle.turns,
        )

    # ── Dungeon level management ──────────────────────────────

    def unlock_dungeon(self, user_id: int, username: str, level: int) -> DungeonUnlockResult:
        """Unlock a dungeon level by paying stars."""
        if level not in DUNGEON_LEVELS:
            return DungeonUnlockResult(
                success=False,
                message=f"Invalid dungeon level! Valid: 1-5",
            )

        stats = self.repo.get_combat_stats(user_id)
        unlock = COMBAT_LEVEL_UNLOCK.get(level, {})
        required = unlock.get("required_combat_level", 0)

        if stats["combat_level"] < required:
            return DungeonUnlockResult(
                success=False,
                message=f"You need **Combat Level {required}** to unlock this dungeon!",
            )

        cost = unlock.get("cost", 0)
        if cost > 0:
            current_stars = self.repo.get_user_stars(user_id, username)
            if current_stars < cost:
                return DungeonUnlockResult(
                    success=False,
                    message=f"You need **{cost}** stars to unlock this dungeon! You have **{current_stars}**.",
                    level=level, cost=cost,
                )
            self.repo.update_user_stars(user_id, username, current_stars - cost)

        self.repo.update_active_combat_level(user_id, level)
        dungeon = DUNGEON_LEVELS[level]
        return DungeonUnlockResult(
            success=True,
            message=f"Unlocked **{dungeon['name']}** {dungeon['emoji']}! Cost: **{cost}** stars.",
            level=level, cost=cost,
        )

    def set_active_level(self, user_id: int, level: int) -> DungeonUnlockResult:
        """Switch to a different dungeon level."""
        if level not in DUNGEON_LEVELS:
            return DungeonUnlockResult(success=False, message="Invalid level! Valid: 1-5")

        stats = self.repo.get_combat_stats(user_id)
        unlock = COMBAT_LEVEL_UNLOCK.get(level, {})
        required = unlock.get("required_combat_level", 0)

        if stats["combat_level"] < required:
            return DungeonUnlockResult(
                success=False,
                message=f"You need **Combat Level {required}** to access this dungeon!",
            )

        self.repo.update_active_combat_level(user_id, level)
        dungeon = DUNGEON_LEVELS[level]
        return DungeonUnlockResult(
            success=True,
            message=f"Now fighting in **{dungeon['name']}** {dungeon['emoji']}!",
            level=level,
        )

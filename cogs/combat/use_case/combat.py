"""Core combat use cases — fighting mobs, death penalties, level progression."""

import random
from typing import Optional

from cogs.combat.constants import (
    BASE_HP, BASE_STAMINA, COMBAT_ITEMS, COMBAT_LEVEL_UNLOCK,
    DAMAGE_FLOOR, DEATH_PENALTIES, DUNGEON_LEVELS, MOBS, MOBS_BY_LEVEL,
    STAMINA_PER_ATTACK, STAMINA_PER_DEFEND, WINS_PER_COMBAT_LEVEL,
)
from cogs.combat.dto import BattleResult, BattleState, BattleTurn, DungeonUnlockResult
from database.repository import UserRepository


class CombatUseCases:
    """Core combat business logic — fights, death penalties, level management."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

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
                "Use `!drink` to restore stamina."
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

    # ── Battle resolution ─────────────────────────────────────

    def resolve_victory(self, user_id: int, username: str, battle: BattleState) -> BattleResult:
        """Handle victory — award stars, check level up, save state."""
        mob = MOBS.get(battle.mob_key)
        star_reward = mob.star_reward if mob else 50

        # Award stars
        current_stars = self.repo.get_user_stars(user_id, username)
        self.repo.update_user_stars(user_id, username, current_stars + star_reward)

        # Save HP/stamina
        self.repo.update_hp(user_id, battle.player_hp)
        self.repo.update_stamina(user_id, battle.player_stamina)

        # Check combat level progression
        stats = self.repo.get_combat_stats(user_id)
        combat_level = stats["combat_level"]
        wins_at_level = self.repo.get_combat_wins_at_level(user_id, battle.dungeon_level) + 1  # +1 for this win
        level_up = False
        new_level = combat_level

        if wins_at_level >= WINS_PER_COMBAT_LEVEL and combat_level == battle.dungeon_level - 1:
            # Can level up if fighting at the appropriate level
            new_level = combat_level + 1
            self.repo.update_combat_level(user_id, new_level)
            level_up = True

        # Log combat
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
        )

    def resolve_defeat(self, user_id: int, username: str, battle: BattleState) -> BattleResult:
        """Handle defeat — apply death penalties based on dungeon level."""
        penalty = DEATH_PENALTIES.get(battle.dungeon_level, DEATH_PENALTIES[1])

        stars_lost = 0
        items_lost = []
        equipment_lost = []
        bank_loss = 0

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
        return BattleResult(
            success=True,
            won=False,
            message=f"Defeated by **{battle.mob_name}**! {penalty_desc}",
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

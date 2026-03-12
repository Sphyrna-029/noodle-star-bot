"""Coop combat use cases — round-based multiplayer fights."""

import random
from typing import Optional

from cogs.combat.constants import (
    BASE_HP, BASE_STAMINA, COMBAT_ITEMS, COOP_MAX_PLAYERS,
    COOP_MOB_DAMAGE_FALLOFF, COOP_REWARD_MULTIPLIER,
    DAMAGE_FLOOR, DEATH_PENALTIES, MOBS, STAMINA_PER_ATTACK,
    STAMINA_PER_DEFEND, WINS_PER_COMBAT_LEVEL,
)
from cogs.combat.dto import (
    AmbushContext, BattleState, BattleTurn, CoopBattleState, CoopPlayer,
)
from cogs.combat.use_case.health import HealthUseCases
from database.repository import UserRepository


class CoopCombatUseCases:
    """Coop combat business logic — round resolution, multi-attack, rewards."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()
        self._health_uc = HealthUseCases(self.repo)

    # ── Conversion from solo to coop ────────────────────────

    def convert_to_coop(self, battle: BattleState, user_id: int, username: str) -> CoopBattleState:
        """Convert a solo BattleState into a CoopBattleState with 1 player."""
        player = CoopPlayer(
            user_id=user_id,
            username=username,
            hp=battle.player_hp,
            max_hp=battle.player_max_hp,
            stamina=battle.player_stamina,
            max_stamina=battle.player_max_stamina,
            attack=battle.player_attack,
            defense=battle.player_defense,
        )
        return CoopBattleState(
            mob_key=battle.mob_key,
            mob_name=battle.mob_name,
            mob_emoji=battle.mob_emoji,
            dungeon_level=battle.dungeon_level,
            players=[player],
            mob_hp=battle.mob_hp,
            mob_max_hp=battle.mob_max_hp,
            mob_attack=battle.mob_attack,
            mob_defense=battle.mob_defense,
            mob_stamina=battle.mob_stamina,
            mob_max_stamina=battle.mob_max_stamina,
            round=0,
            turns=list(battle.turns),
            ambush=battle.ambush,
            original_user_id=user_id,
            open_for_join=True,
        )

    # ── Adding a player ─────────────────────────────────────

    def add_player(self, state: CoopBattleState, user_id: int, username: str) -> Optional[str]:
        """Add a player to a coop battle.

        Returns None on success, or an error string on failure.
        """
        alive_count = sum(1 for p in state.players if p.alive)
        if alive_count >= COOP_MAX_PLAYERS:
            return "This fight is already full!"

        if any(p.user_id == user_id for p in state.players):
            return "You're already in this fight!"

        # Load player stats
        stats = self.repo.get_combat_stats(user_id)
        current_hp = stats["current_hp"] or BASE_HP
        max_hp = stats["max_hp"] or BASE_HP
        current_stamina = stats["current_stamina"] or BASE_STAMINA
        max_stamina = stats["max_stamina"] or BASE_STAMINA

        if current_hp <= 0:
            return "You're out of HP! Use `!consume` to recover."
        if current_stamina < STAMINA_PER_ATTACK:
            return f"You need at least **{STAMINA_PER_ATTACK} stamina** to join!"

        # Calculate ATK/DEF from equipment
        player_atk = 5
        player_def = 2
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = stats.get(slot)
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                player_atk += item.attack
                player_def += item.defense

        player = CoopPlayer(
            user_id=user_id,
            username=username,
            hp=current_hp,
            max_hp=max_hp,
            stamina=current_stamina,
            max_stamina=max_stamina,
            attack=player_atk,
            defense=player_def,
        )
        state.players.append(player)
        return None

    # ── Round checks ─────────────────────────────────────────

    def all_actions_chosen(self, state: CoopBattleState) -> bool:
        """Return True if all living players have chosen an action."""
        return all(p.action is not None for p in state.players if p.alive)

    # ── Round resolution ─────────────────────────────────────

    def resolve_round(self, state: CoopBattleState) -> list[BattleTurn]:
        """Resolve one round of coop combat. Returns the turn log."""
        state.round += 1
        round_turns: list[BattleTurn] = []

        # --- Player actions ---
        for player in state.players:
            if not player.alive or player.action is None:
                continue

            if player.action == "attack":
                turn = self._resolve_player_attack(state, player)
                round_turns.append(turn)

            elif player.action == "defend":
                turn = self._resolve_player_defend(state, player)
                round_turns.append(turn)

            elif player.action == "consume":
                turn = self._resolve_player_consume(state, player)
                round_turns.append(turn)

            elif player.action == "flee":
                turn = self._resolve_player_flee(state, player)
                round_turns.append(turn)

        # Check mob death
        if state.mob_hp <= 0:
            state.finished = True
            state.turns.extend(round_turns)
            self._clear_actions(state)
            return round_turns

        # --- Mob multi-attack ---
        alive_players = [p for p in state.players if p.alive]
        if not alive_players:
            state.finished = True
            state.turns.extend(round_turns)
            self._clear_actions(state)
            return round_turns

        random.shuffle(alive_players)
        mob_stam_ratio = max(DAMAGE_FLOOR, state.mob_stamina / state.mob_max_stamina)

        for i, target in enumerate(alive_players):
            falloff = COOP_MOB_DAMAGE_FALLOFF[i] if i < len(COOP_MOB_DAMAGE_FALLOFF) else COOP_MOB_DAMAGE_FALLOFF[-1]
            base_dmg = max(1, state.mob_attack - target.defense // 2)
            damage = max(1, int(base_dmg * mob_stam_ratio * random.uniform(0.85, 1.15) * falloff))

            if target.defending:
                damage = max(1, damage - target.defense)

            target.hp = max(0, target.hp - damage)

            pct_text = f" ({int(falloff * 100)}%)" if falloff < 1.0 else ""
            turn = BattleTurn(
                turn_number=state.round,
                actor=state.mob_name,
                action="attack",
                damage_dealt=damage,
                actor_hp=state.mob_hp,
                target_hp=target.hp,
                actor_stamina=state.mob_stamina,
                message=f"{state.mob_emoji} **{state.mob_name}** hits **{target.username}** for **{damage}**!{pct_text}",
            )
            round_turns.append(turn)

            if target.hp <= 0:
                target.alive = False
                self._resolve_player_defeat(state, target)
                defeat_turn = BattleTurn(
                    turn_number=state.round,
                    actor=target.username,
                    action="defeated",
                    actor_hp=0,
                    target_hp=state.mob_hp,
                    message=f"💀 **{target.username}** has been defeated!",
                )
                round_turns.append(defeat_turn)

        # Mob loses stamina once per attack cycle
        state.mob_stamina = max(0, state.mob_stamina - 5)

        # Check if all players are dead
        if not any(p.alive for p in state.players):
            state.finished = True

        state.turns.extend(round_turns)
        self._clear_actions(state)
        return round_turns

    # ── Individual action resolution ─────────────────────────

    def _resolve_player_attack(self, state: CoopBattleState, player: CoopPlayer) -> BattleTurn:
        stam_ratio = max(DAMAGE_FLOOR, player.stamina / player.max_stamina)
        base_dmg = max(1, player.attack - state.mob_defense // 2)
        damage = max(1, int(base_dmg * stam_ratio * random.uniform(0.85, 1.15)))
        player.stamina = max(0, player.stamina - STAMINA_PER_ATTACK)
        state.mob_hp = max(0, state.mob_hp - damage)

        return BattleTurn(
            turn_number=state.round,
            actor=player.username,
            action="attack",
            damage_dealt=damage,
            actor_hp=player.hp,
            target_hp=state.mob_hp,
            actor_stamina=player.stamina,
            message=f"⚔️ **{player.username}** hits **{state.mob_name}** for **{damage}**!",
        )

    def _resolve_player_defend(self, state: CoopBattleState, player: CoopPlayer) -> BattleTurn:
        player.stamina = max(0, player.stamina - STAMINA_PER_DEFEND)
        player.defending = True

        return BattleTurn(
            turn_number=state.round,
            actor=player.username,
            action="defend",
            damage_blocked=player.defense,
            actor_hp=player.hp,
            target_hp=state.mob_hp,
            actor_stamina=player.stamina,
            message=f"🛡️ **{player.username}** defends!",
        )

    def _resolve_player_consume(self, state: CoopBattleState, player: CoopPlayer) -> BattleTurn:
        item_key = player.consume_item
        consume_type = player.consume_type
        display = item_key.replace("_", " ").title() if item_key else "Unknown"

        if consume_type == "hp":
            heal = self._health_uc.get_hp_value(item_key) or 0
            if heal > 0 and self._health_uc._find_and_remove(player.user_id, item_key):
                old_hp = player.hp
                player.hp = min(player.max_hp, old_hp + heal)
                actual = player.hp - old_hp
                msg = f"🍖 **{player.username}** consumed **{display}** (+{actual} HP)!"
            else:
                msg = f"❌ **{player.username}** failed to consume **{display}**!"
        else:
            from cogs.combat.constants import STAMINA_RECOVERY
            recovery = STAMINA_RECOVERY.get(item_key, 0)
            if recovery > 0 and self._health_uc._find_and_remove(player.user_id, item_key):
                old_stam = player.stamina
                player.stamina = min(player.max_stamina, old_stam + recovery)
                actual = player.stamina - old_stam
                msg = f"⚡ **{player.username}** consumed **{display}** (+{actual} stamina)!"
            else:
                msg = f"❌ **{player.username}** failed to consume **{display}**!"

        return BattleTurn(
            turn_number=state.round,
            actor=player.username,
            action="consume",
            actor_hp=player.hp,
            target_hp=state.mob_hp,
            actor_stamina=player.stamina,
            message=msg,
        )

    def _resolve_player_flee(self, state: CoopBattleState, player: CoopPlayer) -> BattleTurn:
        # Flee chance: same formula as solo
        stam_ratio = player.stamina / player.max_stamina if player.max_stamina > 0 else 0.0
        def_ratio = min(1.0, player.defense / state.mob_attack) if state.mob_attack > 0 else 1.0
        floor = 0.50 + 0.25 * def_ratio
        ceiling = 0.90
        chance = floor + (ceiling - floor) * stam_ratio

        # Ambush flee lockout applies only to original player
        if state.ambush and player.user_id == state.original_user_id:
            if state.round <= state.ambush.flee_lockout_turns:
                return BattleTurn(
                    turn_number=state.round,
                    actor=player.username,
                    action="flee_fail",
                    actor_hp=player.hp,
                    target_hp=state.mob_hp,
                    actor_stamina=player.stamina,
                    message=f"🏃 **{player.username}** can't flee yet! (ambush lockout)",
                )

        escaped = random.random() < chance
        pct = int(chance * 100)

        if escaped:
            player.alive = False  # removed from fight
            # Save HP/stamina — they fled, no penalty
            self.repo.update_hp(player.user_id, player.hp)
            self.repo.update_stamina(player.user_id, player.stamina)
            return BattleTurn(
                turn_number=state.round,
                actor=player.username,
                action="flee",
                actor_hp=player.hp,
                target_hp=state.mob_hp,
                actor_stamina=player.stamina,
                message=f"🏃 **{player.username}** fled the battle! ({pct}%)",
            )
        else:
            return BattleTurn(
                turn_number=state.round,
                actor=player.username,
                action="flee_fail",
                actor_hp=player.hp,
                target_hp=state.mob_hp,
                actor_stamina=player.stamina,
                message=f"🏃 **{player.username}** tried to flee but failed! ({pct}%)",
            )

    # ── Defeat / Victory ────────────────────────────────────

    def _resolve_player_defeat(self, state: CoopBattleState, player: CoopPlayer):
        """Apply death penalties to a defeated player."""
        if state.ambush:
            penalty = state.ambush.penalty
        else:
            penalty = DEATH_PENALTIES.get(state.dungeon_level, DEATH_PENALTIES[1])

        # Wallet loss
        current_stars = self.repo.get_user_stars(player.user_id, player.username)
        if penalty["wallet_loss_pct"] > 0:
            stars_lost = int(current_stars * penalty["wallet_loss_pct"])
            self.repo.update_user_stars(player.user_id, player.username, max(0, current_stars - stars_lost))

        # Bank loss
        if penalty["bank_loss_pct"] > 0:
            current_bank = self.repo.get_user_bank(player.user_id)
            bank_loss = int(current_bank * penalty["bank_loss_pct"])
            if bank_loss > 0:
                inv = self.repo.get_user_inventory(player.user_id)
                heart_uses = inv.get("heart_of_leviathan", 0)
                bank_ins = inv.get("bank_insurance", 0)
                if heart_uses > 0:
                    self.repo.update_user_inventory(player.user_id, "heart_of_leviathan", heart_uses - 1)
                elif bank_ins > 0:
                    self.repo.update_user_inventory(player.user_id, "bank_insurance", bank_ins - 1)
                else:
                    self.repo.update_user_bank(player.user_id, player.username, max(0, current_bank - bank_loss))

        # Item losses
        if penalty["lose_all_items"]:
            self.repo.clear_inventory(player.user_id)
        elif penalty["lose_random_items_pct"] > 0:
            inv_items = self.repo.get_inventory_items(player.user_id)
            count_to_lose = max(1, int(len(inv_items) * penalty["lose_random_items_pct"]))
            to_remove = random.sample(inv_items, min(count_to_lose, len(inv_items)))
            for item in to_remove:
                self.repo.remove_items_by_ids(player.user_id, [item["id"]])

        # Equipment losses
        if penalty["lose_all_equipment"]:
            self.repo.clear_all_equipment(player.user_id)
            for slot in ("weapon", "shield", "armor"):
                self.repo.set_equipped_combat_item(player.user_id, slot, None)
        elif penalty["lose_random_equipment"] > 0:
            equip = self.repo.get_user_equipment(player.user_id)
            equip_keys = list(equip.keys())
            count = min(penalty["lose_random_equipment"], len(equip_keys))
            if count > 0:
                to_remove = random.sample(equip_keys, count)
                stats = self.repo.get_combat_stats(player.user_id)
                for key in to_remove:
                    self.repo.set_equipment(player.user_id, key, 0)
                    for slot in ("weapon", "shield", "armor"):
                        if stats.get(f"equipped_{slot}") == key:
                            self.repo.set_equipped_combat_item(player.user_id, slot, None)

        # Set HP to 1
        self.repo.update_hp(player.user_id, 1)
        self.repo.update_stamina(player.user_id, player.stamina)

        # Recalculate max HP after equipment loss
        new_stats = self.repo.get_combat_stats(player.user_id)
        max_hp = BASE_HP
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = new_stats.get(slot)
            if key and key in COMBAT_ITEMS:
                max_hp += COMBAT_ITEMS[key].hp_bonus
        self.repo.update_hp(player.user_id, 1, max_hp)

    def resolve_coop_victory(self, state: CoopBattleState) -> dict[int, int]:
        """Award victory rewards to all living players.

        Returns {user_id: stars_earned} for living players.
        """
        # Players who fled are not alive but also didn't lose — save was
        # already done in _resolve_player_flee. They get no rewards.
        alive_players = [p for p in state.players if p.alive]
        rewards: dict[int, int] = {}

        if not alive_players:
            return rewards

        # Ambush victory: no star reward
        if state.ambush:
            for player in alive_players:
                self.repo.update_hp(player.user_id, player.hp)
                self.repo.update_stamina(player.user_id, player.stamina)
                rewards[player.user_id] = 0
            return rewards

        mob = MOBS.get(state.mob_key)
        base_reward = mob.star_reward if mob else 50
        multiplier = COOP_REWARD_MULTIPLIER.get(len(alive_players), 0.40)
        star_reward = max(1, int(base_reward * multiplier))

        for player in alive_players:
            # Save HP/stamina
            self.repo.update_hp(player.user_id, player.hp)
            self.repo.update_stamina(player.user_id, player.stamina)

            # Award stars
            current_stars = self.repo.get_user_stars(player.user_id, player.username)
            self.repo.update_user_stars(player.user_id, player.username, current_stars + star_reward)

            # Combat level progression
            stats = self.repo.get_combat_stats(player.user_id)
            combat_level = stats["combat_level"]
            wins_at_level = self.repo.get_combat_wins_at_level(player.user_id, state.dungeon_level) + 1
            if wins_at_level >= WINS_PER_COMBAT_LEVEL and combat_level == state.dungeon_level - 1:
                self.repo.update_combat_level(player.user_id, combat_level + 1)

            self.repo.log_combat(
                user_id=player.user_id,
                dungeon_level=state.dungeon_level,
                mob_key=state.mob_key,
                result="win",
                stars_change=star_reward,
            )

            rewards[player.user_id] = star_reward

        return rewards

    # ── Helpers ──────────────────────────────────────────────

    def _clear_actions(self, state: CoopBattleState):
        """Clear all player actions and defending flags for next round."""
        for p in state.players:
            p.action = None
            p.consume_item = None
            p.consume_type = None
            p.defending = False

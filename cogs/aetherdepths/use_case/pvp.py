"""Aetherdepths PvP use cases — non-consensual dungeon PvP."""

import random
from datetime import datetime, timedelta
from typing import Optional

from cogs.aetherdepths.constants import (
    AETHER_DEATH_PENALTIES,
    PVP_COOLDOWN_SECONDS,
    PVP_KILL_REWARD_PCT,
)
from cogs.aetherdepths.dto import PvPBattleResult, PvPBattleState
from cogs.combat.constants import BASE_HP, BASE_STAMINA, COMBAT_ITEMS, DAMAGE_FLOOR, STAMINA_PER_ATTACK, STAMINA_PER_DEFEND, MOB_STAMINA_PER_ATTACK, calc_defend_stamina_cost
from cogs.combat.dto import BattleTurn
from database.repository import UserRepository


class PvPUseCases:
    """PvP combat logic for The Aetherdepths."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def validate_pvp(
        self, attacker_id: int, defender_id: int, attacker_level: int,
        defender_level: int | None, modifier: dict | None = None,
    ) -> tuple[bool, str]:
        """Validate that a PvP fight can happen."""
        if attacker_id == defender_id:
            return False, "You can't attack yourself!"

        if modifier and modifier.get("no_pvp"):
            return False, "PvP is disabled today due to the **Calm Depths** modifier."

        if attacker_level < 2:
            return False, "PvP is only available on **Level 2+** of The Aetherdepths!"

        if defender_level is None:
            return False, "That player is not in The Aetherdepths!"

        if defender_level != attacker_level:
            return False, (
                f"You're on Level {attacker_level} but they're on Level {defender_level}. "
                "You must be on the **same level** to PvP!"
            )

        # Check cooldown on victim
        last_pvp = self.repo.get_last_pvp_time(defender_id)
        if last_pvp:
            last_time = datetime.fromisoformat(last_pvp)
            cooldown_end = last_time + timedelta(seconds=PVP_COOLDOWN_SECONDS)
            now = datetime.utcnow()
            if now < cooldown_end:
                remaining = int((cooldown_end - now).total_seconds())
                return False, (
                    f"That player was recently attacked. "
                    f"PvP cooldown: **{remaining}s** remaining."
                )

        return True, ""

    def init_pvp(
        self, attacker_id: int, attacker_name: str,
        defender_id: int, defender_name: str, level: int,
    ) -> tuple[Optional[PvPBattleState], str]:
        """Initialize a PvP battle."""
        atk_stats = self.repo.get_combat_stats(attacker_id)
        def_stats = self.repo.get_combat_stats(defender_id)

        # Load attacker stats
        atk_hp = atk_stats["current_hp"] if atk_stats["current_hp"] is not None else BASE_HP
        atk_max_hp = atk_stats["max_hp"] if atk_stats["max_hp"] is not None else BASE_HP
        atk_stam = atk_stats["current_stamina"] if atk_stats["current_stamina"] is not None else BASE_STAMINA
        atk_max_stam = atk_stats["max_stamina"] if atk_stats["max_stamina"] is not None else BASE_STAMINA

        if atk_hp <= 0:
            return None, "You're out of HP!"
        if atk_stam < STAMINA_PER_ATTACK:
            return None, f"You need at least **{STAMINA_PER_ATTACK} stamina** to fight!"

        # Load defender stats
        def_hp = def_stats["current_hp"] if def_stats["current_hp"] is not None else BASE_HP
        def_max_hp = def_stats["max_hp"] if def_stats["max_hp"] is not None else BASE_HP
        def_stam = def_stats["current_stamina"] if def_stats["current_stamina"] is not None else BASE_STAMINA
        def_max_stam = def_stats["max_stamina"] if def_stats["max_stamina"] is not None else BASE_STAMINA

        if def_hp <= 0:
            return None, "Your target has no HP — they're already down!"

        # Calculate combat stats from equipment
        atk_attack = 5
        atk_defense = 2
        def_attack = 5
        def_defense = 2

        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = atk_stats.get(slot)
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                atk_attack += item.attack
                atk_defense += item.defense

            key = def_stats.get(slot)
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                def_attack += item.attack
                def_defense += item.defense

        state = PvPBattleState(
            attacker_id=attacker_id,
            attacker_name=attacker_name,
            defender_id=defender_id,
            defender_name=defender_name,
            aether_level=level,
            atk_hp=atk_hp,
            atk_max_hp=atk_max_hp,
            atk_stamina=atk_stam,
            atk_max_stamina=atk_max_stam,
            atk_attack=atk_attack,
            atk_defense=atk_defense,
            def_hp=def_hp,
            def_max_hp=def_max_hp,
            def_stamina=def_stam,
            def_max_stamina=def_max_stam,
            def_attack=def_attack,
            def_defense=def_defense,
        )
        return state, ""

    def execute_attack(self, state: PvPBattleState) -> BattleTurn:
        """Active player attacks the other."""
        state.turn += 1
        is_attacker = state.active_player == 0

        if is_attacker:
            atk_power = state.atk_attack
            def_power = state.def_defense
            stam = state.atk_stamina
            max_stam = state.atk_max_stamina
            target_hp = state.def_hp
            actor_name = state.attacker_name
            target_name = state.defender_name
        else:
            atk_power = state.def_attack
            def_power = state.atk_defense
            stam = state.def_stamina
            max_stam = state.def_max_stamina
            target_hp = state.atk_hp
            actor_name = state.defender_name
            target_name = state.attacker_name

        stam_ratio = max(DAMAGE_FLOOR, stam / max_stam) if max_stam > 0 else DAMAGE_FLOOR
        base_dmg = max(1, atk_power - def_power // 2)
        damage = max(1, int(base_dmg * stam_ratio * random.uniform(0.85, 1.15)))

        # Extra reduction if target is defending
        target_defending = state.def_defending if is_attacker else state.atk_defending
        if target_defending:
            damage = max(1, damage - def_power)

        # Consume stamina
        if is_attacker:
            state.atk_stamina = max(0, state.atk_stamina - STAMINA_PER_ATTACK)
            state.def_hp = max(0, state.def_hp - damage)
            actor_hp = state.atk_hp
            target_hp = state.def_hp
            actor_stam = state.atk_stamina
        else:
            state.def_stamina = max(0, state.def_stamina - STAMINA_PER_ATTACK)
            state.atk_hp = max(0, state.atk_hp - damage)
            actor_hp = state.def_hp
            target_hp = state.atk_hp
            actor_stam = state.def_stamina

        turn = BattleTurn(
            turn_number=state.turn,
            actor=actor_name,
            action="attack",
            damage_dealt=damage,
            actor_hp=actor_hp,
            target_hp=target_hp,
            actor_stamina=actor_stam,
            message=f"**{actor_name}** attacks **{target_name}** for **{damage}** damage!",
        )
        state.turns.append(turn)

        # Check for finish
        if state.atk_hp <= 0:
            state.finished = True
            state.winner_id = state.defender_id
            state.loser_id = state.attacker_id
        elif state.def_hp <= 0:
            state.finished = True
            state.winner_id = state.attacker_id
            state.loser_id = state.defender_id
        else:
            # Switch turns
            state.active_player = 1 - state.active_player
            # Clear defending flag for the player who was just hit
            if is_attacker:
                state.def_defending = False
            else:
                state.atk_defending = False

        return turn

    def execute_defend(self, state: PvPBattleState) -> BattleTurn:
        """Active player defends."""
        state.turn += 1
        is_attacker = state.active_player == 0

        if is_attacker:
            incoming_atk = state.def_attack
            player_def = state.atk_defense
            defend_cost = calc_defend_stamina_cost(player_def, incoming_atk)
            state.atk_stamina = max(0, state.atk_stamina - defend_cost)
            state.atk_defending = True
            actor_name = state.attacker_name
            actor_hp = state.atk_hp
            actor_stam = state.atk_stamina
        else:
            incoming_atk = state.atk_attack
            player_def = state.def_defense
            defend_cost = calc_defend_stamina_cost(player_def, incoming_atk)
            state.def_stamina = max(0, state.def_stamina - defend_cost)
            state.def_defending = True
            actor_name = state.defender_name
            actor_hp = state.def_hp
            actor_stam = state.def_stamina

        turn = BattleTurn(
            turn_number=state.turn,
            actor=actor_name,
            action="defend",
            damage_blocked=player_def,
            actor_hp=actor_hp,
            target_hp=state.def_hp if is_attacker else state.atk_hp,
            actor_stamina=actor_stam,
            message=f"**{actor_name}** raises their guard! 🛡️",
        )
        state.turns.append(turn)

        # Switch turns
        state.active_player = 1 - state.active_player
        return turn

    def resolve_pvp(
        self, state: PvPBattleState, winner_name: str, loser_name: str,
    ) -> PvPBattleResult:
        """Resolve PvP outcome — apply penalties to loser, reward winner."""
        winner_id = state.winner_id
        loser_id = state.loser_id
        level = state.aether_level

        penalty = AETHER_DEATH_PENALTIES.get(level, AETHER_DEATH_PENALTIES[1])

        # Apply penalty to loser
        loser_stars = self.repo.get_user_stars(loser_id, loser_name)
        stars_lost = int(loser_stars * penalty["wallet_loss_pct"])
        self.repo.update_user_stars(loser_id, loser_name, max(0, loser_stars - stars_lost))

        # Winner gets PVP_KILL_REWARD_PCT of the stars lost
        reward = int(stars_lost * PVP_KILL_REWARD_PCT)
        winner_stars = self.repo.get_user_stars(winner_id, winner_name)
        self.repo.update_user_stars(winner_id, winner_name, winner_stars + reward)

        # Save HP/stamina for both
        self.repo.update_hp(winner_id, state.atk_hp if winner_id == state.attacker_id else state.def_hp)
        self.repo.update_stamina(winner_id, state.atk_stamina if winner_id == state.attacker_id else state.def_stamina)
        self.repo.update_hp(loser_id, 1)
        self.repo.update_stamina(loser_id, state.atk_stamina if loser_id == state.attacker_id else state.def_stamina)

        # Log
        self.repo.log_pvp(
            attacker_id=state.attacker_id,
            defender_id=state.defender_id,
            aether_level=level,
            result="attacker_win" if winner_id == state.attacker_id else "defender_win",
            attacker_stars_change=reward if winner_id == state.attacker_id else -stars_lost,
            defender_stars_change=reward if winner_id == state.defender_id else -stars_lost,
        )

        return PvPBattleResult(
            success=True,
            message=(
                f"**{winner_name}** defeated **{loser_name}** in PvP! "
                f"Gained **{reward}** stars from the kill."
            ),
            winner_id=winner_id,
            loser_id=loser_id,
            stars_transferred=reward,
        )

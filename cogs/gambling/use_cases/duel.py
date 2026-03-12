"""PvP turn-based duel use case."""

import random
from typing import Optional

from cogs.combat.constants import (
    BASE_HP,
    BASE_STAMINA,
    COMBAT_ITEMS,
    DAMAGE_FLOOR,
    STAMINA_PER_ATTACK,
    STAMINA_PER_DEFEND,
    STAMINA_RECOVERY,
)
from cogs.combat.dto import BattleTurn
from cogs.combat.use_case.health import HealthUseCases
from cogs.gambling.dto import DuelResult, DuelState
from .base import BaseGamblingUseCase


class DuelUseCase(BaseGamblingUseCase):
    """Handles PvP turn-based duel logic."""

    def __init__(self, repository=None):
        super().__init__(repository)
        self._health_uc = HealthUseCases(self.repo)

    # ── Initialization ─────────────────────────────────────

    def validate_and_create_state(
        self,
        p1_id: int,
        p1_name: str,
        p2_id: int,
        p2_name: str,
        amount: int,
    ) -> tuple[Optional[DuelState], str]:
        """Validate both players and create a DuelState.

        Returns (DuelState, "") on success, or (None, error_message) on failure.
        """
        # Check wallets
        p1_stars = self.repo.get_user_stars(p1_id, p1_name)
        p2_stars = self.repo.get_user_stars(p2_id, p2_name)

        if p1_stars < amount:
            return None, f"You only have **{p1_stars}** stars in your wallet!"
        if p2_stars < amount:
            return None, f"Your opponent only has **{p2_stars}** stars in their wallet!"

        # Load combat stats for both
        p1_stats = self.repo.get_combat_stats(p1_id)
        p2_stats = self.repo.get_combat_stats(p2_id)

        p1_hp = p1_stats["current_hp"] or BASE_HP
        p1_max_hp = p1_stats["max_hp"] or BASE_HP
        p1_stamina = p1_stats["current_stamina"] or BASE_STAMINA
        p1_max_stamina = p1_stats["max_stamina"] or BASE_STAMINA

        p2_hp = p2_stats["current_hp"] or BASE_HP
        p2_max_hp = p2_stats["max_hp"] or BASE_HP
        p2_stamina = p2_stats["current_stamina"] or BASE_STAMINA
        p2_max_stamina = p2_stats["max_stamina"] or BASE_STAMINA

        if p1_hp <= 0:
            return None, "You're out of HP! Eat some food with `!eat` to recover."
        if p2_hp <= 0:
            return None, "Your opponent is out of HP and can't fight!"
        if p1_stamina < STAMINA_PER_ATTACK:
            return None, f"You need at least **{STAMINA_PER_ATTACK} stamina** to duel!"
        if p2_stamina < STAMINA_PER_ATTACK:
            return None, f"Your opponent needs at least **{STAMINA_PER_ATTACK} stamina** to duel!"

        # Calculate attack/defense from equipment
        p1_atk, p1_def = self._calc_combat_stats(p1_stats)
        p2_atk, p2_def = self._calc_combat_stats(p2_stats)

        # Lock wager from both wallets
        lock_result = self.repo.lock_duel_bet(
            p1_id, p1_name, p2_id, p2_name, amount
        )
        if lock_result is None:
            return None, "One of you can't afford the wager!"

        state = DuelState(
            p1_id=p1_id,
            p1_name=p1_name,
            p2_id=p2_id,
            p2_name=p2_name,
            wager=amount,
            p1_hp=p1_hp,
            p1_max_hp=p1_max_hp,
            p1_stamina=p1_stamina,
            p1_max_stamina=p1_max_stamina,
            p1_attack=p1_atk,
            p1_defense=p1_def,
            p2_hp=p2_hp,
            p2_max_hp=p2_max_hp,
            p2_stamina=p2_stamina,
            p2_max_stamina=p2_max_stamina,
            p2_attack=p2_atk,
            p2_defense=p2_def,
            active_player=p1_id,
        )
        return state, ""

    def _calc_combat_stats(self, stats: dict) -> tuple[int, int]:
        """Calculate attack and defense from equipment."""
        atk = 5  # base attack
        defense = 2  # base defense
        for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
            key = stats.get(slot)
            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                atk += item.attack
                defense += item.defense
        return atk, defense

    # ── Helpers to get attacker/defender stats ──────────────

    def _get_attacker_stats(self, state: DuelState):
        """Returns (atk, stam, max_stam, target_hp, target_defending)."""
        if state.active_player == state.p1_id:
            return (state.p1_attack, state.p1_stamina, state.p1_max_stamina,
                    state.p2_hp, state.p2_defending)
        return (state.p2_attack, state.p2_stamina, state.p2_max_stamina,
                state.p1_hp, state.p1_defending)

    def _get_defender_defense(self, state: DuelState) -> int:
        if state.active_player == state.p1_id:
            return state.p2_defense
        return state.p1_defense

    # ── Turn actions ───────────────────────────────────────

    def execute_attack(self, state: DuelState) -> BattleTurn:
        """Active player attacks the opponent."""
        state.turn += 1
        is_p1 = state.active_player == state.p1_id

        if is_p1:
            atk, stam, max_stam = state.p1_attack, state.p1_stamina, state.p1_max_stamina
            target_def = state.p2_defense
            target_defending = state.p2_defending
            attacker_name = state.p1_name
            defender_name = state.p2_name
        else:
            atk, stam, max_stam = state.p2_attack, state.p2_stamina, state.p2_max_stamina
            target_def = state.p1_defense
            target_defending = state.p1_defending
            attacker_name = state.p2_name
            defender_name = state.p1_name

        # Damage formula (same as PvE)
        stam_ratio = max(DAMAGE_FLOOR, stam / max_stam) if max_stam > 0 else DAMAGE_FLOOR
        base_dmg = max(1, atk - target_def // 2)
        damage = max(1, int(base_dmg * stam_ratio * random.uniform(0.85, 1.15)))

        # Extra reduction if defender is defending
        if target_defending:
            damage = max(1, damage - target_def)

        # Consume stamina
        if is_p1:
            state.p1_stamina = max(0, state.p1_stamina - STAMINA_PER_ATTACK)
            state.p2_hp = max(0, state.p2_hp - damage)
            state.p2_defending = False  # clear defend flag after being attacked
            actor_hp = state.p1_hp
            target_hp = state.p2_hp
            actor_stamina = state.p1_stamina
        else:
            state.p2_stamina = max(0, state.p2_stamina - STAMINA_PER_ATTACK)
            state.p1_hp = max(0, state.p1_hp - damage)
            state.p1_defending = False
            actor_hp = state.p2_hp
            target_hp = state.p1_hp
            actor_stamina = state.p2_stamina

        turn = BattleTurn(
            turn_number=state.turn,
            actor=attacker_name,
            action="attack",
            damage_dealt=damage,
            actor_hp=actor_hp,
            target_hp=target_hp,
            actor_stamina=actor_stamina,
            message=f"⚔️ **{attacker_name}** attacks **{defender_name}** for **{damage}** damage!",
        )
        state.turns.append(turn)

        # Check for KO
        if target_hp <= 0:
            state.finished = True
            state.winner_id = state.active_player

        # Switch turn
        self._switch_turn(state)
        return turn

    def execute_defend(self, state: DuelState) -> BattleTurn:
        """Active player raises their guard."""
        state.turn += 1
        is_p1 = state.active_player == state.p1_id

        if is_p1:
            state.p1_defending = True
            state.p1_stamina = max(0, state.p1_stamina - STAMINA_PER_DEFEND)
            player_name = state.p1_name
            actor_hp = state.p1_hp
            actor_stamina = state.p1_stamina
            target_hp = state.p2_hp
        else:
            state.p2_defending = True
            state.p2_stamina = max(0, state.p2_stamina - STAMINA_PER_DEFEND)
            player_name = state.p2_name
            actor_hp = state.p2_hp
            actor_stamina = state.p2_stamina
            target_hp = state.p1_hp

        turn = BattleTurn(
            turn_number=state.turn,
            actor=player_name,
            action="defend",
            actor_hp=actor_hp,
            target_hp=target_hp,
            actor_stamina=actor_stamina,
            message=f"🛡️ **{player_name}** raises their guard!",
        )
        state.turns.append(turn)
        self._switch_turn(state)
        return turn

    def execute_consume(
        self, state: DuelState, user_id: int, item_key: str, consume_type: str
    ) -> Optional[BattleTurn]:
        """Consume an HP or stamina item mid-duel. Returns None on failure."""
        is_p1 = user_id == state.p1_id

        if consume_type == "hp":
            heal = self._health_uc.get_hp_value(item_key)
            if not heal:
                return None
            current_hp = state.p1_hp if is_p1 else state.p2_hp
            max_hp = state.p1_max_hp if is_p1 else state.p2_max_hp
            if current_hp >= max_hp:
                return None
        else:
            recovery = STAMINA_RECOVERY.get(item_key)
            if not recovery:
                return None
            current_stam = state.p1_stamina if is_p1 else state.p2_stamina
            max_stam = state.p1_max_stamina if is_p1 else state.p2_max_stamina
            if current_stam >= max_stam:
                return None

        # Remove item from inventory
        if not self._health_uc._find_and_remove(user_id, item_key):
            return None

        state.turn += 1
        display = item_key.replace("_", " ").title()
        player_name = state.p1_name if is_p1 else state.p2_name

        if consume_type == "hp":
            if is_p1:
                old = state.p1_hp
                state.p1_hp = min(state.p1_max_hp, old + heal)
                actual = state.p1_hp - old
            else:
                old = state.p2_hp
                state.p2_hp = min(state.p2_max_hp, old + heal)
                actual = state.p2_hp - old
            msg = f"🍖 **{player_name}** consumed **{display}** and restored **{actual} HP**!"
        else:
            if is_p1:
                old = state.p1_stamina
                state.p1_stamina = min(state.p1_max_stamina, old + recovery)
                actual = state.p1_stamina - old
            else:
                old = state.p2_stamina
                state.p2_stamina = min(state.p2_max_stamina, old + recovery)
                actual = state.p2_stamina - old
            msg = f"⚡ **{player_name}** consumed **{display}** and restored **{actual} stamina**!"

        turn = BattleTurn(
            turn_number=state.turn,
            actor=player_name,
            action="consume",
            actor_hp=state.p1_hp if is_p1 else state.p2_hp,
            target_hp=state.p2_hp if is_p1 else state.p1_hp,
            actor_stamina=state.p1_stamina if is_p1 else state.p2_stamina,
            message=msg,
        )
        state.turns.append(turn)
        self._switch_turn(state)
        return turn

    def _switch_turn(self, state: DuelState) -> None:
        """Switch active player."""
        if not state.finished:
            if state.active_player == state.p1_id:
                state.active_player = state.p2_id
            else:
                state.active_player = state.p1_id

    # ── Resolution ─────────────────────────────────────────

    def resolve_duel(self, state: DuelState) -> DuelResult:
        """Pay out winner and save post-fight stats."""
        winner_id = state.winner_id
        loser_id = state.p2_id if winner_id == state.p1_id else state.p1_id
        winner_name = state.p1_name if winner_id == state.p1_id else state.p2_name
        loser_name = state.p1_name if loser_id == state.p1_id else state.p2_name

        pot = state.wager * 2
        payout = self.repo.payout_duel_winner(
            state.p1_id, state.p1_name,
            state.p2_id, state.p2_name,
            winner_id, pot,
        )

        # Save post-fight HP/stamina for both players
        self.repo.update_hp(state.p1_id, state.p1_hp)
        self.repo.update_stamina(state.p1_id, state.p1_stamina)
        self.repo.update_hp(state.p2_id, state.p2_hp)
        self.repo.update_stamina(state.p2_id, state.p2_stamina)

        # Achievement tracking
        unlocked: list[str] = []
        duel_wins = self.repo.increment_achievement_progress(winner_id, "duel_wins", 1)
        if duel_wins >= 1 and self.repo.unlock_achievement(winner_id, "duel_first_blood"):
            unlocked.append("duel_first_blood")
        if duel_wins >= 50 and self.repo.unlock_achievement(winner_id, "duel_warlord"):
            unlocked.append("duel_warlord")

        winner_bal = 0
        loser_bal = 0
        if payout:
            if winner_id == state.p1_id:
                winner_bal = payout["challenger_wallet"]
                loser_bal = payout["opponent_wallet"]
            else:
                winner_bal = payout["opponent_wallet"]
                loser_bal = payout["challenger_wallet"]

        return DuelResult(
            success=True,
            message="DUEL_COMPLETE",
            winner_id=winner_id,
            loser_id=loser_id,
            amount=state.wager,
            winner_new_balance=winner_bal,
            loser_new_balance=loser_bal,
            unlocked_achievement_keys=unlocked,
        )

    def resolve_timeout(self, state: DuelState) -> DuelResult:
        """Idle player (active_player) forfeits."""
        state.finished = True
        # The idle player loses
        loser_id = state.active_player
        winner_id = state.p2_id if loser_id == state.p1_id else state.p1_id
        state.winner_id = winner_id
        return self.resolve_duel(state)

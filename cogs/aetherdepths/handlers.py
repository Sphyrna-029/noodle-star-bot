"""Aetherdepths dungeon cog — commands, views, background tasks."""

import asyncio
import random
import traceback
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from cogs.aetherdepths.constants import (
    AETHER_DAILY_MODIFIERS,
    AETHER_DEATH_PENALTIES,
    AETHER_LEVELS,
    AETHER_UNLOCK,
    BLAZE_GOBLIN_CHANCE,
    BLAZE_GOBLIN_COOLDOWN,
    BLAZE_GOBLIN_INTERVAL,
    BLAZE_GOBLIN_TIMEOUT,
    DAILY_MODIFIER_CHANCE,
    HAZARD_BASE_CHANCE,
)
from cogs.locations.use_case.locations import LocationUseCases
from cogs.aetherdepths.dto import AetherState
from cogs.aetherdepths.use_case.aetherdepths import AetherdepthsUseCases
from cogs.aetherdepths.use_case.blaze_goblin import BlazeGoblinUseCases
from cogs.aetherdepths.use_case.pvp import PvPUseCases
from cogs.combat.constants import (
    COMBAT_ITEMS, STAMINA_PER_CONSUME, STAMINA_RECOVERY,
)
from cogs.combat.dto import BattleState, BattleTurn
from cogs.combat.use_case.combat import CombatUseCases
from cogs.combat.use_case.health import HealthUseCases
from cogs.locations.check import require_location
from cogs.shop.resources import get_resource
from database.repository import UserRepository

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_active_aether_battles: set[int] = set()
# user_id -> AetherState for hazard tracking between fights
_player_states: dict[int, AetherState] = {}
# user_id -> last goblin encounter time
_last_goblin: dict[int, datetime] = {}


def is_in_aether_battle(user_id: int) -> bool:
    return user_id in _active_aether_battles


def return_stash_on_leave(user_id: int) -> str:
    """Return stashed items when player leaves Aetherdepths. Called by travel."""
    _player_states.pop(user_id, None)
    repo = UserRepository()
    returned = repo.return_stashed_items(user_id)
    if returned > 0:
        return f"**{returned}** stashed item(s) returned to your inventory."
    return ""


# ---------------------------------------------------------------------------
# Progress bar helper
# ---------------------------------------------------------------------------

def _progress_bar(pct: float, length: int = 10) -> str:
    filled = int(pct * length)
    return "█" * filled + "░" * (length - filled)


# ---------------------------------------------------------------------------
# Death confirm view (high-penalty levels)
# ---------------------------------------------------------------------------

class _AetherDeathConfirmView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=30)
        self.author_id = author_id
        self.confirmed = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Not your prompt!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes, fight!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="⚔️ Descending deeper...", view=self)
        self.stop()

    @discord.ui.button(label="No, retreat", style=discord.ButtonStyle.secondary)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🏃 Wisely retreated.", view=self)
        self.stop()

    async def on_timeout(self) -> None:
        self.confirmed = False
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⏰ Timed out — retreated safely.", view=self)
            except Exception:
                pass
        self.stop()


# ---------------------------------------------------------------------------
# Aether Battle View — interactive fight UI
# ---------------------------------------------------------------------------

class _AetherHPSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="🍖 Consume HP item...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, AetherBattleView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your fight!", ephemeral=True)
            return
        view._consume_selected_item = self.values[0]
        view._consume_selected_type = "hp"
        await view._do_consume(interaction)


class _AetherStaminaSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="⚡ Consume stamina item...", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, AetherBattleView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your fight!", ephemeral=True)
            return
        view._consume_selected_item = self.values[0]
        view._consume_selected_type = "stamina"
        await view._do_consume(interaction)


class AetherBattleView(discord.ui.View):
    """Interactive Aetherdepths combat view."""

    def __init__(
        self, battle: BattleState, combat_uc: CombatUseCases,
        aether_uc: AetherdepthsUseCases, author_id: int, username: str,
        is_elite: bool, modifier: dict | None = None,
    ):
        super().__init__(timeout=900)
        self.battle = battle
        self.combat_uc = combat_uc
        self.aether_uc = aether_uc
        self.author_id = author_id
        self.username = username
        self.is_elite = is_elite
        self.modifier = modifier
        self.message = None
        self._finish_lock = asyncio.Lock()
        _active_aether_battles.add(author_id)
        self._consume_selected_item: str | None = None
        self._consume_selected_type: str | None = None
        self._health_uc = HealthUseCases(self.combat_uc.repo)
        self._rebuild_view()

    def _disable_buttons(self) -> None:
        for item in self.children:
            item.disabled = True

    def _finish_battle(self) -> None:
        _active_aether_battles.discard(self.author_id)
        self._disable_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn't your fight!", ephemeral=True)
            return False
        return True

    def _create_embed(self) -> discord.Embed:
        b = self.battle
        if b.finished:
            color = discord.Color.green() if b.player_won else discord.Color.red()
        else:
            color = discord.Color.dark_purple()

        elite_tag = "🔥 " if self.is_elite else ""
        title = f"🕳️ Aetherdepths — {elite_tag}{b.mob_emoji} {b.mob_name} (L{b.dungeon_level})"
        embed = discord.Embed(title=title, color=color)

        # Player stats
        hp_pct = b.player_hp / b.player_max_hp if b.player_max_hp else 0
        stam_pct = b.player_stamina / b.player_max_stamina if b.player_max_stamina else 0
        embed.add_field(
            name="👤 You",
            value=(
                f"❤️ {b.player_hp}/{b.player_max_hp} {_progress_bar(hp_pct)}\n"
                f"⚡ {b.player_stamina}/{b.player_max_stamina} {_progress_bar(stam_pct)}\n"
                f"⚔️ ATK: {b.player_attack}  🛡️ DEF: {b.player_defense}"
            ),
            inline=True,
        )

        # Mob stats
        mob_hp_pct = b.mob_hp / b.mob_max_hp if b.mob_max_hp else 0
        mob_stam_pct = b.mob_stamina / b.mob_max_stamina if b.mob_max_stamina else 0
        embed.add_field(
            name=f"{b.mob_emoji} {b.mob_name}",
            value=(
                f"❤️ {b.mob_hp}/{b.mob_max_hp} {_progress_bar(mob_hp_pct)}\n"
                f"⚡ {b.mob_stamina}/{b.mob_max_stamina} {_progress_bar(mob_stam_pct)}\n"
                f"⚔️ ATK: {b.mob_attack}  🛡️ DEF: {b.mob_defense}"
            ),
            inline=True,
        )

        # Combat log
        recent = b.turns[-4:] if len(b.turns) > 4 else b.turns
        if recent:
            embed.add_field(
                name="📜 Combat Log",
                value="\n".join(t.message for t in recent),
                inline=False,
            )

        if not b.finished:
            embed.set_footer(text="⚔️ Attack | 🛡️ Defend | 🏃 Flee | 🍽️ Consume")

        return embed

    def _build_consume_options(self) -> tuple[list, list]:
        from cogs.combat.constants import CROP_HEAL_VALUES, FISH_HEAL_VALUES
        items = self.combat_uc.repo.get_inventory_items(self.author_id)
        item_counts: dict[str, int] = {}
        for item in items:
            key = item["item_key"]
            item_counts[key] = item_counts.get(key, 0) + 1

        hp_options = []
        stam_options = []

        for key, count in sorted(item_counts.items()):
            heal = self._health_uc.get_hp_value(key)
            if heal and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "🍽️"
                stam_bonus = STAMINA_RECOVERY.get(key)
                label = f"{display} (+{heal} HP"
                if stam_bonus:
                    label += f" +{stam_bonus} stam"
                label += f") x{count}"
                hp_options.append(discord.SelectOption(
                    label=label[:100], value=key, emoji=emoji,
                ))

            recovery = STAMINA_RECOVERY.get(key)
            if recovery and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "⚡"
                stam_options.append(discord.SelectOption(
                    label=f"{display} (+{recovery} stam) x{count}",
                    value=key, emoji=emoji,
                ))

        return hp_options[:25], stam_options[:25]

    def _rebuild_view(self):
        self.clear_items()
        self.add_item(self.attack_button)
        self.add_item(self.defend_button)
        self.add_item(self.flee_button)

        hp_opts, stam_opts = self._build_consume_options()
        if hp_opts:
            self.add_item(_AetherHPSelect(hp_opts))
        if stam_opts:
            self.add_item(_AetherStaminaSelect(stam_opts))

    async def _do_consume(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.battle.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                item_key = self._consume_selected_item
                consume_type = self._consume_selected_type

                if consume_type == "hp":
                    heal = self._health_uc.get_hp_value(item_key)
                    if not heal:
                        return
                    if self.battle.player_hp >= self.battle.player_max_hp:
                        embed = self._create_embed()
                        embed.set_footer(text="❌ HP is already full!")
                        await interaction.edit_original_response(embed=embed, view=self)
                        return

                    # Remove item
                    items = self.combat_uc.repo.get_inventory_items(self.author_id)
                    target = next((i for i in items if i["item_key"] == item_key), None)
                    if not target:
                        return
                    self.combat_uc.repo.remove_items_by_ids(self.author_id, [target["id"]])

                    old_hp = self.battle.player_hp
                    self.battle.player_hp = min(self.battle.player_max_hp, old_hp + heal)
                    restored = self.battle.player_hp - old_hp

                    # Also restore stamina if dual-restore
                    stam_bonus = STAMINA_RECOVERY.get(item_key, 0)
                    if stam_bonus:
                        old_stam = self.battle.player_stamina
                        self.battle.player_stamina = min(self.battle.player_max_stamina, old_stam + stam_bonus)

                    # Consuming costs stamina
                    self.battle.player_stamina = max(0, self.battle.player_stamina - STAMINA_PER_CONSUME)

                    self.battle.turn += 1
                    display = item_key.replace("_", " ").title()
                    msg = f"You consume **{display}** (+{restored} HP"
                    if stam_bonus:
                        actual_stam = self.battle.player_stamina - (old_stam - STAMINA_PER_CONSUME)
                        msg += f" +{max(0, stam_bonus)} stam"
                    msg += ")"
                    turn = BattleTurn(
                        turn_number=self.battle.turn, actor="player", action="consume",
                        actor_hp=self.battle.player_hp, target_hp=self.battle.mob_hp,
                        actor_stamina=self.battle.player_stamina, message=msg,
                    )
                    self.battle.turns.append(turn)
                else:
                    recovery = STAMINA_RECOVERY.get(item_key, 0)
                    if not recovery:
                        return
                    if self.battle.player_stamina >= self.battle.player_max_stamina:
                        embed = self._create_embed()
                        embed.set_footer(text="❌ You're already at full stamina!")
                        await interaction.edit_original_response(embed=embed, view=self)
                        return

                    items = self.combat_uc.repo.get_inventory_items(self.author_id)
                    target = next((i for i in items if i["item_key"] == item_key), None)
                    if not target:
                        return
                    self.combat_uc.repo.remove_items_by_ids(self.author_id, [target["id"]])

                    old_stam = self.battle.player_stamina
                    self.battle.player_stamina = min(self.battle.player_max_stamina, old_stam + recovery)
                    # Consuming costs stamina
                    self.battle.player_stamina = max(0, self.battle.player_stamina - STAMINA_PER_CONSUME)
                    restored = self.battle.player_stamina - old_stam

                    self.battle.turn += 1
                    display = item_key.replace("_", " ").title()
                    turn = BattleTurn(
                        turn_number=self.battle.turn, actor="player", action="consume",
                        actor_hp=self.battle.player_hp, target_hp=self.battle.mob_hp,
                        actor_stamina=self.battle.player_stamina,
                        message=f"You consume **{display}** (+{restored} stamina)",
                    )
                    self.battle.turns.append(turn)

                # Mob attacks back
                mob_turn = self.combat_uc.execute_mob_turn(self.battle, player_defended=False)

                if self.battle.finished:
                    self._finish_battle()
                    if self.battle.player_won:
                        result = self.aether_uc.resolve_victory(
                            self.author_id, self.username, self.battle,
                            self.is_elite, self.modifier,
                        )
                        embed = self._create_embed()
                        embed.add_field(name="🏆 Victory!", value=result["message"], inline=False)
                        if result["drops"]:
                            drop_text = ", ".join(f"**{d[1]}**" for d in result["drops"])
                            embed.add_field(name="🎁 Loot", value=drop_text, inline=False)
                        await self._post_victory(interaction, embed, result)
                    else:
                        result = self.aether_uc.resolve_defeat(
                            self.author_id, self.username, self.battle, self.modifier,
                        )
                        embed = self._create_embed()
                        embed.add_field(name="💀 Defeat", value=result["message"], inline=False)
                        await self._post_defeat(interaction, embed)
                    return

                self._rebuild_view()
                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            traceback.print_exc()

    async def _post_victory(self, interaction, embed, result):
        """Handle post-victory: hazard roll."""
        uid = self.author_id

        # Roll hazard
        hazard = self.aether_uc.roll_hazard(
            uid, self.username, self.battle.dungeon_level, self.modifier,
        )
        if hazard.triggered:
            embed.add_field(
                name=f"{hazard.hazard_emoji} {hazard.hazard_name}!",
                value=hazard.description,
                inline=False,
            )
            if hazard.hp_loss > 0:
                state = _player_states.get(uid)
                if state:
                    state.hp_penalty += hazard.hp_loss
            if hazard.max_hp_reduction > 0:
                state = _player_states.get(uid)
                if state:
                    state.fights_with_curse = 3

        await interaction.edit_original_response(embed=embed, view=self)

    async def _post_defeat(self, interaction, embed):
        """Handle post-defeat."""
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.battle.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                self.combat_uc.execute_player_attack(self.battle)
                if not self.battle.finished:
                    self.combat_uc.execute_mob_turn(self.battle, player_defended=False)

                if self.battle.finished:
                    self._finish_battle()
                    if self.battle.player_won:
                        result = self.aether_uc.resolve_victory(
                            self.author_id, self.username, self.battle,
                            self.is_elite, self.modifier,
                        )
                        embed = self._create_embed()
                        embed.add_field(name="🏆 Victory!", value=result["message"], inline=False)
                        if result["drops"]:
                            drop_text = ", ".join(f"**{d[1]}**" for d in result["drops"])
                            embed.add_field(name="🎁 Loot", value=drop_text, inline=False)
                        await self._post_victory(interaction, embed, result)
                    else:
                        result = self.aether_uc.resolve_defeat(
                            self.author_id, self.username, self.battle, self.modifier,
                        )
                        embed = self._create_embed()
                        embed.add_field(name="💀 Defeat", value=result["message"], inline=False)
                        await self._post_defeat(interaction, embed)
                    return

                self._rebuild_view()
                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.battle.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                self.combat_uc.execute_player_defend(self.battle)
                self.combat_uc.execute_mob_turn(self.battle, player_defended=True)

                if self.battle.finished:
                    self._finish_battle()
                    if self.battle.player_won:
                        result = self.aether_uc.resolve_victory(
                            self.author_id, self.username, self.battle,
                            self.is_elite, self.modifier,
                        )
                        embed = self._create_embed()
                        embed.add_field(name="🏆 Victory!", value=result["message"], inline=False)
                        if result["drops"]:
                            drop_text = ", ".join(f"**{d[1]}**" for d in result["drops"])
                            embed.add_field(name="🎁 Loot", value=drop_text, inline=False)
                        await self._post_victory(interaction, embed, result)
                    else:
                        result = self.aether_uc.resolve_defeat(
                            self.author_id, self.username, self.battle, self.modifier,
                        )
                        embed = self._create_embed()
                        embed.add_field(name="💀 Defeat", value=result["message"], inline=False)
                        await self._post_defeat(interaction, embed)
                    return

                self._rebuild_view()
                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Flee", style=discord.ButtonStyle.secondary, emoji="🏃", row=0)
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.battle.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                success, chance = self.combat_uc.attempt_flee(self.battle)
                pct = int(chance * 100)
                if success:
                    self.battle.finished = True
                    self._finish_battle()
                    self.combat_uc.repo.update_hp(self.author_id, self.battle.player_hp)
                    self.combat_uc.repo.update_stamina(self.author_id, self.battle.player_stamina)
                    embed = self._create_embed()
                    embed.add_field(
                        name="🏃 Fled!",
                        value=f"You escaped! (Chance: {pct}%)",
                        inline=False,
                    )
                    await interaction.edit_original_response(embed=embed, view=self)
                else:
                    self.battle.turn += 1
                    turn = BattleTurn(
                        turn_number=self.battle.turn, actor="player", action="flee",
                        actor_hp=self.battle.player_hp, target_hp=self.battle.mob_hp,
                        actor_stamina=self.battle.player_stamina,
                        message=f"🏃 Flee failed! ({pct}% chance)",
                    )
                    self.battle.turns.append(turn)
                    self.combat_uc.execute_mob_turn(self.battle, player_defended=False)

                    if self.battle.finished:
                        self._finish_battle()
                        result = self.aether_uc.resolve_defeat(
                            self.author_id, self.username, self.battle, self.modifier,
                        )
                        embed = self._create_embed()
                        embed.add_field(name="💀 Defeat", value=result["message"], inline=False)
                        await self._post_defeat(interaction, embed)
                        return

                    self._rebuild_view()
                    embed = self._create_embed()
                    await interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            traceback.print_exc()

    async def on_timeout(self) -> None:
        # Save player state before cleaning up
        self.combat_uc.repo.update_hp(self.author_id, self.battle.player_hp)
        self.combat_uc.repo.update_stamina(self.author_id, self.battle.player_stamina)
        self._finish_battle()
        if self.message:
            try:
                await self.message.edit(content="⏰ Battle timed out!", view=self)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# PvP Battle View
# ---------------------------------------------------------------------------

class PvPBattleView(discord.ui.View):
    """Two-player PvP battle view for Aetherdepths."""

    def __init__(
        self, state, pvp_uc: PvPUseCases,
        attacker_id: int, defender_id: int,
    ):
        super().__init__(timeout=600)  # 10 minute time limit
        self.state = state
        self.pvp_uc = pvp_uc
        self.attacker_id = attacker_id
        self.defender_id = defender_id
        self.message = None
        self._finish_lock = asyncio.Lock()
        _active_aether_battles.add(attacker_id)
        _active_aether_battles.add(defender_id)

    def _disable_buttons(self):
        for item in self.children:
            item.disabled = True

    def _finish_battle(self):
        _active_aether_battles.discard(self.attacker_id)
        _active_aether_battles.discard(self.defender_id)
        self._disable_buttons()

    def _active_player_id(self) -> int:
        return self.attacker_id if self.state.active_player == 0 else self.defender_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        active_id = self._active_player_id()
        if interaction.user.id != active_id:
            if interaction.user.id in (self.attacker_id, self.defender_id):
                await interaction.response.send_message("It's not your turn!", ephemeral=True)
            else:
                await interaction.response.send_message("This isn't your fight!", ephemeral=True)
            return False
        return True

    def _create_embed(self) -> discord.Embed:
        s = self.state
        if s.finished:
            color = discord.Color.gold()
        else:
            color = discord.Color.dark_red()

        embed = discord.Embed(
            title=f"⚔️ PvP — {s.attacker_name} vs {s.defender_name} (L{s.aether_level})",
            color=color,
        )

        # Attacker stats
        atk_hp_pct = s.atk_hp / s.atk_max_hp if s.atk_max_hp else 0
        atk_stam_pct = s.atk_stamina / s.atk_max_stamina if s.atk_max_stamina else 0
        embed.add_field(
            name=f"⚔️ {s.attacker_name}",
            value=(
                f"❤️ {s.atk_hp}/{s.atk_max_hp} {_progress_bar(atk_hp_pct)}\n"
                f"⚡ {s.atk_stamina}/{s.atk_max_stamina} {_progress_bar(atk_stam_pct)}\n"
                f"ATK: {s.atk_attack}  DEF: {s.atk_defense}"
            ),
            inline=True,
        )

        # Defender stats
        def_hp_pct = s.def_hp / s.def_max_hp if s.def_max_hp else 0
        def_stam_pct = s.def_stamina / s.def_max_stamina if s.def_max_stamina else 0
        embed.add_field(
            name=f"🛡️ {s.defender_name}",
            value=(
                f"❤️ {s.def_hp}/{s.def_max_hp} {_progress_bar(def_hp_pct)}\n"
                f"⚡ {s.def_stamina}/{s.def_max_stamina} {_progress_bar(def_stam_pct)}\n"
                f"ATK: {s.def_attack}  DEF: {s.def_defense}"
            ),
            inline=True,
        )

        recent = s.turns[-4:] if len(s.turns) > 4 else s.turns
        if recent:
            embed.add_field(
                name="📜 Combat Log",
                value="\n".join(t.message for t in recent),
                inline=False,
            )

        if not s.finished:
            active_name = s.attacker_name if s.active_player == 0 else s.defender_name
            embed.set_footer(text=f"⏳ {active_name}'s turn")

        return embed

    async def _check_finish(self, interaction):
        if self.state.finished:
            self._finish_battle()
            winner_name = self.state.attacker_name if self.state.winner_id == self.attacker_id else self.state.defender_name
            loser_name = self.state.defender_name if self.state.winner_id == self.attacker_id else self.state.attacker_name
            result = self.pvp_uc.resolve_pvp(self.state, winner_name, loser_name)
            embed = self._create_embed()
            embed.add_field(name="🏆 PvP Result", value=result.message, inline=False)

            await interaction.edit_original_response(embed=embed, view=self)
            return True
        return False

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.state.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                self.pvp_uc.execute_attack(self.state)
                if await self._check_finish(interaction):
                    return

                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.state.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                self.pvp_uc.execute_defend(self.state)
                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            traceback.print_exc()

    async def on_timeout(self) -> None:
        """Time limit reached — attacker wins automatically."""
        async with self._finish_lock:
            if self.state.finished:
                return

            # Force attacker win
            self.state.finished = True
            self.state.winner_id = self.attacker_id

            self._finish_battle()

            winner_name = self.state.attacker_name
            loser_name = self.state.defender_name
            result = self.pvp_uc.resolve_pvp(self.state, winner_name, loser_name)

            embed = self._create_embed()
            embed.add_field(
                name="⏰ Time Limit Reached",
                value=f"**{winner_name}** wins by timeout!\n{result.message}",
                inline=False,
            )

            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Blaze Goblin View
# ---------------------------------------------------------------------------

class BlazeGoblinView(discord.ui.View):
    """Interactive Blaze Goblin trader menu."""

    def __init__(self, user_id: int, username: str, level: int, goblin_uc: BlazeGoblinUseCases):
        super().__init__(timeout=BLAZE_GOBLIN_TIMEOUT)
        self.user_id = user_id
        self.username = username
        self.level = level
        self.goblin_uc = goblin_uc
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This goblin isn't talking to you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Deposit 1000", style=discord.ButtonStyle.success, emoji="🏦", row=0)
    async def deposit_1k(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            success, msg = self.goblin_uc.deposit_stars(self.user_id, self.username, 1000)
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Deposit 5000", style=discord.ButtonStyle.success, emoji="🏦", row=0)
    async def deposit_5k(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            success, msg = self.goblin_uc.deposit_stars(self.user_id, self.username, 5000)
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Deposit All", style=discord.ButtonStyle.success, emoji="🏦", row=0)
    async def deposit_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            repo = self.goblin_uc.repo
            current = repo.get_user_stars(self.user_id, self.username)
            if current <= 0:
                await interaction.response.send_message("No stars to deposit!", ephemeral=True)
                return
            success, msg = self.goblin_uc.deposit_stars(self.user_id, self.username, current)
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Buy Menu", style=discord.ButtonStyle.primary, emoji="🛒", row=1)
    async def buy_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            stock = self.goblin_uc.get_stock(self.level)
            lines = [f"**{name}** — {price} ⭐" for _, name, price in stock]
            await interaction.response.send_message(
                "🧌 **Blaze Goblin's Wares:**\n" + "\n".join(lines) +
                "\n\nType `!gbuy <item>` to purchase.",
                ephemeral=True,
            )
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Stash Item", style=discord.ButtonStyle.primary, emoji="📦", row=1)
    async def stash_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            count = self.goblin_uc.repo.get_stash_count(self.user_id)
            await interaction.response.send_message(
                f"📦 **Stash** ({count}/5 slots used)\n"
                "Stashed items survive death!\n\n"
                "Type `!gstash <item_name>` to stash an inventory item.\n"
                "Type `!astash` to view your stash.",
                ephemeral=True,
            )
        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.secondary, emoji="❌", row=2)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(
                content="🧌 The Blaze Goblin vanishes into the shadows...",
                view=self,
            )
            self.stop()
        except Exception:
            traceback.print_exc()

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    content="🧌 The Blaze Goblin got bored and vanished...",
                    view=self,
                )
            except Exception:
                pass
        self.stop()


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class AetherdepthsCog(commands.Cog, name="Aetherdepths"):
    """The Aetherdepths — a 5-level dungeon with PvP, hazards, and a goblin trader."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = UserRepository()
        self.aether_uc = AetherdepthsUseCases(self.repo)
        self.pvp_uc = PvPUseCases(self.repo)
        self.goblin_uc = BlazeGoblinUseCases(self.repo)
        self.combat_uc = CombatUseCases(self.repo)
        self.locations = LocationUseCases()
        # user_id -> channel_id for goblin encounters
        self._last_channel: dict[int, int] = {}

    async def cog_load(self) -> None:
        self.blaze_goblin_check.start()
        self.daily_modifier_check.start()

    async def cog_unload(self) -> None:
        self.blaze_goblin_check.cancel()
        self.daily_modifier_check.cancel()

    # ── !aether — status / level switch ─────────────────────

    @commands.command(name="aether", aliases=["aetherdepths", "ad"])
    async def aether_status(self, ctx: commands.Context, level: int = None):
        """View Aetherdepths status or switch/unlock levels. Usage: !aether [level]"""
        uid = ctx.author.id
        aether = self.repo.get_aether_stats(uid)
        combat = self.repo.get_combat_stats(uid)

        # Level switch mode
        if level is not None:
            if not await require_location(ctx, "aetherdepths"):
                return
            from cogs.combat.handlers import is_in_battle
            if is_in_battle(uid) or is_in_aether_battle(uid):
                await ctx.send("❌ You're currently in combat!")
                return
            success, msg = self.aether_uc.enter_dungeon(uid, ctx.author.name, level)
            if success:
                _player_states.pop(uid, None)  # Clear hazard state on level switch
            await ctx.send(msg)
            return

        # Status mode
        embed = discord.Embed(
            title="🕳️ The Aetherdepths",
            color=discord.Color.dark_purple(),
        )

        if combat["combat_level"] < 5:
            embed.description = (
                f"You need **Combat Level 5** to enter The Aetherdepths.\n"
                f"Current: Combat Level **{combat['combat_level']}**.\n"
                "Complete the Noodle Colosseum first!"
            )
            await ctx.send(embed=embed)
            return

        unlocked = aether["aether_level"]
        active = aether["active_aether_level"] or 1

        level_lines = []
        for lvl, info in AETHER_LEVELS.items():
            if lvl <= unlocked:
                marker = "⚔️ Active" if lvl == active else "✅"
                level_lines.append(f"{marker} **L{lvl}** {info['emoji']} {info['name']}")
            else:
                cost = AETHER_UNLOCK[lvl]["cost"]
                level_lines.append(f"🔒 **L{lvl}** {info['emoji']} {info['name']} — {cost:,} ⭐")

        embed.add_field(name="Dungeon Levels", value="\n".join(level_lines), inline=False)

        modifier = self.aether_uc.get_active_modifier()
        if modifier:
            embed.add_field(
                name=f"{modifier['emoji']} Daily Modifier: {modifier['name']}",
                value=modifier["description"],
                inline=False,
            )

        embed.set_footer(text="!aether <level> to switch/unlock | !afight to fight")
        await ctx.send(embed=embed)

    # ── !afight — fight a mob ────────────────────────────────

    @commands.command(name="afight", aliases=["af"])
    async def aether_fight(self, ctx: commands.Context):
        """Fight a mob in The Aetherdepths."""
        if not await require_location(ctx, "aetherdepths"):
            return

        uid = ctx.author.id

        from cogs.combat.handlers import is_in_battle
        if is_in_battle(uid) or is_in_aether_battle(uid):
            await ctx.send("❌ You're already in combat!")
            return

        aether = self.repo.get_aether_stats(uid)
        level = aether["active_aether_level"] or 0
        if level < 1:
            await ctx.send("❌ You haven't unlocked any Aetherdepths level! Use `!aether 1` to unlock.")
            return

        self._last_channel[uid] = ctx.channel.id

        # Death confirm for L3+
        penalty = AETHER_DEATH_PENALTIES.get(level, AETHER_DEATH_PENALTIES[1])
        if level >= 3:
            view = _AetherDeathConfirmView(uid)
            msg = await ctx.send(
                f"⚠️ **Level {level}** death penalty: {penalty['description']}\nProceed?",
                view=view,
            )
            view.message = msg
            await view.wait()
            if not view.confirmed:
                return

        modifier = self.aether_uc.get_active_modifier()
        battle, error, is_elite = self.aether_uc.start_fight(uid, ctx.author.name, level, modifier)

        if not battle:
            await ctx.send(f"❌ {error}")
            return

        # Apply hazard HP penalty from previous fight
        state = _player_states.get(uid)
        if state and state.hp_penalty > 0:
            battle.player_hp = max(1, battle.player_hp - state.hp_penalty)
            state.hp_penalty = 0
        else:
            _player_states[uid] = AetherState(user_id=uid, level=level)

        view = AetherBattleView(
            battle, self.combat_uc, self.aether_uc,
            uid, ctx.author.name, is_elite, modifier,
        )
        embed = view._create_embed()
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    # ── !pvp — attack another player ─────────────────────────

    @commands.command(name="pvp")
    async def aether_pvp(self, ctx: commands.Context, target: discord.Member = None):
        """Attack another player in The Aetherdepths (L2+ only)."""
        if not await require_location(ctx, "aetherdepths"):
            return
        if not target:
            await ctx.send("Usage: `!pvp @player`")
            return

        uid = ctx.author.id
        tid = target.id

        from cogs.combat.handlers import is_in_battle
        if is_in_battle(uid) or is_in_aether_battle(uid):
            await ctx.send("❌ You're in combat!")
            return
        if is_in_battle(tid) or is_in_aether_battle(tid):
            await ctx.send("❌ Your target is in combat!")
            return

        # Check target is also at aetherdepths
        target_loc = self.locations.get_location(tid)
        if target_loc != "aetherdepths":
            await ctx.send("❌ That player is not in The Aetherdepths!")
            return

        attacker_aether = self.repo.get_aether_stats(uid)
        defender_aether = self.repo.get_aether_stats(tid)
        attacker_level = attacker_aether["active_aether_level"] or 1
        defender_level = defender_aether["active_aether_level"] or 1

        modifier = self.aether_uc.get_active_modifier()
        valid, err = self.pvp_uc.validate_pvp(uid, tid, attacker_level, defender_level, modifier)
        if not valid:
            await ctx.send(f"❌ {err}")
            return

        state, err = self.pvp_uc.init_pvp(uid, ctx.author.name, tid, target.display_name, attacker_level)
        if not state:
            await ctx.send(f"❌ {err}")
            return

        view = PvPBattleView(state, self.pvp_uc, uid, tid)
        embed = view._create_embed()
        msg = await ctx.send(
            f"⚔️ {ctx.author.mention} attacks {target.mention} in The Aetherdepths!",
            embed=embed, view=view,
        )
        view.message = msg

    # ── !astash — view stash ─────────────────────────────────

    @commands.command(name="astash")
    async def aether_stash(self, ctx: commands.Context):
        """View your Aetherdepths stash."""
        uid = ctx.author.id
        items = self.repo.get_stashed_items(uid)

        if not items:
            await ctx.send("📦 Your Aether stash is empty.")
            return

        lines = []
        for item in items:
            res = get_resource(item["item_key"])
            display = res.display_name if res else item["item_key"].replace("_", " ").title()
            emoji = res.emoji if res else "📦"
            lines.append(f"{emoji} {display}")

        embed = discord.Embed(
            title="📦 Aether Stash",
            description="\n".join(lines),
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text=f"{len(items)}/5 slots used. Items survive death!")
        await ctx.send(embed=embed)

    # ── !gbuy — buy from Blaze Goblin ────────────────────────

    @commands.command(name="gbuy", aliases=["goblinbuy"])
    async def goblin_buy(self, ctx: commands.Context, *, item_name: str = ""):
        """Buy an item from the Blaze Goblin."""
        if not await require_location(ctx, "aetherdepths"):
            return
        uid = ctx.author.id
        if not item_name:
            await ctx.send("Usage: `!gbuy <item name>` — use the Blaze Goblin's Buy Menu to see available items.")
            return

        aether = self.repo.get_aether_stats(uid)
        level = aether["active_aether_level"] or 1
        stock = self.goblin_uc.get_stock(level)

        # Match by display name (case-insensitive) or item key
        match = None
        norm = item_name.strip().lower().replace(" ", "_")
        for item_key, display, price in stock:
            if norm == item_key or norm == display.lower().replace(" ", "_") or norm == display.lower():
                match = (item_key, display, price)
                break

        if not match:
            names = ", ".join(display for _, display, _ in stock)
            await ctx.send(f"Item not found in stock! Available: {names}")
            return

        item_key, display, price = match
        success, msg = self.goblin_uc.buy_item(uid, str(ctx.author), item_key, price)
        prefix = "🧌" if success else "❌"
        await ctx.send(f"{prefix} {ctx.author.mention}, {msg}")

    # ── !gstash — stash an item via Blaze Goblin ─────────────

    @commands.command(name="gstash", aliases=["goblinstash"])
    async def goblin_stash(self, ctx: commands.Context, *, item_name: str = ""):
        """Stash an inventory item (survives death). Requires Blaze Goblin."""
        if not await require_location(ctx, "aetherdepths"):
            return
        uid = ctx.author.id
        if not item_name:
            await ctx.send("Usage: `!gstash <item name>` — stash an item to protect it from death.")
            return

        # Find matching item in user's inventory
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, item_key FROM user_inventory_items WHERE user_id = ? ORDER BY id",
                (uid,),
            )
            rows = cursor.fetchall()

        norm = item_name.strip().lower().replace(" ", "_")
        match_id = None
        for row in rows:
            key = row["item_key"]
            res = get_resource(key)
            display = res.display_name.lower().replace(" ", "_") if res else key
            if norm == key or norm == display or norm == (res.display_name.lower() if res else key):
                match_id = row["id"]
                break

        if match_id is None:
            await ctx.send(f"❌ No item matching **{item_name}** found in your inventory.")
            return

        success, msg = self.goblin_uc.stash_item(uid, match_id)
        prefix = "📦" if success else "❌"
        await ctx.send(f"{prefix} {ctx.author.mention}, {msg}")

    # ── Background tasks ─────────────────────────────────────

    @tasks.loop(minutes=BLAZE_GOBLIN_INTERVAL)
    async def blaze_goblin_check(self):
        """Periodically check for Blaze Goblin encounters for players at Aetherdepths."""
        modifier = self.aether_uc.get_active_modifier()
        goblin_mult = 1.0
        if modifier:
            goblin_mult = modifier.get("goblin_mult", 1.0)

        now = datetime.utcnow()
        # Check all players who recently fought (tracked via _last_channel)
        for uid, channel_id in list(self._last_channel.items()):
            if uid in _active_aether_battles:
                continue

            # Verify still at aetherdepths
            if self.locations.get_location(uid) != "aetherdepths":
                self._last_channel.pop(uid, None)
                continue

            aether = self.repo.get_aether_stats(uid)
            level = aether["active_aether_level"] or 0
            if level < 2:
                continue  # Blaze Goblin only appears on L2-5

            # Cooldown check
            last = _last_goblin.get(uid)
            if last and (now - last).total_seconds() < BLAZE_GOBLIN_COOLDOWN:
                continue

            chance = BLAZE_GOBLIN_CHANCE * goblin_mult
            if random.random() >= chance:
                continue

            _last_goblin[uid] = now

            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue

                user = self.bot.get_user(uid)
                if not user:
                    continue

                view = BlazeGoblinView(uid, user.name, level, self.goblin_uc)
                goblin_msg = await channel.send(
                    f"🧌 {user.mention}, a **Blaze Goblin** appears from the shadows!\n"
                    "Quick — deposit your stars, buy supplies, or stash items before it vanishes!",
                    view=view,
                )
                view.message = goblin_msg
            except Exception as e:
                print(f"Blaze Goblin error for user {uid}: {e}")

    @blaze_goblin_check.before_loop
    async def before_goblin_check(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def daily_modifier_check(self):
        """Check if we need to roll a new daily modifier."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        current = self.repo.get_daily_modifier()

        if current and current.get("active_date") == today:
            return  # Already rolled today

        # Roll for a new modifier
        if random.random() < DAILY_MODIFIER_CHANCE:
            mod = random.choice(AETHER_DAILY_MODIFIERS)
            self.repo.set_daily_modifier(mod["key"], today)
        else:
            self.repo.set_daily_modifier(None, today)

    @daily_modifier_check.before_loop
    async def before_modifier_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AetherdepthsCog(bot))

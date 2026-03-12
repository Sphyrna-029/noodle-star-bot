"""Combat commands cog — fight, consume, equip, craft, gear, hp, stamina."""

import asyncio
import traceback

import discord
from discord.ext import commands

from cogs.combat.constants import (
    COMBAT_ITEMS, COOP_JOIN_TIMEOUT, COOP_MAX_PLAYERS, COOP_ROUND_TIMEOUT,
    CRAFT_RECIPES, CROP_HEAL_VALUES, DEATH_PENALTIES,
    DUNGEON_LEVELS, FISH_HEAL_VALUES, MOBS_BY_LEVEL, STAMINA_RECOVERY,
)
from cogs.shop.resources import get_resource
from cogs.combat.dto import BattleState, BattleTurn, CoopBattleState, CoopPlayer
from cogs.combat.use_case.combat import CombatUseCases
from cogs.combat.use_case.coop import CoopCombatUseCases
from cogs.combat.use_case.crafting import CraftingUseCases
from cogs.combat.use_case.equipment import EquipmentUseCases
from cogs.combat.use_case.health import HealthUseCases, HEALTH_POTION_HP
from cogs.locations.check import require_location


# ---------------------------------------------------------------------------
# Death penalty confirmation view (L3+)
# ---------------------------------------------------------------------------

class _DeathConfirmView(discord.ui.View):
    """Confirmation prompt before fighting in high-penalty dungeons."""

    def __init__(self, author_id: int):
        super().__init__(timeout=30)
        self.author_id = author_id
        self.confirmed = False

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
        await interaction.response.edit_message(content="⚔️ Entering the dungeon...", view=self)
        self.stop()

    @discord.ui.button(label="No, retreat", style=discord.ButtonStyle.secondary)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🏃 Wisely retreated.", view=self)
        self.stop()


# ---------------------------------------------------------------------------
# Battle View — interactive fight UI
# ---------------------------------------------------------------------------

_active_battles: set[int] = set()


def is_in_battle(user_id: int) -> bool:
    """Check if a user is currently in an active battle."""
    return user_id in _active_battles


class _BattleHPSelect(discord.ui.Select):
    """Dropdown for HP restoration items during battle."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="🍖 Consume HP item...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, BattleView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your fight!", ephemeral=True)
            return
        view._consume_selected_item = self.values[0]
        view._consume_selected_type = "hp"
        await view._do_consume(interaction)


class _BattleStaminaSelect(discord.ui.Select):
    """Dropdown for stamina restoration items during battle."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="⚡ Consume stamina item...", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, BattleView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your fight!", ephemeral=True)
            return
        view._consume_selected_item = self.values[0]
        view._consume_selected_type = "stamina"
        await view._do_consume(interaction)


class BattleView(discord.ui.View):
    """Interactive combat view with Attack/Defend/Flee buttons + consume items."""

    def __init__(self, battle: BattleState, combat_uc: CombatUseCases,
                 author_id: int, username: str):
        super().__init__(timeout=180)
        self.battle = battle
        self.combat_uc = combat_uc
        self.author_id = author_id
        self.username = username
        self.message = None
        self._finish_lock = asyncio.Lock()
        _active_battles.add(author_id)
        self._consume_selected_item: str | None = None
        self._consume_selected_type: str | None = None
        self._health_uc = HealthUseCases(self.combat_uc.repo)
        # Build view with action buttons + consume dropdowns
        self._rebuild_view()

    def _disable_buttons(self) -> None:
        for item in self.children:
            item.disabled = True

    def _finish_battle(self) -> None:
        """Clean up when battle ends — remove from active set and disable buttons."""
        _active_battles.discard(self.author_id)
        self._disable_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your fight!", ephemeral=True
            )
            return False
        return True

    def _create_embed(self) -> discord.Embed:
        b = self.battle

        if b.finished:
            color = discord.Color.green() if b.player_won else discord.Color.red()
        else:
            color = discord.Color.orange()

        if b.ambush:
            title = f"⚔️ Ambush! — {b.mob_emoji} {b.mob_name}"
        else:
            title = f"⚔️ Battle — {b.mob_emoji} {b.mob_name} (Lv{b.dungeon_level})"

        embed = discord.Embed(title=title, color=color)

        # Player stats bar
        hp_pct = b.player_hp / b.player_max_hp if b.player_max_hp else 0
        hp_bar = _progress_bar(hp_pct)
        stam_pct = b.player_stamina / b.player_max_stamina if b.player_max_stamina else 0
        stam_bar = _progress_bar(stam_pct)

        embed.add_field(
            name="👤 You",
            value=(
                f"❤️ HP: {b.player_hp}/{b.player_max_hp} {hp_bar}\n"
                f"⚡ Stamina: {b.player_stamina}/{b.player_max_stamina} {stam_bar}\n"
                f"⚔️ ATK: {b.player_attack}  🛡️ DEF: {b.player_defense}"
            ),
            inline=True,
        )

        # Mob stats bar
        mob_hp_pct = b.mob_hp / b.mob_max_hp if b.mob_max_hp else 0
        mob_hp_bar = _progress_bar(mob_hp_pct)
        mob_stam_pct = b.mob_stamina / b.mob_max_stamina if b.mob_max_stamina else 0
        mob_stam_bar = _progress_bar(mob_stam_pct)

        embed.add_field(
            name=f"{b.mob_emoji} {b.mob_name}",
            value=(
                f"❤️ HP: {b.mob_hp}/{b.mob_max_hp} {mob_hp_bar}\n"
                f"⚡ Stamina: {b.mob_stamina}/{b.mob_max_stamina} {mob_stam_bar}\n"
                f"⚔️ ATK: {b.mob_attack}  🛡️ DEF: {b.mob_defense}"
            ),
            inline=True,
        )

        # Last 3 turns as combat log
        recent = b.turns[-4:] if len(b.turns) > 4 else b.turns
        if recent:
            log_lines = [t.message for t in recent]
            embed.add_field(
                name="📜 Combat Log",
                value="\n".join(log_lines),
                inline=False,
            )

        if not b.finished:
            rounds_done = b.turn // 2
            if b.ambush and rounds_done < b.ambush.flee_lockout_turns:
                remaining = b.ambush.flee_lockout_turns - rounds_done
                embed.set_footer(text=f"⚔️ Attack | 🛡️ Defend | 🏃 Flee (locked {remaining} rnd) | 🍽️ Consume (costs turn)")
            else:
                embed.set_footer(text="⚔️ Attack | 🛡️ Defend | 🏃 Flee | 🍽️ Consume (costs turn)")

        return embed

    def _update_flee_button(self) -> None:
        """Enable/disable the Flee button based on lockout."""
        b = self.battle
        rounds_done = b.turn // 2
        if b.ambush and rounds_done < b.ambush.flee_lockout_turns:
            remaining = b.ambush.flee_lockout_turns - rounds_done
            self.flee_button.label = f"Flee ({remaining})"
            self.flee_button.disabled = True
        else:
            self.flee_button.label = "Flee"
            self.flee_button.disabled = False

    def _build_consume_options(self) -> tuple[list, list]:
        """Build HP and stamina dropdown options from current inventory."""
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
                hp_options.append(discord.SelectOption(
                    label=f"{display} (+{heal} HP) x{count}",
                    value=key,
                    emoji=emoji,
                    default=(key == self._consume_selected_item and self._consume_selected_type == "hp"),
                ))

            recovery = STAMINA_RECOVERY.get(key)
            if recovery and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "⚡"
                stam_options.append(discord.SelectOption(
                    label=f"{display} (+{recovery} stam) x{count}",
                    value=key,
                    emoji=emoji,
                    default=(key == self._consume_selected_item and self._consume_selected_type == "stamina"),
                ))

        return hp_options, stam_options

    def _rebuild_view(self):
        """Rebuild all view components — action buttons + consume dropdowns."""
        self.clear_items()
        self.add_item(self.attack_button)
        self.add_item(self.defend_button)
        self.add_item(self.flee_button)

        hp_opts, stam_opts = self._build_consume_options()
        if hp_opts:
            self.add_item(_BattleHPSelect(hp_opts))
        if stam_opts:
            self.add_item(_BattleStaminaSelect(stam_opts))
        if hp_opts or stam_opts:
            self.add_item(self.battle_consume_btn)

        self.add_item(self.request_help_button)
        self._update_flee_button()

    async def _do_consume(self, interaction: discord.Interaction):
        """Consume the selected item during battle — takes a turn, mob attacks back."""
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.battle.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                item_key = self._consume_selected_item
                consume_type = self._consume_selected_type
                display = item_key.replace("_", " ").title()

                if consume_type == "hp":
                    heal = self._health_uc.get_hp_value(item_key)
                    if not heal:
                        return

                    if self.battle.player_hp >= self.battle.player_max_hp:
                        embed = self._create_embed()
                        embed.set_footer(text="❌ You're already at full HP!")
                        await interaction.edit_original_response(embed=embed, view=self)
                        return

                    if not self._health_uc._find_and_remove(self.author_id, item_key):
                        self._rebuild_view()
                        embed = self._create_embed()
                        embed.set_footer(text=f"❌ No {display} in inventory!")
                        await interaction.edit_original_response(embed=embed, view=self)
                        return

                    old_hp = self.battle.player_hp
                    self.battle.player_hp = min(self.battle.player_max_hp, old_hp + heal)
                    actual = self.battle.player_hp - old_hp

                    self.battle.turn += 1
                    turn = BattleTurn(
                        turn_number=self.battle.turn,
                        actor="player",
                        action="consume",
                        actor_hp=self.battle.player_hp,
                        target_hp=self.battle.mob_hp,
                        actor_stamina=self.battle.player_stamina,
                        message=f"🍖 You consumed **{display}** and restored **{actual} HP**!",
                    )
                    self.battle.turns.append(turn)

                else:
                    recovery = STAMINA_RECOVERY.get(item_key)
                    if not recovery:
                        return

                    if self.battle.player_stamina >= self.battle.player_max_stamina:
                        embed = self._create_embed()
                        embed.set_footer(text="❌ You're already at full stamina!")
                        await interaction.edit_original_response(embed=embed, view=self)
                        return

                    if not self._health_uc._find_and_remove(self.author_id, item_key):
                        self._rebuild_view()
                        embed = self._create_embed()
                        embed.set_footer(text=f"❌ No {display} in inventory!")
                        await interaction.edit_original_response(embed=embed, view=self)
                        return

                    old_stam = self.battle.player_stamina
                    self.battle.player_stamina = min(self.battle.player_max_stamina, old_stam + recovery)
                    actual = self.battle.player_stamina - old_stam

                    self.battle.turn += 1
                    turn = BattleTurn(
                        turn_number=self.battle.turn,
                        actor="player",
                        action="consume",
                        actor_hp=self.battle.player_hp,
                        target_hp=self.battle.mob_hp,
                        actor_stamina=self.battle.player_stamina,
                        message=f"⚡ You consumed **{display}** and restored **{actual} stamina**!",
                    )
                    self.battle.turns.append(turn)

                # Update consume button for quick re-use
                res = get_resource(item_key)
                btn_emoji = res.emoji if res else "🍽️"
                self.battle_consume_btn.label = f"Consume {display}"
                self.battle_consume_btn.emoji = btn_emoji
                self.battle_consume_btn.style = discord.ButtonStyle.success
                self.battle_consume_btn.disabled = False

                # Mob gets a free attack
                await self._do_mob_turn(interaction, player_defended=False)

                if not self.battle.finished:
                    self._rebuild_view()
                    embed = self._create_embed()
                    await interaction.edit_original_response(embed=embed, view=self)

        except Exception:
            traceback.print_exc()

    async def _do_mob_turn(self, interaction: discord.Interaction, player_defended: bool):
        """Execute mob's turn and check for defeat."""
        if self.battle.finished:
            return

        mob_turn = self.combat_uc.execute_mob_turn(self.battle, player_defended)

        if self.battle.finished:
            # Player was killed
            result = self.combat_uc.resolve_defeat(
                self.author_id, self.username, self.battle
            )
            self._finish_battle()
            embed = self._create_embed()

            # Add defeat info
            penalty_lines = []
            if result.stars_lost > 0:
                penalty_lines.append(f"💫 Stars lost: **{result.stars_lost}**")
            if result.bank_loss > 0:
                penalty_lines.append(f"🏦 Bank loss: **{result.bank_loss}**")
            if result.items_lost:
                penalty_lines.append(f"📦 Items lost: **{len(result.items_lost)}**")
            if result.equipment_lost:
                penalty_lines.append(f"🔧 Equipment lost: {', '.join(result.equipment_lost)}")

            embed.add_field(
                name="💀 DEFEAT",
                value=result.message + ("\n" + "\n".join(penalty_lines) if penalty_lines else ""),
                inline=False,
            )
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

                # Player attacks
                self.combat_uc.execute_player_attack(self.battle)

                if self.battle.finished and self.battle.player_won:
                    # Victory!
                    result = self.combat_uc.resolve_victory(
                        self.author_id, self.username, self.battle
                    )
                    self._finish_battle()
                    embed = self._create_embed()
                    victory_text = result.message
                    if result.combat_level_up:
                        victory_text += f"\n🎉 **COMBAT LEVEL UP!** → Level {result.new_combat_level}"
                    embed.add_field(name="🏆 VICTORY", value=victory_text, inline=False)
                    if result.drops:
                        embed.add_field(
                            name="🎁 Loot Drops",
                            value=_format_drops(result.drops),
                            inline=False,
                        )
                    await interaction.edit_original_response(embed=embed, view=self)
                    return

                # Mob's turn
                await self._do_mob_turn(interaction, player_defended=False)

                if not self.battle.finished:
                    self._update_flee_button()
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

                # Player defends
                self.combat_uc.execute_player_defend(self.battle)

                # Mob's turn (with defend bonus)
                await self._do_mob_turn(interaction, player_defended=True)

                if not self.battle.finished:
                    self._update_flee_button()
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

                escaped, chance = self.combat_uc.attempt_flee(self.battle)
                pct = int(chance * 100)

                if escaped:
                    self.battle.finished = True
                    self._finish_battle()

                    # Save current HP/stamina (no death penalty)
                    self.combat_uc.repo.update_hp(self.author_id, self.battle.player_hp)
                    self.combat_uc.repo.update_stamina(self.author_id, self.battle.player_stamina)

                    embed = self._create_embed()
                    embed.add_field(
                        name="🏃 FLED",
                        value=f"You escaped the fight! ({pct}% chance)\nNo penalties, but no rewards either.",
                        inline=False,
                    )
                    await interaction.edit_original_response(embed=embed, view=self)
                else:
                    # Failed flee — mob gets a free attack
                    self.battle.turn += 1
                    turn = BattleTurn(
                        turn_number=self.battle.turn,
                        actor="player",
                        action="flee_fail",
                        actor_hp=self.battle.player_hp,
                        target_hp=self.battle.mob_hp,
                        actor_stamina=self.battle.player_stamina,
                        message=f"🏃 You tried to flee but couldn't escape! ({pct}% chance)",
                    )
                    self.battle.turns.append(turn)

                    await self._do_mob_turn(interaction, player_defended=False)

                    if not self.battle.finished:
                        self._update_flee_button()
                        embed = self._create_embed()
                        await interaction.edit_original_response(embed=embed, view=self)

        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Select item first", emoji="🍽️", style=discord.ButtonStyle.secondary, disabled=True, row=3)
    async def battle_consume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Not your fight!", ephemeral=True)
            return
        if not self._consume_selected_item:
            await interaction.response.send_message("Select an item from the dropdown first!", ephemeral=True)
            return
        await self._do_consume(interaction)

    @discord.ui.button(label="Request Help", emoji="\U0001f198", style=discord.ButtonStyle.secondary, row=4)
    async def request_help_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Convert to coop and post a join message."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the fighter can request help!", ephemeral=True)
            return

        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.battle.finished:
                    return

                # Disable this button
                button.label = "Help Requested!"
                button.disabled = True

                # Convert to coop
                coop_uc = CoopCombatUseCases(self.combat_uc.repo)
                coop_state = coop_uc.convert_to_coop(self.battle, self.author_id, self.username)

                # Disable all solo buttons
                self._disable_buttons()
                embed = self._create_embed()
                embed.set_footer(text="Switching to coop mode... Waiting for allies!")
                await interaction.edit_original_response(embed=embed, view=self)

                # Send join message
                join_view = JoinFightView(
                    coop_state=coop_state,
                    coop_uc=coop_uc,
                    combat_uc=self.combat_uc,
                    original_message=self.message,
                    original_author_id=self.author_id,
                )
                mob_hp_text = f"{coop_state.mob_hp}/{coop_state.mob_max_hp}"
                join_msg = await interaction.channel.send(
                    f"\U0001f198 **{self.username} needs help fighting "
                    f"{coop_state.mob_emoji} {coop_state.mob_name}!** "
                    f"(HP: {mob_hp_text})\n"
                    f"Click Join to help! ({COOP_JOIN_TIMEOUT}s)",
                    view=join_view,
                )
                join_view.message = join_msg
                # Remove original fighter from solo _active_battles — they'll be
                # tracked via the coop view
                _active_battles.discard(self.author_id)
                _active_battles.add(self.author_id)

        except Exception:
            traceback.print_exc()

    async def on_timeout(self) -> None:
        async with self._finish_lock:
            if self.battle.finished:
                # Already resolved by a button press
                if self.message:
                    try:
                        await self.message.edit(view=self)
                    except Exception:
                        pass
                return
            self.battle.finished = True
            self.battle.player_won = False
            self._finish_battle()
            # Apply defeat penalties — player abandoned the fight
            result = self.combat_uc.resolve_defeat(
                self.author_id, self.username, self.battle
            )
            if self.message:
                try:
                    embed = self._create_embed()
                    penalty_lines = []
                    if result.stars_lost > 0:
                        penalty_lines.append(f"💫 Stars lost: **{result.stars_lost}**")
                    if result.bank_loss > 0:
                        penalty_lines.append(f"🏦 Bank loss: **{result.bank_loss}**")
                    if result.items_lost:
                        penalty_lines.append(f"📦 Items lost: **{len(result.items_lost)}**")
                    if result.equipment_lost:
                        penalty_lines.append(f"🔧 Equipment lost: {', '.join(result.equipment_lost)}")
                    embed.add_field(
                        name="⏰ TIMED OUT — DEFEAT",
                        value="You abandoned the fight and were defeated!\n"
                              + ("\n".join(penalty_lines) if penalty_lines else ""),
                        inline=False,
                    )
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass


def _progress_bar(pct: float, length: int = 10) -> str:
    """Create a text progress bar."""
    filled = int(pct * length)
    return "█" * filled + "░" * (length - filled)


def _format_drops(drops: list[tuple[str, str]]) -> str:
    """Format a drops list into a display string for embeds."""
    if not drops:
        return ""
    res_lines = []
    for item_key, display in drops:
        res = get_resource(item_key)
        emoji = res.emoji if res else "📦"
        res_lines.append(f"{emoji} {display}")
    return "\n".join(res_lines)


# ---------------------------------------------------------------------------
# Coop — Join Fight View
# ---------------------------------------------------------------------------

class JoinFightView(discord.ui.View):
    """Lobby view that lets other players join an existing fight."""

    def __init__(self, coop_state: CoopBattleState, coop_uc: CoopCombatUseCases,
                 combat_uc: CombatUseCases, original_message, original_author_id: int):
        super().__init__(timeout=COOP_JOIN_TIMEOUT)
        self.coop_state = coop_state
        self.coop_uc = coop_uc
        self.combat_uc = combat_uc
        self.original_message = original_message
        self.original_author_id = original_author_id
        self.message = None

    @discord.ui.button(label="Join Fight", emoji="⚔️", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        # Check not in battle/duel
        if is_in_battle(user_id):
            await interaction.response.send_message("You're already in a fight!", ephemeral=True)
            return
        from cogs.gambling.handlers import is_in_duel
        if is_in_duel(user_id):
            await interaction.response.send_message("You're in a PvP duel!", ephemeral=True)
            return

        # Check location
        from cogs.locations.use_case import LocationUseCases
        loc_uc = LocationUseCases()
        if loc_uc.get_location(user_id) != "noodle_colosseum":
            await interaction.response.send_message(
                "You need to be at the **Noodle Colosseum** to join! Use `!travel`.",
                ephemeral=True,
            )
            return

        # Try to add player
        error = self.coop_uc.add_player(self.coop_state, user_id, str(interaction.user))
        if error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
            return

        _active_battles.add(user_id)

        # Update join message to show who's in
        player_names = [p.username for p in self.coop_state.players]
        player_list = ", ".join(player_names)
        count = len(self.coop_state.players)

        await interaction.response.edit_message(
            content=(
                f"\U0001f198 **Coop Fight vs {self.coop_state.mob_emoji} {self.coop_state.mob_name}!**\n"
                f"Players ({count}/{COOP_MAX_PLAYERS}): {player_list}\n"
                + ("Waiting for more players..." if count < COOP_MAX_PLAYERS else "Full! Starting...")
            ),
            view=self,
        )

        # If full (4 players), start immediately
        if count >= COOP_MAX_PLAYERS:
            await self._start_coop_battle(interaction)

    async def _start_coop_battle(self, interaction: discord.Interaction):
        """Transition from join phase to coop battle."""
        self.coop_state.open_for_join = False

        # Disable join button
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                player_names = [p.username for p in self.coop_state.players]
                await self.message.edit(
                    content=f"⚔️ Coop battle started! Players: {', '.join(player_names)}",
                    view=self,
                )
            except Exception:
                pass

        # Create coop battle view on the original message
        coop_view = CoopBattleView(
            coop_state=self.coop_state,
            coop_uc=self.coop_uc,
            combat_uc=self.combat_uc,
        )
        embed = coop_view.create_embed()
        if self.original_message:
            try:
                await self.original_message.edit(embed=embed, view=coop_view)
                coop_view.message = self.original_message
            except Exception:
                traceback.print_exc()

        self.stop()

    async def on_timeout(self):
        """Timeout — start with whoever joined (even if just the original player)."""
        self.coop_state.open_for_join = False

        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    content=f"⚔️ Join phase ended! Starting coop battle...",
                    view=self,
                )
            except Exception:
                pass

        # Start coop battle with whoever is in
        coop_view = CoopBattleView(
            coop_state=self.coop_state,
            coop_uc=self.coop_uc,
            combat_uc=self.combat_uc,
        )
        embed = coop_view.create_embed()
        if self.original_message:
            try:
                await self.original_message.edit(embed=embed, view=coop_view)
                coop_view.message = self.original_message
            except Exception:
                traceback.print_exc()


# ---------------------------------------------------------------------------
# Coop — Battle View (round-based)
# ---------------------------------------------------------------------------

class _CoopHPSelect(discord.ui.Select):
    """HP consume dropdown for coop battle — each player sees their own items."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="🍖 Consume HP item...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, CoopBattleView):
            return
        player = view._get_player(interaction.user.id)
        if not player or not player.alive:
            await interaction.response.send_message("You're not in this fight!", ephemeral=True)
            return
        view._pending_consume[interaction.user.id] = (self.values[0], "hp")
        await interaction.response.send_message(
            f"Selected **{self.values[0].replace('_', ' ').title()}** (HP). Click Consume to use it.",
            ephemeral=True,
        )


class _CoopStaminaSelect(discord.ui.Select):
    """Stamina consume dropdown for coop battle."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="⚡ Consume stamina item...", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, CoopBattleView):
            return
        player = view._get_player(interaction.user.id)
        if not player or not player.alive:
            await interaction.response.send_message("You're not in this fight!", ephemeral=True)
            return
        view._pending_consume[interaction.user.id] = (self.values[0], "stamina")
        await interaction.response.send_message(
            f"Selected **{self.values[0].replace('_', ' ').title()}** (stamina). Click Consume to use it.",
            ephemeral=True,
        )


class CoopBattleView(discord.ui.View):
    """Round-based coop battle view. All players pick actions, then resolve."""

    def __init__(self, coop_state: CoopBattleState, coop_uc: CoopCombatUseCases,
                 combat_uc: CombatUseCases):
        super().__init__(timeout=COOP_ROUND_TIMEOUT)
        self.coop_state = coop_state
        self.coop_uc = coop_uc
        self.combat_uc = combat_uc
        self.message = None
        self._finish_lock = asyncio.Lock()
        self._pending_consume: dict[int, tuple[str, str]] = {}  # user_id -> (item_key, type)
        self._health_uc = HealthUseCases(self.combat_uc.repo)
        self._rebuild_view()

    def _get_player(self, user_id: int) -> CoopPlayer | None:
        for p in self.coop_state.players:
            if p.user_id == user_id:
                return p
        return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Allow any participant to interact."""
        player = self._get_player(interaction.user.id)
        if not player or not player.alive:
            await interaction.response.send_message("You're not in this fight!", ephemeral=True)
            return False
        return True

    def _rebuild_view(self):
        """Rebuild view components."""
        self.clear_items()
        self.add_item(self.attack_button)
        self.add_item(self.defend_button)
        self.add_item(self.flee_button)
        self.add_item(self.consume_button)

    def create_embed(self) -> discord.Embed:
        s = self.coop_state

        if s.finished:
            mob_dead = s.mob_hp <= 0
            color = discord.Color.green() if mob_dead else discord.Color.red()
        else:
            color = discord.Color.orange()

        dungeon_info = DUNGEON_LEVELS.get(s.dungeon_level, {})
        dungeon_name = dungeon_info.get("name", f"Level {s.dungeon_level}")

        if s.ambush:
            title = f"⚔️ Coop Ambush — {s.mob_emoji} {s.mob_name}"
        else:
            title = f"⚔️ Coop Battle — {dungeon_name} (Level {s.dungeon_level})"

        embed = discord.Embed(title=title, color=color)

        # Player status lines
        player_lines = []
        for p in s.players:
            if not p.alive:
                player_lines.append(f"💀 **{p.username}** — OUT (defeated)")
                continue

            hp_pct = p.hp / p.max_hp if p.max_hp else 0
            hp_bar = _progress_bar(hp_pct)
            stam_pct = p.stamina / p.max_stamina if p.max_stamina else 0
            stam_bar = _progress_bar(stam_pct)

            action_icon = "✅" if p.action else "⏳"
            action_text = ""
            if p.action:
                action_text = f" {p.action.title()}"

            player_lines.append(
                f"👤 **{p.username}** — ❤️ {p.hp}/{p.max_hp} {hp_bar} "
                f"⚡ {p.stamina}/{p.max_stamina} {stam_bar} "
                f"{action_icon}{action_text}"
            )

        embed.add_field(
            name="Players",
            value="\n".join(player_lines) or "No players",
            inline=False,
        )

        # Mob stats
        mob_hp_pct = s.mob_hp / s.mob_max_hp if s.mob_max_hp else 0
        mob_hp_bar = _progress_bar(mob_hp_pct)

        embed.add_field(
            name=f"{s.mob_emoji} {s.mob_name}",
            value=(
                f"❤️ HP: {s.mob_hp}/{s.mob_max_hp} {mob_hp_bar}\n"
                f"⚔️ ATK: {s.mob_attack}  🛡️ DEF: {s.mob_defense}"
            ),
            inline=False,
        )

        # Combat log — last 6 entries
        recent = s.turns[-6:] if len(s.turns) > 6 else s.turns
        if recent:
            log_lines = [t.message for t in recent]
            embed.add_field(
                name=f"📜 Round {s.round}",
                value="\n".join(log_lines),
                inline=False,
            )

        alive_count = sum(1 for p in s.players if p.alive)
        total = len(s.players)
        if not s.finished:
            embed.set_footer(
                text=f"Round {s.round + 1} — Choose your action | \U0001f198 Coop ({alive_count}/{total} players)"
            )

        return embed

    async def _try_resolve_round(self, interaction: discord.Interaction):
        """If all actions are chosen, resolve the round."""
        if not self.coop_uc.all_actions_chosen(self.coop_state):
            return

        async with self._finish_lock:
            if self.coop_state.finished:
                return

            round_turns = self.coop_uc.resolve_round(self.coop_state)

            if self.coop_state.finished:
                # Check victory or defeat
                if self.coop_state.mob_hp <= 0:
                    rewards, all_drops = self.coop_uc.resolve_coop_victory(self.coop_state)
                    self._finish_coop_battle()
                    embed = self.create_embed()
                    reward_lines = []
                    for uid, stars in rewards.items():
                        p = self._get_player(uid)
                        name = p.username if p else str(uid)
                        if stars > 0:
                            reward_lines.append(f"⭐ **{name}**: +{stars} stars")
                        else:
                            reward_lines.append(f"✅ **{name}**: survived!")
                    embed.add_field(
                        name="🏆 VICTORY",
                        value="\n".join(reward_lines) if reward_lines else "No rewards.",
                        inline=False,
                    )
                    # Show drops per player
                    for uid, drops in all_drops.items():
                        if drops:
                            p = self._get_player(uid)
                            name = p.username if p else str(uid)
                            embed.add_field(
                                name=f"🎁 {name}'s Loot",
                                value=_format_drops(drops),
                                inline=True,
                            )
                    await self._update_message(embed)
                else:
                    # All players dead
                    self._finish_coop_battle()
                    embed = self.create_embed()
                    embed.add_field(
                        name="💀 TOTAL DEFEAT",
                        value="All players have been defeated!",
                        inline=False,
                    )
                    await self._update_message(embed)
            else:
                # Round resolved but fight continues — reset timer
                self.timeout = COOP_ROUND_TIMEOUT
                embed = self.create_embed()
                await self._update_message(embed)

    def _finish_coop_battle(self):
        """Clean up after coop battle ends."""
        for p in self.coop_state.players:
            _active_battles.discard(p.user_id)
        self._disable_buttons()

    def _disable_buttons(self):
        for item in self.children:
            item.disabled = True

    async def _update_message(self, embed: discord.Embed):
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                traceback.print_exc()

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._get_player(interaction.user.id)
        if player.action is not None:
            await interaction.response.send_message("You already chose this round!", ephemeral=True)
            return
        player.action = "attack"
        await interaction.response.defer()
        embed = self.create_embed()
        await self._update_message(embed)
        await self._try_resolve_round(interaction)

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._get_player(interaction.user.id)
        if player.action is not None:
            await interaction.response.send_message("You already chose this round!", ephemeral=True)
            return
        player.action = "defend"
        await interaction.response.defer()
        embed = self.create_embed()
        await self._update_message(embed)
        await self._try_resolve_round(interaction)

    @discord.ui.button(label="Flee", style=discord.ButtonStyle.secondary, emoji="🏃", row=0)
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._get_player(interaction.user.id)
        if player.action is not None:
            await interaction.response.send_message("You already chose this round!", ephemeral=True)
            return
        player.action = "flee"
        await interaction.response.defer()
        embed = self.create_embed()
        await self._update_message(embed)
        await self._try_resolve_round(interaction)

    @discord.ui.button(label="Consume", style=discord.ButtonStyle.success, emoji="🍽️", row=3)
    async def consume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._get_player(interaction.user.id)
        if player.action is not None:
            await interaction.response.send_message("You already chose this round!", ephemeral=True)
            return

        uid = interaction.user.id
        pending = self._pending_consume.get(uid)

        if not pending:
            # Show item selection via ephemeral dropdowns
            items = self.combat_uc.repo.get_inventory_items(uid)
            item_counts: dict[str, int] = {}
            for item in items:
                key = item["item_key"]
                item_counts[key] = item_counts.get(key, 0) + 1

            hp_lines = []
            stam_lines = []
            for key, count in sorted(item_counts.items()):
                heal = self._health_uc.get_hp_value(key)
                if heal and count > 0:
                    display = key.replace("_", " ").title()
                    hp_lines.append(f"🍖 **{display}** (+{heal} HP) x{count} — type: `{key}`")
                recovery = STAMINA_RECOVERY.get(key)
                if recovery and count > 0:
                    display = key.replace("_", " ").title()
                    stam_lines.append(f"⚡ **{display}** (+{recovery} stam) x{count} — type: `{key}`")

            if not hp_lines and not stam_lines:
                await interaction.response.send_message("You have no consumable items!", ephemeral=True)
                return

            text = "**Select an item from the dropdowns above**, then click Consume again.\n\n"
            if hp_lines:
                text += "**HP Items:**\n" + "\n".join(hp_lines[:10]) + "\n\n"
            if stam_lines:
                text += "**Stamina Items:**\n" + "\n".join(stam_lines[:10])

            # Build ephemeral view with selects
            ephemeral_view = _CoopConsumeSelectView(self, uid)
            await interaction.response.send_message(text, view=ephemeral_view, ephemeral=True)
            return

        # Consume the pending item
        item_key, consume_type = pending
        player.action = "consume"
        player.consume_item = item_key
        player.consume_type = consume_type
        del self._pending_consume[uid]

        await interaction.response.defer()
        embed = self.create_embed()
        await self._update_message(embed)
        await self._try_resolve_round(interaction)

    async def on_timeout(self):
        """Auto-resolve: any player without an action defaults to defend."""
        async with self._finish_lock:
            if self.coop_state.finished:
                return

            for p in self.coop_state.players:
                if p.alive and p.action is None:
                    p.action = "defend"

            round_turns = self.coop_uc.resolve_round(self.coop_state)

            if self.coop_state.finished:
                if self.coop_state.mob_hp <= 0:
                    rewards, all_drops = self.coop_uc.resolve_coop_victory(self.coop_state)
                    self._finish_coop_battle()
                    embed = self.create_embed()
                    reward_lines = []
                    for uid, stars in rewards.items():
                        p = self._get_player(uid)
                        name = p.username if p else str(uid)
                        if stars > 0:
                            reward_lines.append(f"⭐ **{name}**: +{stars} stars")
                    embed.add_field(
                        name="🏆 VICTORY",
                        value="\n".join(reward_lines) if reward_lines else "No rewards.",
                        inline=False,
                    )
                    for uid, drops in all_drops.items():
                        if drops:
                            p = self._get_player(uid)
                            name = p.username if p else str(uid)
                            embed.add_field(
                                name=f"🎁 {name}'s Loot",
                                value=_format_drops(drops),
                                inline=True,
                            )
                    await self._update_message(embed)
                else:
                    self._finish_coop_battle()
                    embed = self.create_embed()
                    embed.add_field(
                        name="💀 TOTAL DEFEAT",
                        value="All players have been defeated!",
                        inline=False,
                    )
                    await self._update_message(embed)
            else:
                # Fight continues, but timed out — just show the result
                embed = self.create_embed()
                embed.set_footer(text="⏰ Round auto-resolved (idle players defended)")
                await self._update_message(embed)
                # Restart the timeout for next round
                self.timeout = COOP_ROUND_TIMEOUT


class _CoopConsumeSelectView(discord.ui.View):
    """Ephemeral view for selecting a consume item in coop."""

    def __init__(self, parent_view: CoopBattleView, user_id: int):
        super().__init__(timeout=30)
        self.parent_view = parent_view
        self.user_id = user_id
        self._build_selects()

    def _build_selects(self):
        items = self.parent_view.combat_uc.repo.get_inventory_items(self.user_id)
        item_counts: dict[str, int] = {}
        for item in items:
            key = item["item_key"]
            item_counts[key] = item_counts.get(key, 0) + 1

        hp_opts = []
        stam_opts = []
        health_uc = self.parent_view._health_uc

        for key, count in sorted(item_counts.items()):
            heal = health_uc.get_hp_value(key)
            if heal and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "🍽️"
                hp_opts.append(discord.SelectOption(
                    label=f"{display} (+{heal} HP) x{count}",
                    value=key,
                    emoji=emoji,
                ))
            recovery = STAMINA_RECOVERY.get(key)
            if recovery and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "⚡"
                stam_opts.append(discord.SelectOption(
                    label=f"{display} (+{recovery} stam) x{count}",
                    value=key,
                    emoji=emoji,
                ))

        if hp_opts:
            self.add_item(_CoopHPSelect(hp_opts[:25]))
        if stam_opts:
            self.add_item(_CoopStaminaSelect(stam_opts[:25]))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


# ---------------------------------------------------------------------------
# Gear management view — interactive equip/unequip buttons
# ---------------------------------------------------------------------------

class _GearSlotSelect(discord.ui.Select):
    """Dropdown showing owned items for a specific equipment slot."""

    def __init__(self, slot: str, owned_items: list[tuple[str, str]], equipped_key: str | None, row: int):
        self.slot = slot
        slot_emoji = {"weapon": "🗡️", "shield": "🛡️", "armor": "🦺"}[slot]
        options = []
        for item_key, item in owned_items:
            label = f"{item.name} (T{item.tier})"
            desc = f"ATK +{item.attack}  DEF +{item.defense}  HP +{item.hp_bonus}"
            is_equipped = item_key == equipped_key
            options.append(discord.SelectOption(
                label=label,
                value=item_key,
                emoji=item.emoji,
                description=desc,
                default=is_equipped,
            ))
        # Add "unequip" option
        options.append(discord.SelectOption(
            label=f"Unequip {slot}",
            value=f"__unequip_{slot}__",
            emoji="❌",
            description=f"Remove your {slot}",
            default=equipped_key is None,
        ))
        super().__init__(
            placeholder=f"{slot_emoji} Choose {slot}...",
            options=options,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        view: GearView = self.view
        if interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your gear menu!", ephemeral=True)
            return

        value = self.values[0]
        if value.startswith("__unequip_"):
            result = view.equip_uc.unequip(view.author_id, self.slot)
        else:
            result = view.equip_uc.equip(view.author_id, value)

        # Rebuild the view with updated state
        view.refresh()
        embed = view.build_embed()
        status_line = f"✅ {result.message}" if result.success else f"❌ {result.message}"
        embed.set_footer(text=status_line)
        await interaction.response.edit_message(embed=embed, view=view)


class GearView(discord.ui.View):
    """Interactive gear management view with dropdowns per slot."""

    def __init__(self, author_id: int, equip_uc, health_uc, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.equip_uc = equip_uc
        self.health_uc = health_uc
        self.message = None
        self.refresh()

    def refresh(self):
        """Rebuild dropdowns from current equipment state."""
        self.clear_items()
        equipment = self.equip_uc.repo.get_user_equipment(self.author_id)
        stats = self.equip_uc.repo.get_combat_stats(self.author_id)

        # Find all owned combat items grouped by slot
        slot_items: dict[str, list[tuple[str, object]]] = {
            "weapon": [], "shield": [], "armor": [],
        }
        for item_key, uses in equipment.items():
            if uses > 0 and item_key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[item_key]
                slot_items[item.slot].append((item_key, item))

        # Sort each slot by tier descending
        for slot in slot_items:
            slot_items[slot].sort(key=lambda x: (-x[1].tier, -x[1].attack - x[1].defense))

        # Add a select for each slot that has items (or has something equipped)
        row = 0
        for slot in ("weapon", "shield", "armor"):
            equipped_key = stats.get(f"equipped_{slot}")
            items = slot_items[slot]
            if not items and not equipped_key:
                continue  # No items and nothing equipped — skip
            if items:
                self.add_item(_GearSlotSelect(slot, items, equipped_key, row=row))
                row += 1

    def build_embed(self) -> discord.Embed:
        gear = self.equip_uc.get_gear(self.author_id)
        status = self.health_uc.get_status(self.author_id)

        embed = discord.Embed(
            title="⚔️ Combat Gear",
            color=discord.Color.dark_gold(),
        )
        embed.add_field(
            name="Equipped",
            value=(
                f"🗡️ Weapon: {gear.weapon or '*empty*'}\n"
                f"🛡️ Shield: {gear.shield or '*empty*'}\n"
                f"🦺 Armor: {gear.armor or '*empty*'}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Total Stats",
            value=(
                f"⚔️ Attack: **{gear.total_attack + 5}** (base 5 + {gear.total_attack})\n"
                f"🛡️ Defense: **{gear.total_defense + 2}** (base 2 + {gear.total_defense})\n"
                f"❤️ Max HP: **{status.max_hp}** (base 100 + {gear.total_hp_bonus})"
            ),
            inline=False,
        )
        embed.description = "Use the dropdowns below to equip or swap gear."
        return embed

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


# ---------------------------------------------------------------------------
# Recipe page view — paginated tier navigation
# ---------------------------------------------------------------------------

class _RecipePageView(discord.ui.View):
    """Paginated view for browsing crafting recipes by tier."""

    def __init__(self, author_id: int, pages: list[tuple[str, discord.Embed]], timeout: float = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.pages = pages  # list of (tier_label, embed)
        self.current = 0
        self.message = None
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        for i, (label, _) in enumerate(self.pages):
            style = discord.ButtonStyle.primary if i == self.current else discord.ButtonStyle.secondary
            btn = discord.ui.Button(label=label, style=style, row=0)
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("Not your recipe book!", ephemeral=True)
                return
            self.current = index
            self._build_buttons()
            await interaction.response.edit_message(embed=self.pages[index][1], view=self)
        return callback

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


# ---------------------------------------------------------------------------
# Consume View (unified eat/drink menu)
# ---------------------------------------------------------------------------

class _ConsumeHPSelect(discord.ui.Select):
    """Dropdown for HP restoration items."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(
            placeholder="🍖 Restore HP...",
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, _ConsumeView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return
        item_key = self.values[0]
        view.selected_item = item_key
        view.selected_type = "hp"
        await view.do_consume(interaction)


class _ConsumeStaminaSelect(discord.ui.Select):
    """Dropdown for stamina restoration items."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(
            placeholder="⚡ Restore Stamina...",
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, _ConsumeView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return
        item_key = self.values[0]
        view.selected_item = item_key
        view.selected_type = "stamina"
        await view.do_consume(interaction)


class _ConsumeView(discord.ui.View):
    """Two-dropdown consume menu with a Consume Again button."""

    def __init__(
        self,
        author_id: int,
        health_uc: HealthUseCases,
        repo,
        hp_options: list[discord.SelectOption],
        stam_options: list[discord.SelectOption],
        timeout: float = 120,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.health_uc = health_uc
        self.repo = repo
        self.message = None
        self.selected_item: str | None = None
        self.selected_type: str | None = None  # "hp" or "stamina"
        self._hp_options = hp_options
        self._stam_options = stam_options

        if hp_options:
            self.add_item(_ConsumeHPSelect(hp_options))
        if stam_options:
            self.add_item(_ConsumeStaminaSelect(stam_options))

    def _rebuild_options(self):
        """Refresh item counts in dropdown options after consuming."""
        items = self.repo.get_inventory_items(self.author_id)
        item_counts: dict[str, int] = {}
        for item in items:
            key = item["item_key"]
            item_counts[key] = item_counts.get(key, 0) + 1

        # Rebuild HP options
        new_hp = []
        for key, count in sorted(item_counts.items()):
            heal = self.health_uc.get_hp_value(key)
            if heal and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "🍽️"
                new_hp.append(discord.SelectOption(
                    label=f"{display} (+{heal} HP) x{count}",
                    value=key,
                    emoji=emoji,
                    default=(key == self.selected_item and self.selected_type == "hp"),
                ))
        self._hp_options = new_hp

        new_stam = []
        for key, count in sorted(item_counts.items()):
            recovery = STAMINA_RECOVERY.get(key)
            if recovery and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "⚡"
                new_stam.append(discord.SelectOption(
                    label=f"{display} (+{recovery} stam) x{count}",
                    value=key,
                    emoji=emoji,
                    default=(key == self.selected_item and self.selected_type == "stamina"),
                ))
        self._stam_options = new_stam

        # Rebuild the view components
        self.clear_items()
        if self._hp_options:
            self.add_item(_ConsumeHPSelect(self._hp_options))
        if self._stam_options:
            self.add_item(_ConsumeStaminaSelect(self._stam_options))
        # Re-add the consume again button
        self.add_item(self.consume_again_btn)

    async def do_consume(self, interaction: discord.Interaction):
        """Consume the selected item and update the embed."""
        if self.selected_type == "hp":
            result = self.health_uc.eat_fish(self.author_id, self.selected_item)
        else:
            result = self.health_uc.drink(self.author_id, self.selected_item)

        if not result.success:
            # Item depleted or at full — disable button, show error
            self.consume_again_btn.disabled = True
            self.consume_again_btn.label = "Can't Consume"
            self.consume_again_btn.style = discord.ButtonStyle.secondary
            self._rebuild_options()
            status = self.health_uc.get_status(self.author_id)
            embed = _consume_status_embed(status, f"❌ {result.message}")
            await interaction.response.edit_message(embed=embed, view=self)
            return

        # Success — update button and rebuild dropdowns
        status = self.health_uc.get_status(self.author_id)
        display = self.selected_item.replace("_", " ").title()
        res = get_resource(self.selected_item)
        emoji = res.emoji if res else "🍽️"

        self.consume_again_btn.disabled = False
        self.consume_again_btn.label = f"Consume {display}"
        self.consume_again_btn.emoji = emoji
        self.consume_again_btn.style = discord.ButtonStyle.success
        self._rebuild_options()

        if self.selected_type == "hp":
            msg = f"🍖 {result.message}"
        else:
            msg = f"⚡ {result.message}"

        embed = _consume_status_embed(status, msg)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Select an item first", emoji="🍽️", style=discord.ButtonStyle.secondary, disabled=True, row=3)
    async def consume_again_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return
        if not self.selected_item:
            await interaction.response.send_message("Select an item from the dropdown first!", ephemeral=True)
            return
        await self.do_consume(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


def _consume_status_embed(status, last_action: str) -> discord.Embed:
    hp_pct = status.current_hp / status.max_hp if status.max_hp else 0
    hp_bar = _progress_bar(hp_pct)
    stam_pct = status.current_stamina / status.max_stamina if status.max_stamina else 0
    stam_bar = _progress_bar(stam_pct)
    embed = discord.Embed(
        title="🍽️ Consume Menu",
        description=(
            f"{last_action}\n\n"
            f"❤️ **HP:** {status.current_hp}/{status.max_hp} {hp_bar}\n"
            f"⚡ **Stamina:** {status.current_stamina}/{status.max_stamina} {stam_bar}\n\n"
            "Select an item or click the button to consume again."
        ),
        color=discord.Color.green(),
    )
    return embed


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class CombatCog(commands.Cog):
    """Combat commands — fight mobs, manage gear, consume, craft."""

    def __init__(self, bot):
        self.bot = bot
        self.combat_uc = CombatUseCases()
        self.health_uc = HealthUseCases(self.combat_uc.repo)
        self.equip_uc = EquipmentUseCases(self.combat_uc.repo)
        self.craft_uc = CraftingUseCases(self.combat_uc.repo)

    # ── Fight ─────────────────────────────────────────────────

    @commands.command(name="fight", aliases=["battle", "f"])
    async def fight(self, ctx):
        """Fight a random mob in the Noodle Colosseum!"""
        if not await require_location(ctx, "noodle_colosseum"):
            return

        if is_in_battle(ctx.author.id):
            await ctx.send(f"❌ {ctx.author.mention}, you're already in a fight! Finish it first.")
            return

        from cogs.gambling.handlers import is_in_duel
        if is_in_duel(ctx.author.id):
            await ctx.send(f"❌ {ctx.author.mention}, you're in a PvP duel! Finish it first.")
            return

        # Gear warning
        from cogs.combat.use_case.gear_check import gear_warning
        stats = self.combat_uc.repo.get_combat_stats(ctx.author.id)
        active_level = stats["active_combat_level"]
        level_mobs = MOBS_BY_LEVEL.get(active_level, [])
        warning = gear_warning(ctx.author.id, level_mobs, self.combat_uc.repo)
        if warning:
            await ctx.send(warning)

        battle, error = self.combat_uc.start_fight(ctx.author.id, str(ctx.author))
        if error:
            await ctx.send(f"❌ {error}")
            return

        # Confirmation for L3+ dungeons
        if battle.dungeon_level >= 3:
            penalty = DEATH_PENALTIES[battle.dungeon_level]
            view = _DeathConfirmView(ctx.author.id)
            await ctx.send(
                f"⚠️ **Dungeon Level {battle.dungeon_level}** — Death penalty: "
                f"**{penalty['description']}**\n"
                f"Are you sure you want to fight?",
                view=view,
            )
            await view.wait()
            if not view.confirmed:
                return

        # Start the battle
        battle_view = BattleView(battle, self.combat_uc, ctx.author.id, str(ctx.author))
        embed = battle_view._create_embed()
        msg = await ctx.send(embed=embed, view=battle_view)
        battle_view.message = msg

    # ── Dungeon level management ──────────────────────────────

    @commands.command(name="dungeon", aliases=["dungeonlevel", "dl"])
    async def dungeon(self, ctx, level: int = None):
        """View or switch dungeon levels. Usage: !dungeon [level]"""
        if level is None:
            stats = self.combat_uc.repo.get_combat_stats(ctx.author.id)
            active = stats["active_combat_level"]
            combat_lvl = stats["combat_level"]

            embed = discord.Embed(
                title="🏰 Noodle Colosseum — Dungeons",
                description=f"Combat Level: **{combat_lvl}** | Active: **Level {active}**",
                color=discord.Color.dark_purple(),
            )
            for lvl, info in DUNGEON_LEVELS.items():
                locked = combat_lvl < (lvl - 1)
                status = "🔒 Locked" if locked else ("⚔️ Active" if lvl == active else "✅ Unlocked")
                mobs = MOBS_BY_LEVEL.get(lvl, [])
                mob_names = ", ".join(f"{m.emoji}{m.name}" for m in mobs[:3])
                if len(mobs) > 3:
                    mob_names += f" +{len(mobs)-3} more"
                penalty = DEATH_PENALTIES[lvl]["description"]
                embed.add_field(
                    name=f"{info['emoji']} Level {lvl}: {info['name']} [{status}]",
                    value=f"Mobs: {mob_names}\n☠️ Death: {penalty}",
                    inline=False,
                )
            await ctx.send(embed=embed)
            return

        result = self.combat_uc.set_active_level(ctx.author.id, level)
        if result.success:
            await ctx.send(f"✅ {result.message}")
        else:
            await ctx.send(f"❌ {result.message}")

    # ── Health & Stamina ──────────────────────────────────────

    @commands.command(name="hp", aliases=["health"])
    async def hp(self, ctx):
        """Check your current HP and stamina."""
        status = self.health_uc.get_status(ctx.author.id)
        hp_bar = _progress_bar(status.current_hp / status.max_hp if status.max_hp else 0)
        stam_bar = _progress_bar(status.current_stamina / status.max_stamina if status.max_stamina else 0)
        await ctx.send(
            f"❤️ **HP:** {status.current_hp}/{status.max_hp} {hp_bar}\n"
            f"⚡ **Stamina:** {status.current_stamina}/{status.max_stamina} {stam_bar}"
        )

    @commands.command(name="consume", aliases=["c", "eat", "drink"])
    async def consume(self, ctx):
        """Open the consume menu to restore HP or stamina from your inventory."""
        health_uc = self.health_uc
        repo = self.combat_uc.repo
        user_id = ctx.author.id

        # Gather inventory — all consumables are rows in user_inventory_items
        items = repo.get_inventory_items(user_id)
        item_counts: dict[str, int] = {}
        for item in items:
            key = item["item_key"]
            item_counts[key] = item_counts.get(key, 0) + 1

        # Build HP items list
        hp_options = []
        for key, count in sorted(item_counts.items()):
            heal = health_uc.get_hp_value(key)
            if heal and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "🍽️"
                hp_options.append(
                    discord.SelectOption(
                        label=f"{display} (+{heal} HP) x{count}",
                        value=key,
                        emoji=emoji,
                    )
                )

        # Build stamina items list
        stam_options = []
        for key, count in sorted(item_counts.items()):
            recovery = STAMINA_RECOVERY.get(key)
            if recovery and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "⚡"
                stam_options.append(
                    discord.SelectOption(
                        label=f"{display} (+{recovery} stam) x{count}",
                        value=key,
                        emoji=emoji,
                    )
                )

        if not hp_options and not stam_options:
            await ctx.send(f"❌ {ctx.author.mention}, you don't have any consumable items!")
            return

        status = health_uc.get_status(user_id)
        embed = _consume_status_embed(status, "Select an item to consume.")

        view = _ConsumeView(ctx.author.id, health_uc, repo, hp_options, stam_options)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    # ── Equipment ─────────────────────────────────────────────

    @commands.command(name="equip")
    async def equip(self, ctx, *, item_name: str):
        """Equip a combat item. Usage: !equip <item key>"""
        # Try to match by key or name
        item_key = _resolve_item_key(item_name)
        if not item_key:
            await ctx.send(f"❌ Unknown combat item: `{item_name}`. Check `!gear` for options.")
            return

        result = self.equip_uc.equip(ctx.author.id, item_key)
        if result.success:
            await ctx.send(f"✅ {result.message}")
        else:
            await ctx.send(f"❌ {result.message}")

    @commands.command(name="unequip")
    async def unequip(self, ctx, slot: str):
        """Unequip a combat slot. Usage: !unequip <weapon|shield|armor>"""
        result = self.equip_uc.unequip(ctx.author.id, slot.lower())
        if result.success:
            await ctx.send(f"✅ {result.message}")
        else:
            await ctx.send(f"❌ {result.message}")

    @commands.command(name="gear", aliases=["combatgear", "cg"])
    async def gear(self, ctx):
        """View and manage your equipped combat gear."""
        view = GearView(ctx.author.id, self.equip_uc, self.health_uc)
        embed = view.build_embed()
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    # ── Crafting ──────────────────────────────────────────────

    @commands.command(name="craft")
    async def craft_cmd(self, ctx, *, recipe_name: str):
        """Craft an item. Usage: !craft <recipe key>"""
        recipe_key = _resolve_recipe_key(recipe_name)
        if not recipe_key:
            await ctx.send(f"❌ Unknown recipe: `{recipe_name}`. Use `!recipes` to see all.")
            return

        result = self.craft_uc.craft(ctx.author.id, recipe_key)
        if result.success:
            await ctx.send(f"🔨 {result.message}")
        else:
            await ctx.send(f"❌ {result.message}")

    @commands.command(name="recipes", aliases=["recipelist"])
    async def recipes(self, ctx):
        """View all crafting recipes grouped by tier."""
        recipe_list = self.craft_uc.get_recipes(ctx.author.id)
        equipment = self.equip_uc.repo.get_user_equipment(ctx.author.id)

        # Build recipe data grouped by tier/category
        tiers: dict[str, list[str]] = {}
        tier_order = ["Tier 2", "Tier 3", "Tier 4", "Tier 5", "Potions"]

        for r in recipe_list:
            key = _find_recipe_key(r.name)
            ingredients = " + ".join(
                f"{_ingredient_emoji(name)}{name.replace('_', ' ').title()} x{count}"
                for name, count in r.ingredients
            )

            if key and key in COMBAT_ITEMS:
                item = COMBAT_ITEMS[key]
                tier_label = f"Tier {item.tier}"
                # Stats summary
                stats = []
                if item.attack:
                    stats.append(f"ATK +{item.attack}")
                if item.defense:
                    stats.append(f"DEF +{item.defense}")
                if item.hp_bonus:
                    stats.append(f"HP +{item.hp_bonus}")
                stat_str = " | ".join(stats)
                # Owned check
                owned = equipment.get(key, 0) > 0
                if owned:
                    status = "📦"
                elif r.can_craft:
                    status = "✅"
                else:
                    status = "❌"
                line = f"{status} {r.emoji} **{r.name}** — {stat_str}\n> {ingredients}"
            else:
                tier_label = "Potions"
                status = "✅" if r.can_craft else "❌"
                # Potion effect
                from cogs.combat.constants import STAMINA_RECOVERY
                stam = STAMINA_RECOVERY.get(key, 0)
                effect = f"+{stam} stamina" if stam else ""
                line = f"{status} {r.emoji} **{r.name}**"
                if effect:
                    line += f" — {effect}"
                line += f"\n> {ingredients}"

            tiers.setdefault(tier_label, []).append(line)

        # Build paginated embeds per tier
        pages = []
        for tier in tier_order:
            lines = tiers.get(tier, [])
            if not lines:
                continue
            embed = discord.Embed(
                title=f"🔨 Crafting Recipes — {tier}",
                description="✅ = can craft now | ❌ = missing materials | 📦 = already owned\nUse `!craft <name>` to craft.\n\n" + "\n\n".join(lines),
                color=discord.Color.dark_gold(),
            )
            pages.append((tier, embed))

        if not pages:
            await ctx.send("No crafting recipes available.")
            return

        view = _RecipePageView(ctx.author.id, pages)
        msg = await ctx.send(embed=pages[0][1], view=view)
        view.message = msg

    @commands.command(name="recipe")
    async def recipe(self, ctx, *, recipe_name: str):
        """View details for a specific recipe. Usage: !recipe <name>"""
        recipe_key = _resolve_recipe_key(recipe_name)
        if not recipe_key:
            await ctx.send(f"❌ Unknown recipe: `{recipe_name}`")
            return

        info = self.craft_uc.get_recipe(recipe_key, ctx.author.id)
        if not info:
            await ctx.send(f"❌ Recipe not found: `{recipe_name}`")
            return

        embed = discord.Embed(
            title=f"{info.emoji} {info.name}",
            description=info.description,
            color=discord.Color.green() if info.can_craft else discord.Color.red(),
        )
        ingredients_text = "\n".join(
            f"• **{name.replace('_', ' ').title()}** x{count}" for name, count in info.ingredients
        )
        embed.add_field(
            name="Ingredients",
            value=ingredients_text,
            inline=False,
        )
        embed.set_footer(text="✅ You can craft this!" if info.can_craft else "❌ Missing materials")
        await ctx.send(embed=embed)

    # ── Stamina status shortcut ───────────────────────────────

    @commands.command(name="stamina", aliases=["stam"])
    async def stamina(self, ctx):
        """Check your current stamina."""
        status = self.health_uc.get_status(ctx.author.id)
        bar = _progress_bar(status.current_stamina / status.max_stamina if status.max_stamina else 0)
        await ctx.send(f"⚡ **Stamina:** {status.current_stamina}/{status.max_stamina} {bar}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_item_key(name: str) -> str | None:
    """Try to match a combat item by key or display name."""
    lower = name.lower().replace(" ", "_")
    if lower in COMBAT_ITEMS:
        return lower
    # Fuzzy match by name
    for key, item in COMBAT_ITEMS.items():
        if item.name.lower() == name.lower():
            return key
    return None


def _resolve_recipe_key(name: str) -> str | None:
    """Try to match a recipe by key or display name."""
    lower = name.lower().replace(" ", "_")
    if lower in CRAFT_RECIPES:
        return lower
    for key, recipe in CRAFT_RECIPES.items():
        if recipe.result_name.lower() == name.lower():
            return key
    return None


def _find_recipe_key(name: str) -> str | None:
    """Find recipe key by result name."""
    for key, recipe in CRAFT_RECIPES.items():
        if recipe.result_name == name:
            return key
    return None


def _ingredient_emoji(item_key: str) -> str:
    """Return the emoji for an ingredient key, with trailing space."""
    res = get_resource(item_key)
    return f"{res.emoji} " if res else ""


# ---------------------------------------------------------------------------
# Cog setup
# ---------------------------------------------------------------------------

async def setup(bot):
    await bot.add_cog(CombatCog(bot))

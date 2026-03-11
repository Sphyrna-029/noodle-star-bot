"""Combat commands cog — fight, eat, drink, equip, craft, gear, hp, stamina."""

import asyncio
import traceback

import discord
from discord.ext import commands

from cogs.combat.constants import (
    COMBAT_ITEMS, CRAFT_RECIPES, DEATH_PENALTIES, DUNGEON_LEVELS,
    FISH_HEAL_VALUES, MOBS_BY_LEVEL, STAMINA_RECOVERY,
)
from cogs.combat.dto import BattleState, BattleTurn
from cogs.combat.use_case.combat import CombatUseCases
from cogs.combat.use_case.crafting import CraftingUseCases
from cogs.combat.use_case.equipment import EquipmentUseCases
from cogs.combat.use_case.health import HealthUseCases
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


class BattleView(discord.ui.View):
    """Interactive combat view with Attack/Defend/Flee buttons."""

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
        # Initialize flee lockout state
        self._update_flee_button()

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
                embed.set_footer(text=f"⚔️ Attack | 🛡️ Defend | 🏃 Flee (locked for {remaining} rounds)")
            else:
                embed.set_footer(text="⚔️ Attack | 🛡️ Defend | 🏃 Flee")

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

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
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

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="🛡️")
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

    @discord.ui.button(label="Flee", style=discord.ButtonStyle.secondary, emoji="🏃")
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

    async def on_timeout(self) -> None:
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
# Cog
# ---------------------------------------------------------------------------

class CombatCog(commands.Cog):
    """Combat commands — fight mobs, manage gear, eat, drink, craft."""

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

    @commands.command(name="eat")
    async def eat(self, ctx, *, fish_name: str = None):
        """Eat a fish to restore HP. Usage: !eat <fish name>"""
        if not fish_name:
            # Show healable fish list
            lines = []
            for key, hp in sorted(FISH_HEAL_VALUES.items(), key=lambda x: x[1]):
                display = key.replace("_", " ").title()
                lines.append(f"**{display}** → +{hp} HP")
            embed = discord.Embed(
                title="🍽️ Healing Fish",
                description="Use `!eat <fish name>` to restore HP.\n\n" + "\n".join(lines),
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
            return

        result = self.health_uc.eat_fish(ctx.author.id, fish_name)
        if result.success:
            await ctx.send(
                f"🍽️ {result.message}\n"
                f"❤️ HP: **{result.current_hp}/{result.max_hp}**"
            )
        else:
            await ctx.send(f"❌ {result.message}")

    @commands.command(name="drink")
    async def drink(self, ctx, *, item_name: str = None):
        """Drink a stamina item. Usage: !drink <item name>"""
        if not item_name:
            lines = []
            for key, stam in sorted(STAMINA_RECOVERY.items(), key=lambda x: x[1]):
                display = key.replace("_", " ").title()
                lines.append(f"**{display}** → +{stam} stamina")
            embed = discord.Embed(
                title="🧪 Stamina Recovery Items",
                description="Use `!drink <item name>` to restore stamina.\n\n" + "\n".join(lines),
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
            return

        result = self.health_uc.drink(ctx.author.id, item_name)
        if result.success:
            await ctx.send(
                f"🧪 {result.message}\n"
                f"⚡ Stamina: **{result.current_stamina}/{result.max_stamina}**"
            )
        else:
            await ctx.send(f"❌ {result.message}")

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
                f"{name.replace('_', ' ').title()} x{count}"
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


# ---------------------------------------------------------------------------
# Cog setup
# ---------------------------------------------------------------------------

async def setup(bot):
    await bot.add_cog(CombatCog(bot))

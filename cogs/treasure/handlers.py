"""Treasure chest lock-picking commands cog — button-based UI."""

from __future__ import annotations

import calendar
import random
import traceback
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from cogs.treasure.constants import (
    EXPIRED_MESSAGE,
    LOCK_ATTEMPTS,
    LOCK_PIN_COUNT_ITEM_CHEST,
    LOCK_PIN_MAX,
    LOCK_PIN_MIN,
    TIMEOUT_MESSAGE,
    TREASURE_ANNOUNCEMENT_CHANNEL_ID,
    TREASURE_REWARD_MAX,
    TREASURE_REWARD_MAX_RARE,
    TREASURE_REWARD_MIN,
    TREASURE_REWARD_MIN_RARE,
)
from cogs.treasure.dto import ChestState
from cogs.treasure.use_case import TreasureUseCases


# ---------------------------------------------------------------------------
# Pin select dropdown
# ---------------------------------------------------------------------------

class _PinSelect(discord.ui.Select):
    """Dropdown for selecting a single pin value (1-4)."""

    def __init__(self, pin_index: int, row: int, current_value: int | None = None):
        self.pin_index = pin_index
        options = [
            discord.SelectOption(
                label=str(i), value=str(i),
                default=(current_value == i),
            )
            for i in range(LOCK_PIN_MIN, LOCK_PIN_MAX + 1)
        ]
        super().__init__(placeholder=f"🔢 Pin {pin_index + 1}", options=options, row=row)

    async def callback(self, interaction: discord.Interaction):
        view: ChestView = self.view
        chest = view.cog.treasure._chest
        if not chest or chest.state != ChestState.LOCKED:
            await interaction.response.send_message("No active lock.", ephemeral=True)
            return
        if interaction.user.id != chest.owner_id:
            await interaction.response.send_message("Someone else is picking this lock!", ephemeral=True)
            return
        uid = interaction.user.id
        if uid not in view.pin_selections:
            view.pin_selections[uid] = [None] * chest.pin_count
        view.pin_selections[uid][self.pin_index] = int(self.values[0])

        # Rebuild to show updated selections in embed
        view._rebuild()
        embed = view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


# ---------------------------------------------------------------------------
# Chest view — single view that adapts to chest state
# ---------------------------------------------------------------------------

class ChestView(discord.ui.View):
    """Manages the entire chest interface: claim, pick, result."""

    def __init__(self, cog: "TreasureCog"):
        super().__init__(timeout=3600)
        self.cog = cog
        self.pin_selections: dict[int, list[int | None]] = {}
        self.message: discord.Message | None = None
        self._last_result_text: str | None = None
        self._rebuild()

    def _rebuild(self):
        """Rebuild components based on current chest state."""
        self.clear_items()
        chest = self.cog.treasure._chest
        if chest is None:
            return

        if chest.state == ChestState.AVAILABLE:
            btn = discord.ui.Button(
                label="Claim Lock", style=discord.ButtonStyle.success,
                emoji="🔓", row=0,
            )
            btn.callback = self._claim_callback
            self.add_item(btn)

        elif chest.state == ChestState.LOCKED:
            owner_id = chest.owner_id
            current_pins = self.pin_selections.get(owner_id, [None] * chest.pin_count)

            for i in range(chest.pin_count):
                val = current_pins[i] if i < len(current_pins) else None
                self.add_item(_PinSelect(i, row=i, current_value=val))

            submit_row = chest.pin_count
            submit_btn = discord.ui.Button(
                label="Submit Guess", style=discord.ButtonStyle.success,
                emoji="✅", row=submit_row,
            )
            submit_btn.callback = self._submit_callback
            self.add_item(submit_btn)

            give_up_btn = discord.ui.Button(
                label="Give Up", style=discord.ButtonStyle.secondary,
                emoji="🏳️", row=submit_row,
            )
            give_up_btn.callback = self._give_up_callback
            self.add_item(give_up_btn)

    def build_embed(self) -> discord.Embed:
        """Build embed reflecting current chest state."""
        chest = self.cog.treasure._chest
        if chest is None:
            return discord.Embed(
                title="🧰 No Active Chest",
                description="There is no treasure chest right now.",
                color=discord.Color.dark_gray(),
            )

        if chest.state == ChestState.AVAILABLE:
            is_rare = chest.pin_count >= LOCK_PIN_COUNT_ITEM_CHEST
            if is_rare:
                title = "🧰 RARE Treasure Chest!"
                reward_range = f"⭐ **Reward:** {TREASURE_REWARD_MIN_RARE}-{TREASURE_REWARD_MAX_RARE} stars"
                lock_info = f"🔒 **Lock:** {chest.pin_count} pins (each {LOCK_PIN_MIN}-{LOCK_PIN_MAX}) — harder lock!"
            else:
                title = "🧰 Treasure Chest!"
                reward_range = f"⭐ **Reward:** {TREASURE_REWARD_MIN}-{TREASURE_REWARD_MAX} stars"
                lock_info = f"🔒 **Lock:** {chest.pin_count} pins (each {LOCK_PIN_MIN}-{LOCK_PIN_MAX})"

            desc = (
                "A locked treasure chest has appeared!\n\n"
                f"{lock_info}\n"
                f"{reward_range}\n\n"
                "Click **Claim Lock** to start picking!"
            )
            embed = discord.Embed(title=title, description=desc, color=discord.Color.gold())
            if self._last_result_text:
                embed.set_footer(text=self._last_result_text)
                self._last_result_text = None
            return embed

        if chest.state == ChestState.LOCKED:
            is_rare = chest.pin_count >= LOCK_PIN_COUNT_ITEM_CHEST
            owner_pins = self.pin_selections.get(chest.owner_id, [None] * chest.pin_count)
            pin_display = "  ".join(
                f"**[{p}]**" if p is not None else "[ ? ]"
                for p in owner_pins
            )

            desc = (
                f"👤 **Picker:** <@{chest.owner_id}>\n"
                f"🎯 **Attempts:** {chest.attempts_left}/{LOCK_ATTEMPTS}\n\n"
                f"Current guess: {pin_display}\n"
            )

            if chest.guess_history:
                desc += "\n📋 **Previous guesses:**\n"
                for guess, exact, misplaced in chest.guess_history[-5:]:
                    guess_str = "  ".join(str(g) for g in guess)
                    desc += f"• `{guess_str}` → 🟩 {exact} exact | 🟨 {misplaced} misplaced\n"

            desc += "\nSelect your pins and click **Submit Guess**!"

            color = discord.Color.teal() if is_rare else discord.Color.orange()
            embed = discord.Embed(title="🔐 Lock Picking", description=desc, color=color)
            if self._last_result_text:
                embed.set_footer(text=self._last_result_text)
                self._last_result_text = None
            return embed

        return discord.Embed(title="🧰 Chest", color=discord.Color.dark_gray())

    # ------------------------------------------------------------------ #
    # Button callbacks
    # ------------------------------------------------------------------ #

    async def _claim_callback(self, interaction: discord.Interaction):
        result = self.cog.treasure.start_pick(interaction.user.id, interaction.channel.id)
        if not result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            return

        chest = self.cog.treasure._chest
        self.pin_selections[interaction.user.id] = [None] * chest.pin_count
        self._rebuild()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _submit_callback(self, interaction: discord.Interaction):
        chest = self.cog.treasure._chest
        if not chest or chest.state != ChestState.LOCKED:
            await interaction.response.send_message("No active lock!", ephemeral=True)
            return
        if interaction.user.id != chest.owner_id:
            await interaction.response.send_message("Not your lock!", ephemeral=True)
            return

        pins = self.pin_selections.get(interaction.user.id, [])
        if len(pins) != chest.pin_count or any(p is None for p in pins):
            await interaction.response.send_message(
                f"Select all {chest.pin_count} pins before submitting!", ephemeral=True,
            )
            return

        result = self.cog.treasure.make_guess(
            user_id=interaction.user.id,
            username=str(interaction.user),
            channel_id=interaction.channel.id,
            guess=list(pins),
        )

        if not result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            return

        if result.opened:
            # Success — show victory embed, disable everything
            embed = discord.Embed(
                title="🎉 Chest Opened!",
                description=result.message,
                color=discord.Color.green(),
            )
            self.clear_items()
            await interaction.response.edit_message(embed=embed, view=self)
            self.cog._chest_view = None
            self.cog._chest_message = None
            self.stop()
            return

        if result.attempts_left <= 0:
            # Lock jammed — chest resets to AVAILABLE
            self.pin_selections.clear()
            self._last_result_text = (
                f"💥 {interaction.user.display_name}'s lock jammed! Chest is up for grabs."
            )
            self._rebuild()
            embed = self.build_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            return

        # Wrong guess, attempts remain — clear pins for next guess
        self._last_result_text = (
            f"❌ Wrong combo! 🟩 {result.exact} exact | 🟨 {result.misplaced} misplaced"
        )
        self.pin_selections[interaction.user.id] = [None] * chest.pin_count
        self._rebuild()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _give_up_callback(self, interaction: discord.Interaction):
        chest = self.cog.treasure._chest
        if not chest or chest.state != ChestState.LOCKED:
            await interaction.response.send_message("No active lock!", ephemeral=True)
            return
        if interaction.user.id != chest.owner_id:
            await interaction.response.send_message("Not your lock!", ephemeral=True)
            return

        self.cog.treasure._reset_lock(reason="give_up")
        self.pin_selections.clear()
        self._last_result_text = f"🏳️ {interaction.user.display_name} gave up. Chest is available!"
        self._rebuild()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class TreasureCog(commands.Cog):
    """Commands for spawning and lock-picking treasure chests."""

    def __init__(self, bot):
        self.bot = bot
        self.treasure = TreasureUseCases()
        self.treasure.set_event_callback(self._on_chest_event)
        self._next_spawn_at: datetime | None = None
        self._monthly_spawn_times: list[datetime] = []
        self._chest_view: ChestView | None = None
        self._chest_message: discord.Message | None = None
        self._schedule_next_spawn()
        self.auto_spawn_check.start()

    def cog_unload(self):
        self.auto_spawn_check.cancel()

    # ------------------------------------------------------------------ #
    # Spawn helpers
    # ------------------------------------------------------------------ #

    async def _spawn_and_announce(self, channel, force: bool = False):
        """Spawn a chest and send the button-based announcement."""
        result = self.treasure.spawn_chest(channel.id, force=force)
        if not result.success:
            return result
        view = ChestView(self)
        embed = view.build_embed()
        msg = await channel.send(embed=embed, view=view)
        view.message = msg
        self._chest_view = view
        self._chest_message = msg
        return result

    def _schedule_next_spawn(self) -> None:
        now = datetime.now()
        if not self._monthly_spawn_times or all(
            target <= now for target in self._monthly_spawn_times
        ):
            self._monthly_spawn_times = self._generate_monthly_spawn_times(now.year, now.month)
            if all(target <= now for target in self._monthly_spawn_times):
                next_year, next_month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
                self._monthly_spawn_times = self._generate_monthly_spawn_times(next_year, next_month)
        self._next_spawn_at = next(
            (target for target in self._monthly_spawn_times if target > now), None,
        )

    def _generate_monthly_spawn_times(self, year: int, month: int) -> list[datetime]:
        last_day = calendar.monthrange(year, month)[1]
        return [
            datetime(
                year=year, month=month, day=random.randint(1, last_day),
                hour=random.randint(0, 23), minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )
        ]

    def _advance_spawn_schedule(self) -> None:
        now = datetime.now()
        self._monthly_spawn_times = [t for t in self._monthly_spawn_times if t > now]
        self._schedule_next_spawn()

    # ------------------------------------------------------------------ #
    # Auto-spawn
    # ------------------------------------------------------------------ #

    @tasks.loop(minutes=1)
    async def auto_spawn_check(self) -> None:
        if TREASURE_ANNOUNCEMENT_CHANNEL_ID == 0:
            return
        if self._next_spawn_at is None:
            self._schedule_next_spawn()
            return
        if datetime.now() < self._next_spawn_at:
            return

        channel = self.bot.get_channel(TREASURE_ANNOUNCEMENT_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(TREASURE_ANNOUNCEMENT_CHANNEL_ID)
            except Exception:
                channel = None

        if channel is not None:
            await self._spawn_and_announce(channel)
        self._advance_spawn_schedule()

    # ------------------------------------------------------------------ #
    # Event callback — updates the button view on timeout/expiry
    # ------------------------------------------------------------------ #

    async def _on_chest_event(self, event: str, chest) -> None:
        if event == "owner_timeout":
            if self._chest_view and self._chest_message:
                self._chest_view.pin_selections.clear()
                self._chest_view._last_result_text = "⌛ Lock timed out and reset — chest is up for grabs!"
                self._chest_view._rebuild()
                embed = self._chest_view.build_embed()
                try:
                    await self._chest_message.edit(embed=embed, view=self._chest_view)
                except Exception:
                    traceback.print_exc()

        elif event == "expired":
            embed = discord.Embed(
                title="🕳️ Chest Vanished",
                description=EXPIRED_MESSAGE,
                color=discord.Color.dark_gray(),
            )
            if self._chest_message:
                try:
                    await self._chest_message.edit(embed=embed, view=None)
                except Exception:
                    traceback.print_exc()
            self._chest_view = None
            self._chest_message = None

    # ------------------------------------------------------------------ #
    # Chest management commands (mod)
    # ------------------------------------------------------------------ #

    @commands.command(name="chest")
    async def chest(self, ctx, action: str = ""):
        """Manage treasure chests. Usage: !chest spawn|status|end"""
        action = (action or "").lower().strip()

        if action in ("spawn", "start"):
            if not ctx.author.guild_permissions.moderate_members:
                await ctx.send("❌ You need moderator permissions to spawn a chest.")
                return
            result = await self._spawn_and_announce(ctx.channel)
            if not result.success:
                await ctx.send(f"❌ {result.message}")
            return

        if action in ("end", "stop"):
            if not ctx.author.guild_permissions.moderate_members:
                await ctx.send("❌ You need moderator permissions to end a chest.")
                return
            result = self.treasure.end_chest()
            if not result.success:
                await ctx.send(f"❌ {result.message}")
                return
            # Clean up the view
            if self._chest_message:
                try:
                    embed = discord.Embed(
                        title="🧹 Chest Removed",
                        description="A moderator removed the chest.",
                        color=discord.Color.dark_gray(),
                    )
                    await self._chest_message.edit(embed=embed, view=None)
                except Exception:
                    pass
            self._chest_view = None
            self._chest_message = None
            await ctx.send("🧹 Chest removed.")
            return

        if action in ("status", "info"):
            result = self.treasure.status()
            await ctx.send(result.message)
            return

        await ctx.send("**Usage:** `!chest spawn` | `!chest status` | `!chest end`")

    # ------------------------------------------------------------------ #
    # Text-based picking (fallback)
    # ------------------------------------------------------------------ #

    @commands.command(name="pick")
    async def pick(self, ctx, *args: str):
        """Lock-pick a treasure chest. Usage: !pick start | !pick <digits>"""
        if not args or args[0].lower() == "start":
            result = self.treasure.start_pick(ctx.author.id, ctx.channel.id)
            if not result.success:
                await ctx.send(f"❌ {result.message}")
                return
            await ctx.send(f"🔐 Lock claimed! Use the button interface or `!pick <digits>` to guess.")
            # Sync the button view
            await self._sync_chest_view(ctx.author.id)
            return

        if args[0].lower() in ("status", "info"):
            result = self.treasure.status()
            await ctx.send(result.message)
            return

        # Parse guess
        if len(args) == 1 and args[0].isdigit():
            raw_digits = [int(ch) for ch in args[0]]
            guess = raw_digits if len(raw_digits) in (3, 4) else []
        else:
            guess = []

        try:
            if not guess:
                guess = [int(x) for x in args]
        except ValueError:
            await ctx.send("❌ Use numbers like: `!pick 1 3 2` or `!pick 132`.")
            return

        result = self.treasure.make_guess(
            user_id=ctx.author.id,
            username=str(ctx.author),
            channel_id=ctx.channel.id,
            guess=guess,
        )

        if not result.success:
            await ctx.send(f"❌ {result.message}")
            return

        if result.opened:
            color = discord.Color.green()
            title = "🎉 Chest Opened!"
        elif result.attempts_left <= 0:
            color = discord.Color.red()
            title = "❌ Lock Jammed!"
        else:
            color = discord.Color.orange()
            title = "🔓 Pick Result"

        await ctx.send(embed=discord.Embed(title=title, description=result.message, color=color))
        # Sync the button view
        await self._sync_chest_view()

    async def _sync_chest_view(self, owner_id: int | None = None):
        """Sync the button-based view with current chest state."""
        if not self._chest_view or not self._chest_message:
            return
        chest = self.treasure._chest
        if chest and owner_id and chest.state == ChestState.LOCKED:
            if owner_id not in self._chest_view.pin_selections:
                self._chest_view.pin_selections[owner_id] = [None] * chest.pin_count
        self._chest_view.pin_selections.clear()
        self._chest_view._rebuild()

        if chest is None:
            # Chest was opened or ended via text
            embed = discord.Embed(
                title="🧰 Chest Resolved",
                description="This chest has been resolved.",
                color=discord.Color.dark_gray(),
            )
            try:
                await self._chest_message.edit(embed=embed, view=None)
            except Exception:
                pass
            self._chest_view = None
            self._chest_message = None
        else:
            embed = self._chest_view.build_embed()
            try:
                await self._chest_message.edit(embed=embed, view=self._chest_view)
            except Exception:
                pass


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(TreasureCog(bot))

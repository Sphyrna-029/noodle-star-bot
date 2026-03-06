"""Treasure chest lock-picking commands cog."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from discord.ext import commands, tasks

from cogs.treasure.constants import (
    EXPIRED_MESSAGE,
    TIMEOUT_MESSAGE,
    TREASURE_ANNOUNCEMENT_CHANNEL_ID,
)
from cogs.treasure.use_cases import TreasureUseCases


class TreasureCog(commands.Cog):
    """Commands for spawning and lock-picking treasure chests."""

    def __init__(self, bot):
        self.bot = bot
        self.treasure = TreasureUseCases()
        self.treasure.set_event_callback(self._on_chest_event)
        self._next_spawn_at: datetime | None = None
        self._schedule_next_spawn()
        self.auto_spawn_check.start()

    def cog_unload(self):
        """Stop background tasks when cog is unloaded."""
        self.auto_spawn_check.cancel()

    def _schedule_next_spawn(self) -> None:
        """Pick a random time for the next daily auto-spawn."""
        now = datetime.now()
        target = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )
        if target <= now:
            target += timedelta(days=1)
        self._next_spawn_at = target

    @tasks.loop(minutes=1)
    async def auto_spawn_check(self) -> None:
        """Auto-spawn one chest per day at a random time."""
        if TREASURE_ANNOUNCEMENT_CHANNEL_ID == 0:
            return

        if self._next_spawn_at is None:
            self._schedule_next_spawn()
            return

        now = datetime.now()
        if now < self._next_spawn_at:
            return

        channel = self.bot.get_channel(TREASURE_ANNOUNCEMENT_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(TREASURE_ANNOUNCEMENT_CHANNEL_ID)
            except Exception:
                channel = None

        if channel is not None:
            result = self.treasure.spawn_chest(channel.id)
            if result.success:
                await channel.send(result.message)

        self._schedule_next_spawn()

    async def _on_chest_event(self, event: str, chest) -> None:
        """Callback for chest events: expired, owner_timeout, opened."""
        channel = self.bot.get_channel(chest.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(chest.channel_id)
            except Exception:
                return

        if event == "owner_timeout":
            await channel.send(TIMEOUT_MESSAGE)
        elif event == "expired":
            await channel.send(EXPIRED_MESSAGE)
        # "opened" is already announced in the pick result message.

    # ------------------------------------------------------------------ #
    # Chest management (mods)
    # ------------------------------------------------------------------ #

    @commands.command(name="chest")
    async def chest(self, ctx, action: str = ""):
        """Manage treasure chests. Usage: !chest spawn|status|end"""
        action = (action or "").lower().strip()

        if action in ("spawn", "start"):
            if not ctx.author.guild_permissions.moderate_members:
                await ctx.send("❌ You need moderator permissions to spawn a chest.")
                return

            result = self.treasure.spawn_chest(ctx.channel.id)
            if not result.success:
                await ctx.send(f"❌ {result.message}")
                return

            await ctx.send(result.message)
            return

        if action in ("end", "stop"):
            if not ctx.author.guild_permissions.moderate_members:
                await ctx.send("❌ You need moderator permissions to end a chest.")
                return

            result = self.treasure.end_chest()
            if not result.success:
                await ctx.send(f"❌ {result.message}")
                return

            await ctx.send("🧹 Chest removed.")
            return

        if action in ("status", "info"):
            result = self.treasure.status()
            await ctx.send(result.message)
            return

        await ctx.send(
            "Usage: `!chest spawn` (mod) | `!chest status` | `!chest end` (mod)"
        )

    # ------------------------------------------------------------------ #
    # Lock-picking
    # ------------------------------------------------------------------ #

    @commands.command(name="pick")
    async def pick(self, ctx, *args: str):
        """Lock-pick a treasure chest. Usage: !pick start | !pick 1 3 2"""
        if not args or args[0].lower() == "start":
            result = self.treasure.start_pick(ctx.author.id, ctx.channel.id)
            if not result.success:
                await ctx.send(f"❌ {result.message}")
                return

            await ctx.send(result.message)
            return

        if args[0].lower() in ("status", "info"):
            result = self.treasure.status()
            await ctx.send(result.message)
            return

        # Interpret args as a guess
        try:
            guess = [int(x) for x in args]
        except ValueError:
            await ctx.send(
                "❌ Invalid guess. Use numbers like: `!pick 1 3 2`."
            )
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

        await ctx.send(result.message)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(TreasureCog(bot))

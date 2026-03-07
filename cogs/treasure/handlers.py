"""Treasure chest lock-picking commands cog."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from cogs.treasure.constants import (
    EXPIRED_MESSAGE,
    TIMEOUT_MESSAGE,
    TREASURE_ANNOUNCEMENT_CHANNEL_ID,
)
from cogs.treasure.use_case import TreasureUseCases


class TreasureCog(commands.Cog):
    """Commands for spawning and lock-picking treasure chests."""

    def __init__(self, bot):
        self.bot = bot
        self.treasure = TreasureUseCases()
        self.treasure.set_event_callback(self._on_chest_event)
        self._next_spawn_at: datetime | None = None
        self._daily_spawn_times: list[datetime] = []
        self._schedule_next_spawn()
        self.auto_spawn_check.start()

    def cog_unload(self):
        """Stop background tasks when cog is unloaded."""
        self.auto_spawn_check.cancel()

    def _schedule_next_spawn(self) -> None:
        """Pick random times for the next two daily auto-spawns."""
        now = datetime.now()

        if not self._daily_spawn_times or all(
            target <= now for target in self._daily_spawn_times
        ):
            target_day = now.date()
            self._daily_spawn_times = self._generate_daily_spawn_times(target_day)
            if all(target <= now for target in self._daily_spawn_times):
                target_day = (now + timedelta(days=1)).date()
                self._daily_spawn_times = self._generate_daily_spawn_times(target_day)

        self._next_spawn_at = next(
            (target for target in self._daily_spawn_times if target > now),
            None,
        )

    def _generate_daily_spawn_times(self, target_day) -> list[datetime]:
        times = [
            datetime(
                year=target_day.year,
                month=target_day.month,
                day=target_day.day,
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            ),
            datetime(
                year=target_day.year,
                month=target_day.month,
                day=target_day.day,
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            ),
        ]
        return sorted(times)

    def _advance_spawn_schedule(self) -> None:
        now = datetime.now()
        self._daily_spawn_times = [
            target for target in self._daily_spawn_times if target > now
        ]
        self._schedule_next_spawn()

    def _build_alert_embed(
        self,
        title: str,
        description: str,
        *,
        color: discord.Color,
        emoji: str,
    ) -> discord.Embed:
        return discord.Embed(
            title=f"{emoji} {title}",
            description=description,
            color=color,
        )

    def _build_chest_alert_embed(self) -> discord.Embed:
        return self._build_alert_embed(
            title="Treasure Chest Alert!",
            description=(
                "A **locked treasure chest** appears!\n"
                "Use `!pick start` to claim the lock and begin."
            ),
            color=discord.Color.gold(),
            emoji="🧰",
        )

    def _build_chest_usage_embed(self) -> discord.Embed:
        return self._build_alert_embed(
            title="Chest Commands",
            description=(
                "🧭 **Usage**\n"
                "`!chest spawn` (mod)\n"
                "`!chest status`\n"
                "`!chest end` (mod)"
            ),
            color=discord.Color.blurple(),
            emoji="🧰",
        )

    def _build_pick_embed(
        self,
        title: str,
        description: str,
        *,
        color: discord.Color,
        emoji: str,
    ) -> discord.Embed:
        return self._build_alert_embed(
            title=title,
            description=description,
            color=color,
            emoji=emoji,
        )

    @tasks.loop(minutes=1)
    async def auto_spawn_check(self) -> None:
        """Auto-spawn two chests per day at random times."""
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
                await channel.send(embed=self._build_chest_alert_embed())

        self._advance_spawn_schedule()

    async def _on_chest_event(self, event: str, chest) -> None:
        """Callback for chest events: expired, owner_timeout, opened."""
        channel = self.bot.get_channel(chest.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(chest.channel_id)
            except Exception:
                return

        if event == "owner_timeout":
            await channel.send(
                embed=self._build_alert_embed(
                    title="Lock Reset!",
                    description=TIMEOUT_MESSAGE,
                    color=discord.Color.orange(),
                    emoji="⌛",
                )
            )
        elif event == "expired":
            await channel.send(
                embed=self._build_alert_embed(
                    title="Chest Vanished",
                    description=EXPIRED_MESSAGE,
                    color=discord.Color.dark_gray(),
                    emoji="🕳️",
                )
            )
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

            await ctx.send(embed=self._build_chest_alert_embed())
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

        await ctx.send(embed=self._build_chest_usage_embed())

    # ------------------------------------------------------------------ #
    # Lock-picking
    # ------------------------------------------------------------------ #

    @commands.command(name="pick")
    async def pick(self, ctx, *args: str):
        """Lock-pick a treasure chest. Usage: !pick start | !pick 1 3 2"""
        if not args or args[0].lower() == "start":
            result = self.treasure.start_pick(ctx.author.id, ctx.channel.id)
            if not result.success:
                await ctx.send(
                    embed=self._build_pick_embed(
                        title="Can't Start Picking",
                        description=result.message,
                        color=discord.Color.red(),
                        emoji="⛔",
                    )
                )
                return

            await ctx.send(
                embed=self._build_pick_embed(
                    title="Lock Claimed!",
                    description=result.message,
                    color=discord.Color.gold(),
                    emoji="🔐",
                )
            )
            return

        if args[0].lower() in ("status", "info"):
            result = self.treasure.status()
            await ctx.send(
                embed=self._build_pick_embed(
                    title="Chest Status",
                    description=result.message,
                    color=discord.Color.blurple(),
                    emoji="🧰",
                )
            )
            return

        # Interpret args as a guess
        try:
            guess = [int(x) for x in args]
        except ValueError:
            await ctx.send(
                embed=self._build_pick_embed(
                    title="Invalid Guess",
                    description="Use numbers like: `!pick 1 3 2`.",
                    color=discord.Color.red(),
                    emoji="❌",
                )
            )
            return

        result = self.treasure.make_guess(
            user_id=ctx.author.id,
            username=str(ctx.author),
            channel_id=ctx.channel.id,
            guess=guess,
        )

        if not result.success:
            await ctx.send(
                embed=self._build_pick_embed(
                    title="Pick Failed",
                    description=result.message,
                    color=discord.Color.red(),
                    emoji="❌",
                )
            )
            return

        await ctx.send(
            embed=self._build_pick_embed(
                title="Pick Result",
                description=result.message,
                color=discord.Color.green(),
                emoji="🔓",
            )
        )


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(TreasureCog(bot))

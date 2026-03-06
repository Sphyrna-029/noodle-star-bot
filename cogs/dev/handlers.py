"""Developer-only commands."""

import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from config.bot import DEV_USER_IDS
from cogs.economy.use_case import EconomyUseCases
from cogs.events.farming_weather import WEATHER_EVENT_CHANCE, FarmingWeatherCog


class DevCog(commands.Cog):
    """Hidden command family for developer utilities."""

    def __init__(self, bot):
        self.bot = bot
        self.economy = EconomyUseCases()

    async def cog_check(self, ctx):
        """Restrict all dev commands to explicit developer IDs."""
        return ctx.author.id in DEV_USER_IDS

    @commands.group(name="dev", hidden=True, invoke_without_command=True)
    async def dev_group(self, ctx):
        """Developer command group."""
        await self._send_private(ctx, "🛠️ Dev commands: `weathertest`, `staractivity`")

    @dev_group.command(name="weathertest", hidden=True)
    async def weather_test(self, ctx):
        """Run farming weather check manually with debug pre-check output."""
        weather_cog = self.bot.get_cog("FarmingWeatherCog")
        if not isinstance(weather_cog, FarmingWeatherCog):
            await self._send_private(ctx, "❌ FarmingWeatherCog is not loaded.")
            return

        users_with_crops = weather_cog._get_users_with_active_farms()
        first_timers = weather_cog._get_first_time_farmers(users_with_crops)
        eligible_crops = weather_cog._count_bonus_eligible_crops(users_with_crops)
        roll_pass = (
            len(first_timers) > 0 or (random.random() <= WEATHER_EVENT_CHANCE)
        ) if users_with_crops else False

        await self._send_private(
            ctx,
            "🧪 Weather debug pre-check:\n"
            f"- users with growing crops: **{len(users_with_crops)}**\n"
            f"- first-time farmers in that set: **{len(first_timers)}**\n"
            f"- crops still eligible for new bonus: **{eligible_crops}**\n"
            f"- trigger roll would pass now: **{roll_pass}** (chance={WEATHER_EVENT_CHANCE})"
        )

        await self._send_private(
            ctx,
            "🧪 Running manual weather check now (dry run; DM preview only; no state changes)...",
        )
        await weather_cog.run_weather_check(announcement_target_user=ctx.author, dry_run=True)
        await self._send_private(
            ctx,
            "✅ Manual weather check finished. No bonuses/flags were consumed; midnight behavior remains unchanged.",
        )

    @dev_group.command(name="staractivity", hidden=True)
    async def star_activity(self, ctx, member: discord.Member, days: int = 7):
        """Show per-day star ledger activity for a user."""
        if member is None:
            await self._send_private(ctx, "❌ You must mention a user.")
            return

        max_days = 30
        if days < 1:
            days = 1
        if days > max_days:
            days = max_days

        end = datetime.now()
        start = end - timedelta(days=days)

        activity = self.economy.get_user_daily_star_activity(member.id, start, end)
        if not activity:
            await self._send_private(
                ctx,
                f"ℹ️ No star ledger activity for {member.mention} in the last {days} day(s).",
            )
            return

        earned_total = sum(day[1] for day in activity)
        lost_total = sum(day[2] for day in activity)
        net_total = sum(day[3] for day in activity)
        volume_total = sum(day[4] for day in activity)

        lines = [
            f"{day}: +{earned} / -{lost} (net {net:+}, vol {volume})"
            for day, earned, lost, net, volume in activity
        ]
        header = (
            f"📊 Star activity for {member.mention} "
            f"(last {days} day(s), {start.date().isoformat()} → {end.date().isoformat()}):"
        )
        totals = (
            f"Totals: +{earned_total} / -{lost_total} "
            f"(net {net_total:+}, vol {volume_total})"
        )
        await self._send_private(ctx, "\n".join([header, totals, *lines]))

    async def _send_private(self, ctx, message: str):
        """Send dev command output privately to the caller via DM."""
        try:
            if ctx.guild and ctx.message:
                await ctx.message.delete()
        except Exception:
            # Ignore missing permissions or already-deleted messages.
            pass

        try:
            await ctx.author.send(message)
        except Exception:
            # Fallback if DMs are disabled.
            await ctx.send("❌ Couldn't DM you. Enable DMs to use private dev commands.")

    @dev_group.error
    async def dev_error(self, ctx, error):
        """Handle access-denied errors quietly with a generic message."""
        if isinstance(error, commands.CheckFailure):
            return
        raise error


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(DevCog(bot))

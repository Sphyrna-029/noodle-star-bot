"""Developer-only commands."""

import random

from discord.ext import commands

from config.bot import DEV_USER_IDS
from cogs.events.farming_weather import WEATHER_EVENT_CHANCE, FarmingWeatherCog


class DevCog(commands.Cog):
    """Hidden command family for developer utilities."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Restrict all dev commands to explicit developer IDs."""
        return ctx.author.id in DEV_USER_IDS

    @commands.group(name="dev", hidden=True, invoke_without_command=True)
    async def dev_group(self, ctx):
        """Developer command group."""
        await self._send_private(ctx, "🛠️ Dev commands: `weathertest`")

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
            "🧪 Running manual weather check now (simulating midnight trigger; event announcement will be DM-only)...",
        )
        await weather_cog.run_weather_check(announcement_target_user=ctx.author)
        await self._send_private(ctx, "✅ Manual weather check finished. Check logs/announcement channel/DM errors.")

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

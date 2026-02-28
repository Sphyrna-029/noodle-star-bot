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
        await ctx.send("🛠️ Dev commands: `weathertest`")

    @dev_group.command(name="weathertest", hidden=True)
    async def weather_test(self, ctx):
        """Run farming weather check manually with debug pre-check output."""
        weather_cog = self.bot.get_cog("FarmingWeatherCog")
        if not isinstance(weather_cog, FarmingWeatherCog):
            await ctx.send("❌ FarmingWeatherCog is not loaded.")
            return

        users_with_crops = weather_cog._get_users_with_active_farms()
        first_timers = weather_cog._get_first_time_farmers(users_with_crops)
        eligible_crops = weather_cog._count_bonus_eligible_crops(users_with_crops)
        roll_pass = (
            len(first_timers) > 0 or (random.random() <= WEATHER_EVENT_CHANCE)
        ) if users_with_crops else False

        await ctx.send(
            "🧪 Weather debug pre-check:\n"
            f"- users with growing crops: **{len(users_with_crops)}**\n"
            f"- first-time farmers in that set: **{len(first_timers)}**\n"
            f"- crops still eligible for new bonus: **{eligible_crops}**\n"
            f"- trigger roll would pass now: **{roll_pass}** (chance={WEATHER_EVENT_CHANCE})"
        )

        await ctx.send("🧪 Running manual weather check now (simulating midnight trigger)...")
        await weather_cog.daily_weather_check()
        await ctx.send("✅ Manual weather check finished. Check logs/announcement channel/DM errors.")

    @dev_group.error
    async def dev_error(self, ctx, error):
        """Handle access-denied errors quietly with a generic message."""
        if isinstance(error, commands.CheckFailure):
            return
        raise error


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(DevCog(bot))

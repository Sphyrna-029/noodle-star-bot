"""Farming weather events - daily random beneficial weather for active farms."""

import random
from datetime import datetime, time

import discord
from discord.ext import commands, tasks

from config.bot import COMMAND_PREFIX
from database.repository import UserRepository


# Weather event chance: 5% per day
WEATHER_EVENT_CHANCE = 0.05

# Weather bonus multiplier (100% boost = 2.0x)
WEATHER_BONUS_MULTIPLIER = 2.0

# Channel ID for weather announcements
#ANNOUNCEMENT_CHANNEL_ID = 1464375861800210688 # noodle-house chan in ZGAF
ANNOUNCEMENT_CHANNEL_ID = 1476611236345942248 # noodle-house chan in ZGAF

# Single weather event
WEATHER_EVENT = {
    "name": "Perfect Weather",
    "emoji": "🌤️",
    "description": "Perfect growing conditions blanket the region!",
}


class FarmingWeatherCog(commands.Cog):
    """Daily weather events for farming with 100% harvest bonus."""

    def __init__(self, bot):
        self.bot = bot
        self.repo = UserRepository()
        self.daily_weather_check.start()

    def cog_unload(self):
        """Stop the task when cog is unloaded."""
        self.daily_weather_check.cancel()

    @tasks.loop(time=time(hour=0, minute=0))  # Run at midnight
    async def daily_weather_check(self):
        """Check daily if weather events should occur for users with active farms."""
        print(f"[{datetime.now()}] Running daily farming weather check...")

        try:
            # Get all users with active farms (have planted crops)
            users_with_crops = self._get_users_with_active_farms()

            if not users_with_crops:
                print("No active farms found.")
                return

            print(f"Found {len(users_with_crops)} users with active farms.")

            # Check for first-time farmers (sneaky bonus!)
            first_timers = self._get_first_time_farmers(users_with_crops)

            # Determine if weather event should happen
            force_event = len(first_timers) > 0  # Force event if any first-timers
            should_trigger = force_event or (random.random() <= WEATHER_EVENT_CHANCE)

            if not should_trigger:
                print("No weather event today.")
                return

            # Weather event triggered!
            if force_event:
                print(f"Weather event triggered for {len(first_timers)} first-time farmer(s)! (Sneaky welcome bonus)")
            else:
                print(f"Weather event triggered: {WEATHER_EVENT['name']} {WEATHER_EVENT['emoji']}")

            # Apply weather bonus to all users with active farms
            blessed_users = []
            for user_id in users_with_crops:
                affected_count = self._apply_weather_bonus(user_id)
                if affected_count > 0:
                    blessed_users.append((user_id, affected_count))

            # Mark first-timers as having received their bonus
            for user_id in first_timers:
                self._mark_first_weather_bonus_used(user_id)

            print(f"Applied weather bonus to {len(blessed_users)} users.")

            # Post announcement in a channel (find the first text channel we can post to)
            if blessed_users:
                await self._post_weather_announcement(blessed_users)

            print("Weather event complete!")

        except Exception as e:
            print(f"Error in daily weather check: {e}")
            if hasattr(self.bot, "report_background_error"):
                await self.bot.report_background_error("farming_weather.daily_weather_check", e)
            import traceback
            traceback.print_exc()

    def _get_users_with_active_farms(self) -> list[int]:
        """Get list of user IDs who have crops currently planted."""
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT user_id
                FROM planted_crops
                WHERE ready_at > ?
                """,
                (datetime.now().isoformat(),),
            )
            return [row[0] for row in cursor.fetchall()]

    def _get_first_time_farmers(self, user_ids: list[int]) -> list[int]:
        """Get users who are first-time farmers (haven't received bonus yet and have crops planted).

        A first-time farmer is someone who:
        1. Has at least 1 plot
        2. Has never received the first weather bonus
        3. Has crops currently growing
        """
        if not user_ids:
            return []

        with self.repo.db.get_cursor() as cursor:
            placeholders = ",".join("?" * len(user_ids))
            cursor.execute(
                f"""
                SELECT user_id
                FROM user_inventory
                WHERE user_id IN ({placeholders})
                  AND farm_plots >= 1
                  AND COALESCE(first_weather_bonus, 0) = 0
                """,
                user_ids,
            )
            return [row[0] for row in cursor.fetchall()]

    def _mark_first_weather_bonus_used(self, user_id: int):
        """Mark that a user has received their first-time weather bonus."""
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_inventory
                SET first_weather_bonus = 1
                WHERE user_id = ?
                """,
                (user_id,),
            )

    def _apply_weather_bonus(self, user_id: int) -> int:
        """Apply weather bonus to all growing crops for a user.

        Returns the number of crops affected.
        """
        with self.repo.db.get_cursor() as cursor:
            # Only apply to crops that are still growing (not ready yet) and don't already have bonus
            cursor.execute(
                """
                UPDATE planted_crops
                SET weather_bonus = ?
                WHERE user_id = ?
                  AND ready_at > ?
                  AND weather_bonus = 1.0
                """,
                (WEATHER_BONUS_MULTIPLIER, user_id, datetime.now().isoformat()),
            )
            return cursor.rowcount

    async def _post_weather_announcement(self, blessed_users: list[tuple[int, int]]):
        """Post a public announcement about the weather event."""
        try:
            # Get the specific channel
            channel = self.bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)

            if not channel:
                print(f"Could not find channel with ID {ANNOUNCEMENT_CHANNEL_ID}.")
                return

            # Build mention string (limit to avoid message too long)
            mentions = []
            total_crops = 0
            for user_id, crop_count in blessed_users[:50]:  # Limit to 50 mentions
                mentions.append(f"<@{user_id}>")
                total_crops += crop_count

            if len(blessed_users) > 50:
                mentions.append(f"...and {len(blessed_users) - 50} more!")

            embed = discord.Embed(
                title=f"{WEATHER_EVENT['emoji']} {WEATHER_EVENT['name']} {WEATHER_EVENT['emoji']}",
                description=(
                    f"{WEATHER_EVENT['description']}\n\n"
                    f"🌟 **{len(blessed_users)} farmer{'s' if len(blessed_users) != 1 else ''}** "
                    f"with **{total_crops} growing crop{'s' if total_crops != 1 else ''}** "
                    f"will receive a **100% harvest bonus**!\n\n"
                    f"💚 Your blessed crops will be worth double when you harvest them!"
                ),
                color=discord.Color.green(),
            )

            embed.add_field(
                name="Lucky Farmers",
                value=" ".join(mentions),
                inline=False,
            )

            embed.set_footer(text=f"Use {COMMAND_PREFIX}harvest to collect your bonus crops!")

            await channel.send(embed=embed)
            print(f"Posted weather announcement in {channel.name} ({channel.guild.name})")

        except Exception as e:
            print(f"Error posting weather announcement: {e}")
            if hasattr(self.bot, "report_background_error"):
                await self.bot.report_background_error("farming_weather._post_weather_announcement", e)
            import traceback
            traceback.print_exc()

    @commands.command(name="weathertest", hidden=True)
    async def weather_test(self, ctx):
        """Manual one-off trigger for weather check debugging."""
        dev_user_ids = {249969537066205185, 85538959156850688, 445641460507869185}
        if ctx.author.id not in dev_user_ids:
            await ctx.send("❌ You don't have permission to run this command.")
            return

        await ctx.send("🧪 Running manual weather check now (simulating midnight trigger)...")
        await self.daily_weather_check()
        await ctx.send("✅ Manual weather check finished. Check logs/announcement channel/DM errors.")

    @daily_weather_check.before_loop
    async def before_daily_check(self):
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()
        print("Farming weather system initialized - will check daily at midnight.")


async def setup(bot):
    """Required for cog loading."""
    await bot.add_cog(FarmingWeatherCog(bot))

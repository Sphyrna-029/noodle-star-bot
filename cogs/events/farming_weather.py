"""Farming weather events - daily random beneficial weather for active farms."""

import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from config.bot import COMMAND_PREFIX
from database.repository import UserRepository


# Weather event chance: 5% per day (per event)
WEATHER_EVENT_CHANCE = 0.05

# Channel ID for weather announcements
ANNOUNCEMENT_CHANNEL_ID = 1464375861800210688 # noodle-house chan in ZGAF

# Weather events
PERFECT_WEATHER_EVENT = {
    "name": "Perfect Weather",
    "emoji": "🌤️",
    "description": "Perfect growing conditions blanket the region!",
    "multiplier": 2.0,
}

STARLIT_DEW_EVENT = {
    "name": "Starlit Dew",
    "emoji": "✨",
    "description": "A shimmering dew nourishes the fields overnight.",
    "multiplier": 1.5,
}

BLIGHT_WINDS_EVENT = {
    "name": "Blight Winds",
    "emoji": "🍂",
    "description": "Dry, biting winds sap the vitality of young crops.",
    "multiplier": 0.5,
}

LOCUSTS_EVENT = {
    "name": "Locusts",
    "emoji": "🦗",
    "description": "A ravenous swarm tears through the fields, ruining every growing crop.",
    "effect": "destroy",
}

WEATHER_EVENTS = [
    PERFECT_WEATHER_EVENT,
    STARLIT_DEW_EVENT,
    BLIGHT_WINDS_EVENT,
    LOCUSTS_EVENT,
]


class FarmingWeatherCog(commands.Cog):
    """Daily weather events for farming with 100% harvest bonus."""

    def __init__(self, bot):
        self.bot = bot
        self.repo = UserRepository()
        self._next_weather_check_at: datetime | None = None
        self._daily_weather_times: list[datetime] = []
        self._schedule_next_weather_check()
        self.daily_weather_check.start()

    def cog_unload(self):
        """Stop the task when cog is unloaded."""
        self.daily_weather_check.cancel()

    def _schedule_next_weather_check(self) -> None:
        """Pick a random time for the next daily weather check."""
        now = datetime.now()

        if not self._daily_weather_times or all(
            target <= now for target in self._daily_weather_times
        ):
            target_day = now.date()
            self._daily_weather_times = self._generate_daily_weather_times(target_day)
            if all(target <= now for target in self._daily_weather_times):
                target_day = (now + timedelta(days=1)).date()
                self._daily_weather_times = self._generate_daily_weather_times(target_day)

        self._next_weather_check_at = next(
            (target for target in self._daily_weather_times if target > now),
            None,
        )

    def _generate_daily_weather_times(self, target_day) -> list[datetime]:
        return [
            datetime(
                year=target_day.year,
                month=target_day.month,
                day=target_day.day,
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )
        ]

    def _advance_weather_schedule(self) -> None:
        now = datetime.now()
        self._daily_weather_times = [
            target for target in self._daily_weather_times if target > now
        ]
        self._schedule_next_weather_check()

    @tasks.loop(minutes=1)
    async def daily_weather_check(self):
        """Check daily if weather events should occur for users with active farms."""
        if self._next_weather_check_at is None:
            self._schedule_next_weather_check()
            return

        now = datetime.now()
        if now < self._next_weather_check_at:
            return

        await self.run_weather_check()
        self._advance_weather_schedule()

    async def run_weather_check(
        self,
        announcement_target_user: discord.abc.Messageable | None = None,
        dry_run: bool = False,
    ):
        """Run weather check once.

        Args:
            announcement_target_user: If provided, send event announcement to this user's DMs
                instead of the public announcement channel.
            dry_run: If True, evaluate and announce only; do not mutate database state.
        """
        try:
            # Get all users with active farms (have planted crops)
            users_with_crops = self._get_users_with_active_farms()

            if not users_with_crops:
                print("No active farms found.")
                return

            # Check for first-time farmers (sneaky bonus!)
            first_timers = self._get_first_time_farmers(users_with_crops)

            # Determine if weather event should happen
            force_event = len(first_timers) > 0  # Force event if any first-timers
            if force_event:
                selected_event = PERFECT_WEATHER_EVENT
                print(f"Weather event triggered for {len(first_timers)} first-time farmer(s)! (Sneaky welcome bonus)")
            else:
                rolled_events = [
                    event for event in WEATHER_EVENTS if random.random() <= WEATHER_EVENT_CHANCE
                ]
                if not rolled_events:
                    print("No weather event today.")
                    return
                selected_event = random.choice(rolled_events)
                multiplier = selected_event.get("multiplier")
                if multiplier is not None:
                    print(
                        f"Weather event triggered: {selected_event['name']} {selected_event['emoji']} "
                        f"(x{multiplier})"
                    )
                else:
                    print(f"Weather event triggered: {selected_event['name']} {selected_event['emoji']}")

            # Apply weather effect to all users with active farms
            blessed_users = []
            is_destroy_event = selected_event.get("effect") == "destroy"
            for user_id in users_with_crops:
                if dry_run:
                    affected_count = self._count_user_bonus_eligible_crops(user_id)
                else:
                    if is_destroy_event:
                        affected_count = self._destroy_user_growing_crops(user_id)
                    else:
                        affected_count = self._apply_weather_bonus(user_id, selected_event["multiplier"])
                if affected_count > 0:
                    if not dry_run:
                        self._grant_weather_achievements(user_id, selected_event)
                    blessed_users.append((user_id, affected_count))

            # Mark first-timers as having received their bonus
            if not dry_run:
                for user_id in first_timers:
                    self._mark_first_weather_bonus_used(user_id)

            print(f"Applied weather effect to {len(blessed_users)} users.")

            # Post announcement in a channel (find the first text channel we can post to)
            if blessed_users:
                if announcement_target_user is not None:
                    await self._post_weather_announcement_dm(
                        announcement_target_user, blessed_users, selected_event
                    )
                else:
                    await self._post_weather_announcement(blessed_users, selected_event)

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

    def _apply_weather_bonus(self, user_id: int, multiplier: float) -> int:
        """Apply weather bonus to all growing crops for a user.

        Returns the number of crops affected.
        """
        with self.repo.db.get_cursor() as cursor:
            # Only apply to crops that are still growing (not ready yet)
            cursor.execute(
                """
                UPDATE planted_crops
                SET weather_bonus = ?
                WHERE user_id = ?
                  AND ready_at > ?
                """,
                (multiplier, user_id, datetime.now().isoformat()),
            )
            return cursor.rowcount

    def _grant_weather_achievements(self, user_id: int, weather_event: dict):
        """Increment weather-related achievement progress for one affected user."""
        if weather_event is PERFECT_WEATHER_EVENT:
            perfect_events = self.repo.increment_achievement_progress(
                user_id, "weather_perfect_events", 1
            )
            if perfect_events >= 1:
                self.repo.unlock_achievement(user_id, "sun_blessed")
            return

        if weather_event.get("effect") == "destroy":
            bad_events = self.repo.increment_achievement_progress(
                user_id, "weather_bad_events", 1
            )
            if bad_events >= 1:
                self.repo.unlock_achievement(user_id, "storm_touched")
            return

        if float(weather_event.get("multiplier", 1.0)) < 1.0:
            bad_events = self.repo.increment_achievement_progress(
                user_id, "weather_bad_events", 1
            )
            if bad_events >= 1:
                self.repo.unlock_achievement(user_id, "storm_touched")

    def _destroy_user_growing_crops(self, user_id: int) -> int:
        """Destroy all crops that are still growing for a user.

        Returns the number of crops destroyed.
        """
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM planted_crops
                WHERE user_id = ?
                  AND ready_at > ?
                """,
                (user_id, datetime.now().isoformat()),
            )
            return cursor.rowcount

    def _count_bonus_eligible_crops(self, user_ids: list[int]) -> int:
        """Count crops that could receive a new weather bonus right now."""
        if not user_ids:
            return 0
        with self.repo.db.get_cursor() as cursor:
            placeholders = ",".join("?" * len(user_ids))
            cursor.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM planted_crops
                WHERE user_id IN ({placeholders})
                  AND ready_at > ?
                """,
                [*user_ids, datetime.now().isoformat()],
            )
            row = cursor.fetchone()
            return int(row["count"]) if row and row["count"] is not None else 0

    def _count_user_bonus_eligible_crops(self, user_id: int) -> int:
        """Count crops for one user that could receive a new weather bonus now."""
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM planted_crops
                WHERE user_id = ?
                  AND ready_at > ?
                """,
                (user_id, datetime.now().isoformat()),
            )
            row = cursor.fetchone()
            return int(row["count"]) if row and row["count"] is not None else 0

    async def _post_weather_announcement(
        self, blessed_users: list[tuple[int, int]], weather_event: dict
    ):
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

            if weather_event.get("effect") == "destroy":
                effect_text = "**total crop loss**"
                outcome_text = "completely ruined and have been destroyed"
                color = discord.Color.dark_red()
                event_verb = "suffer"
            else:
                multiplier = weather_event["multiplier"]
                if multiplier >= 1.0:
                    effect_text = f"**{int((multiplier - 1) * 100)}% harvest bonus**"
                    outcome_text = "worth more when you harvest them"
                    color = discord.Color.green()
                else:
                    effect_text = f"**{int((1 - multiplier) * 100)}% harvest penalty**"
                    outcome_text = "worth less when you harvest them"
                    color = discord.Color.red()
                event_verb = "receive"

            embed = discord.Embed(
                title=f"{weather_event['emoji']} {weather_event['name']} {weather_event['emoji']}",
                description=(
                    f"{weather_event['description']}\n\n"
                    f"🌟 **{len(blessed_users)} farmer{'s' if len(blessed_users) != 1 else ''}** "
                    f"with **{total_crops} growing crop{'s' if total_crops != 1 else ''}** "
                    f"will {event_verb} {effect_text}!\n\n"
                    f"💚 Those crops will be {outcome_text}."
                ),
                color=color,
            )

            embed.add_field(
                name="Affected Farmers",
                value=" ".join(mentions),
                inline=False,
            )

            if weather_event.get("effect") == "destroy":
                embed.set_footer(
                    text=f"Replant with {COMMAND_PREFIX}plant <crop> <plot_number> to recover your farm."
                )
            else:
                embed.set_footer(text=f"Use {COMMAND_PREFIX}harvest to collect your bonus crops!")

            await channel.send(embed=embed)
            print(f"Posted weather announcement in {channel.name} ({channel.guild.name})")

        except Exception as e:
            print(f"Error posting weather announcement: {e}")
            if hasattr(self.bot, "report_background_error"):
                await self.bot.report_background_error("farming_weather._post_weather_announcement", e)
            import traceback
            traceback.print_exc()

    async def _post_weather_announcement_dm(
        self,
        user: discord.abc.Messageable,
        blessed_users: list[tuple[int, int]],
        weather_event: dict,
    ):
        """Send weather announcement privately to a specific user."""
        try:
            total_crops = sum(crop_count for _, crop_count in blessed_users)

            if weather_event.get("effect") == "destroy":
                effect_text = "**total crop loss**"
                outcome_text = "completely ruined and have been destroyed"
                color = discord.Color.dark_red()
                event_verb = "suffer"
            else:
                multiplier = weather_event["multiplier"]
                if multiplier >= 1.0:
                    effect_text = f"**{int((multiplier - 1) * 100)}% harvest bonus**"
                    outcome_text = "worth more when you harvest them"
                    color = discord.Color.green()
                else:
                    effect_text = f"**{int((1 - multiplier) * 100)}% harvest penalty**"
                    outcome_text = "worth less when you harvest them"
                    color = discord.Color.red()
                event_verb = "receive"

            embed = discord.Embed(
                title=f"{weather_event['emoji']} {weather_event['name']} {weather_event['emoji']}",
                description=(
                    f"{weather_event['description']}\n\n"
                    f"🌟 **{len(blessed_users)} farmer{'s' if len(blessed_users) != 1 else ''}** "
                    f"with **{total_crops} growing crop{'s' if total_crops != 1 else ''}** "
                    f"will {event_verb} {effect_text}!\n\n"
                    f"💚 Those crops will be {outcome_text}."
                ),
                color=color,
            )

            mentions = [f"<@{user_id}>" for user_id, _ in blessed_users[:50]]
            if len(blessed_users) > 50:
                mentions.append(f"...and {len(blessed_users) - 50} more!")

            embed.add_field(name="Affected Farmers", value=" ".join(mentions), inline=False)
            if weather_event.get("effect") == "destroy":
                embed.set_footer(
                    text=f"Replant with {COMMAND_PREFIX}plant <crop> <plot_number> to recover your farm."
                )
            else:
                embed.set_footer(text=f"Use {COMMAND_PREFIX}harvest to collect your bonus crops!")

            await user.send(embed=embed)
        except Exception as e:
            print(f"Error sending DM weather announcement: {e}")
            if hasattr(self.bot, "report_background_error"):
                await self.bot.report_background_error("farming_weather._post_weather_announcement_dm", e)
            import traceback
            traceback.print_exc()

    @daily_weather_check.before_loop
    async def before_daily_check(self):
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()
        print("Farming weather system initialized - will check daily at a random time.")


async def setup(bot):
    """Required for cog loading."""
    await bot.add_cog(FarmingWeatherCog(bot))

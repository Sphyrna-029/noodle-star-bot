"""Custom Bot class for Noodle Star Bot."""

import traceback

import discord
from discord.ext import commands

from config.bot import COMMAND_PREFIX, DEV_USER_IDS
from database.migrations import MigrationManager
from utils.help import NoodleHelpCommand


class NoodleStarBot(commands.Bot):
    """
    Custom Bot class with shared state and initialization.

    Handles:
    - Discord intents configuration
    - Database migration on startup
    - Cog loading
    """

    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)

        # Custom help
        self.help_command = NoodleHelpCommand()
        self.help_command.cog = None

        # List of cogs to load
        self.cog_list = [
            "cogs.events.alien_abduction",
            "cogs.events.farming_weather",
            "cogs.economy.handlers",
            "cogs.gambling.handlers",
            "cogs.mining.handlers",
            "cogs.shop.handlers",
            "cogs.moderator.handlers",
            "cogs.dev.handlers",
            "cogs.fishing.handlers",
            "cogs.farming.handlers",
            "cogs.trading.handlers",
        ]

    async def setup_hook(self):
        """
        Called when the bot is starting up.

        Runs database migrations and loads all cogs.
        """
        # Run database migrations
        print("Running database migrations...")
        migration_manager = MigrationManager()
        applied = migration_manager.run_migrations()

        if applied:
            print(f"Applied {len(applied)} migration(s):")
            for migration in applied:
                print(f"  - {migration}")
        else:
            print("Database is up to date.")

        # Load all cogs
        print("Loading cogs...")
        for cog in self.cog_list:
            try:
                await self.load_extension(cog)
                print(f"  - Loaded {cog}")
            except Exception as e:
                print(f"  - Failed to load {cog}: {e}")

    async def on_ready(self):
        """Called when the bot is connected and ready."""
        print(f"{self.user} has connected to Discord!")
        print("Bot is ready to track noodle stars!")
        print(f"Serving {len(self.guilds)} guild(s)")

    async def report_background_error(self, source: str, error: Exception):
        """DM traceback details for non-command/background failures."""
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        tb_text = "".join(tb_lines)

        # Keep payload under Discord's message limit
        if len(tb_text) > 1600:
            tb_text = tb_text[:1600] + "\n... (truncated)"

        message = f"❌ **Background error in `{source}`:**\n```python\n{tb_text}\n```"

        for user_id in DEV_USER_IDS:
            try:
                user = self.get_user(user_id) or await self.fetch_user(user_id)
                if user:
                    await user.send(message)
            except Exception as dm_error:
                print(f"Failed sending background error DM to {user_id}: {dm_error}")

    async def on_command_error(self, ctx, error):
        """Global error handler - sends traceback to Discord for debugging."""
        # Only show detailed errors to specific users (devs)
        if ctx.author.id not in DEV_USER_IDS:
            return

        # Get the original exception if it's wrapped
        original = getattr(error, "original", error)

        # Format the traceback
        tb_lines = traceback.format_exception(type(original), original, original.__traceback__)
        tb_text = "".join(tb_lines)

        # Truncate if too long for Discord (max 2000 chars)
        if len(tb_text) > 1900:
            tb_text = tb_text[:1900] + "\n... (truncated)"

        # Send to user's DMs (private)
        try:
            await ctx.author.send(
                f"❌ **Error in `{ctx.command}` (from {ctx.guild.name if ctx.guild else 'DM'}):**\n```python\n{tb_text}\n```"
            )
        except discord.Forbidden:
            # Can't DM user, fall back to channel
            await ctx.send(
                f"❌ **Error in `{ctx.command}`:**\n```python\n{tb_text}\n```"
            )

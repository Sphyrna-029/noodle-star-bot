"""Custom Bot class for Noodle Star Bot."""

import discord
from discord.ext import commands

from config.bot import COMMAND_PREFIX
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
            "cogs.economy.handlers",
            "cogs.gambling.handlers",
            "cogs.mining.handlers",
            "cogs.shop.handlers",
            "cogs.moderator.handlers",
            "cogs.fishing.handlers",
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

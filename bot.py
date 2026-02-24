"""Custom Bot class for Noodle Star Bot."""

import discord
from discord.ext import commands

from config import COMMAND_PREFIX
from database.migrations import MigrationManager


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

        # List of cogs to load
        self.cog_list = [
            "cogs.alien_abduction",
            "cogs.economy",
            "cogs.gambling",
            "cogs.mining",
            "cogs.shop",
            "cogs.moderator",
            "cogs.fishing",
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

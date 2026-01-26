"""Entry point for Noodle Star Bot."""

import os
import sys

from bot import NoodleStarBot


def main():
    """Main entry point for the bot."""
    # Get token from environment variable
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set!")
        print("Please set your bot token as an environment variable.")
        sys.exit(1)

    # Create and run bot
    bot = NoodleStarBot()
    bot.run(token)


if __name__ == "__main__":
    main()

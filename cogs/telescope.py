"""Telescope command cog."""
import discord
import random
from discord.ext import commands

from database.repository import UserRepository


class TelescopeCog(commands.Cog):
    """Commands for the telescope functionality."""

    def __init__(self, bot):
        self.bot = bot
        self.user_repo = UserRepository()

    @commands.command(name="telescope")
    async def telescope(self, ctx):
        """View a random 10x10 emoji starfield if you have a telescope in your inventory."""
        # Check if user has a telescope
        user_inventory = self.user_repo.get_user_inventory(ctx.author.id)

        if user_inventory.get("telescope", 0) <= 0:
            await ctx.send(
                f"❌ {ctx.author.mention}, you don't have a telescope in your inventory! "
                f"Use `!store` to purchase one for 200 stars."
            )
            return

        # Generate a random 10x10 starfield
        emojis = ["⭐", "🌟", "✨", "💫", "🌌", "🌠", "☄️", "🪐", "🌌", "🌌"]
        starfield = []

        for _ in range(10):
            row = []
            for _ in range(10):
                row.append(random.choice(emojis))
            starfield.append(" ".join(row))

        # Create embed with the starfield
        embed = discord.Embed(
            title="🔭 Telescope View",
            description="\n".join(starfield),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use !telescope to view the starfield again")

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(TelescopeCog(bot))
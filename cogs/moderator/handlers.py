"""Moderator commands cog."""

import discord
from discord.ext import commands

from cogs.economy.use_case import EconomyUseCases
from utils.checks import is_moderator


class ModeratorCog(commands.Cog):
    """Commands for moderators to manage user stars."""

    def __init__(self, bot):
        self.bot = bot
        self.economy = EconomyUseCases()

    @commands.command(name="addstar")
    @is_moderator()
    async def add_star(self, ctx, member: discord.Member, amount: int = 1):
        """Add noodle stars to a user (Moderator only)"""
        result = self.economy.add_stars(member.id, str(member), amount)

        await ctx.send(
            f"⭐ Added {amount} noodle star(s) to {member.mention}! "
            f"They now have **{result.wallet}** noodle stars!"
        )

    @commands.command(name="removestar")
    @is_moderator()
    async def remove_star(self, ctx, member: discord.Member, amount: int = 1):
        """Remove noodle stars from a user (Moderator only)"""
        result = self.economy.remove_stars(member.id, str(member), amount)

        await ctx.send(
            f"📉 Removed {amount} noodle star(s) from {member.mention}! "
            f"They now have **{result.wallet}** noodle stars!"
        )

    @add_star.error
    @remove_star.error
    async def mod_error(self, ctx, error):
        """Error handler for moderator commands."""
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You need moderator permissions to use this command!")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(ModeratorCog(bot))

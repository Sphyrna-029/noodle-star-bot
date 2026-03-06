"""Economy commands cog."""

from datetime import datetime

import discord
from discord.ext import commands

from cogs.economy.use_cases import EconomyUseCases


class EconomyCog(commands.Cog):
    """Commands for checking and managing star balances."""

    def __init__(self, bot):
        self.bot = bot
        self.economy = EconomyUseCases()

    @commands.command(name="stars")
    async def check_stars(self, ctx, member: discord.Member = None):
        """Check noodle stars for a user"""
        if member is None:
            member = ctx.author

        result = self.economy.get_balance(member.id, str(member))

        await ctx.send(
            f"⭐ {member.mention}'s Noodle Stars:\n"
            f"💰 Wallet: **{result.wallet}** stars\n"
            f"🏦 Bank: **{result.bank}** stars\n"
            f"📊 Total: **{result.total}** stars"
        )

    @commands.command(name="profile", aliases=["achievements", "ach"])
    async def profile(self, ctx, member: discord.Member = None):
        """View your profile with simple achievement progress."""
        if member is None:
            member = ctx.author

        result = self.economy.get_profile(member.id, str(member))
        unlocked = [achievement for achievement in result.achievements if achievement.unlocked]

        embed = discord.Embed(
            title=f"👤 {member.display_name}'s Profile",
            color=discord.Color.teal(),
        )
        embed.add_field(
            name="💰 Balance",
            value=(
                f"Wallet: **{result.wallet}**\n"
                f"Bank: **{result.bank}**\n"
                f"Total: **{result.total}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🏆 Achievements",
            value=f"Unlocked: **{result.unlocked_achievements}/{result.total_achievements}**",
            inline=False,
        )

        if unlocked:
            embed.add_field(
                name="✅ Unlocked",
                value="\n".join(
                    f"{achievement.emoji} **{achievement.name}**"
                    for achievement in unlocked
                ),
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="topstars")
    async def top_stars(self, ctx):
        """Show top 10 users with the most noodle stars."""
        results = self.economy.get_leaderboard(limit=10, ascending=False)

        if not results:
            await ctx.send("No noodle stars have been awarded yet!")
            return

        embed = discord.Embed(title="🌟 Top 10 Good Noodles 🌟", color=discord.Color.gold())

        for i, (username, stars) in enumerate(results, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(name=f"{medal} {username}", value=f"{stars} stars", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="bottomstars")
    async def bottom_stars(self, ctx):
        """Show bottom 5 users with the least noodle stars."""
        results = self.economy.get_leaderboard(limit=5, ascending=True)

        if not results:
            await ctx.send("No noodle stars have been awarded yet!")
            return

        embed = discord.Embed(title="📉 Bottom 10 Noodles 📉", color=discord.Color.red())

        for i, (username, stars) in enumerate(results, 1):
            embed.add_field(name=f"{i}. {username}", value=f"{stars} stars", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="deposit")
    async def deposit(self, ctx, amount: str = ''):
        """Deposit noodle stars into your bank for safekeeping."""
        if amount == '':
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an amount to deposit! "
                f"Usage: `!deposit <amount>` or `!deposit all`"
            )
            return

        result = self.economy.deposit(ctx.author.id, str(ctx.author), amount)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"🏦 {ctx.author.mention} deposited **{result.message.split('**')[1]}** stars into the bank!\n"
            f"💰 Wallet: **{result.wallet}** stars\n"
            f"🏦 Bank: **{result.bank}** stars\n"
            f"📊 Total: **{result.total}** stars"
        )

    @commands.command(name="withdraw")
    async def withdraw(self, ctx, amount: str = ''):
        """Withdraw noodle stars from your bank."""
        if amount == '':
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an amount to withdraw! "
                f"Usage: `!withdraw <amount>` or `!withdraw all`"
            )
            return

        result = self.economy.withdraw(ctx.author.id, str(ctx.author), amount)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"🏦 {ctx.author.mention} withdrew **{result.message.split('**')[1]}** stars from the bank!\n"
            f"💰 Wallet: **{result.wallet}** stars\n"
            f"🏦 Bank: **{result.bank}** stars\n"
            f"📊 Total: **{result.total}** stars"
        )

    @commands.command(name="starstats")
    async def star_stats(self, ctx, period: str | None = None):
        """Show monthly earned stars and more. Usage: !stats [last|YYYY-MM]"""

        if period is None:
            now = datetime.utcnow()
            year, month = now.year, now.month
            earned = self.economy.get_monthly_stars_earned(year, month)
        else:
            period = period.strip().lower()

            if period == "last":
                earned, year, month = self.economy.get_last_month_stars_earned()
            else:
                try:
                    parsed = datetime.strptime(period, "%Y-%m")
                    year, month = parsed.year, parsed.month
                except ValueError:
                    await ctx.send(
                        f"❌ {ctx.author.mention}, invalid period. Use `last` or `YYYY-MM` (example: `2026-01`)."
                    )
                    return

                earned = self.economy.get_monthly_stars_earned(year, month)

        lost = self.economy.get_monthly_stars_lost(year, month)
        economy_stats = self.economy.get_economy_stats()
        total_in_circulation = economy_stats.total_stars if economy_stats.success else 0

        month_label = f"{year}-{month:02d}"
        embed = discord.Embed(
            title=f"📈 ZGAF star stats for {month_label}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="🌟 Stars earned:",
            value=f"**{earned}**",
            inline=False,
        )
        embed.add_field(
            name="📉 Stars lost:",
            value=f"**{lost}**",
            inline=False,
        )
        embed.add_field(
            name="🔄 Stars in circulation:",
            value=f"**{total_in_circulation}**",
            inline=False,
        )

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(EconomyCog(bot))

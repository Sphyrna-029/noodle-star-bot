"""Gambling commands cog."""

import discord
from discord.ext import commands

from cogs.gambling.use_cases import GamblingUseCases


class GamblingCog(commands.Cog):
    """Commands for gambling games."""

    def __init__(self, bot):
        self.bot = bot
        self.gambling = GamblingUseCases()

    @commands.command(name="gamble")
    async def gamble(self, ctx, amount: int = None):
        """Gamble your noodle stars for a chance to win more!"""
        if amount is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify how many stars to gamble! "
                f"Usage: `!gamble <amount>`"
            )
            return

        result = self.gambling.gamble(ctx.author.id, str(ctx.author), amount)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        if result.won:
            await ctx.send(
                f"🎰 {ctx.author.mention} gambled **{amount}** stars and rolled a **{result.roll}**! 🎉\n"
                f"**YOU WIN!** Multiplier: **{result.multiplier}x**\n"
                f"You won **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! ⭐"
            )
        else:
            await ctx.send(
                f"🎰 {ctx.author.mention} gambled **{amount}** stars and rolled a **{result.roll}**... 💔\n"
                f"**YOU LOSE!** You needed a 7!\n"
                f"You lost **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! 😢"
            )

    @commands.command(name="coinflip")
    async def coinflip(self, ctx, amount: int = 0, choice: str = ''):
        """Flip a coin and bet on heads or tails!"""
        if amount is None or choice is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an amount and choice! "
                f"Usage: `!coinflip <amount> <heads/tails>`"
            )
            return

        result = self.gambling.coinflip(ctx.author.id, str(ctx.author), amount, choice)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Normalize choice for display
        choice_display = choice.lower()
        if choice_display == "h":
            choice_display = "heads"
        elif choice_display == "t":
            choice_display = "tails"

        if result.won:
            await ctx.send(
                f"🪙 {ctx.author.mention} bet **{amount}** stars on **{choice_display}**!\n"
                f"The coin landed on... **{result.result.upper()}**! 🎉\n"
                f"**YOU WIN!** You won **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! ⭐"
            )
        else:
            await ctx.send(
                f"🪙 {ctx.author.mention} bet **{amount}** stars on **{choice_display}**!\n"
                f"The coin landed on... **{result.result.upper()}**! 💔\n"
                f"**YOU LOSE!** You lost **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! 😢"
            )

    @commands.command(name="duel")
    async def duel(self, ctx, opponent: discord.Member = None, amount: int = 0):
        """Challenge another user to a dice duel!"""
        if opponent is None or amount is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an opponent and amount! "
                f"Usage: `!duel @user <amount>`"
            )
            return

        # Check if trying to duel a bot
        if opponent.bot:
            await ctx.send(f"❌ {ctx.author.mention}, you can't duel a bot!")
            return

        result = self.gambling.duel(
            ctx.author.id,
            str(ctx.author),
            opponent.id,
            str(opponent),
            amount,
        )

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Send initial duel message
        await ctx.send(
            f"⚔️ **DICE DUEL!** ⚔️\n"
            f"{ctx.author.mention} challenges {opponent.mention} to a duel for **{amount}** stars!\n"
            f"💪 Stamina: **{result.challenger_stamina_before}** → **{result.challenger_stamina_after}** "
            f"(cost **{result.stamina_cost}**)\n\n"
            f"🎲 Rolling..."
        )

        # Determine winner display
        if result.winner_id == ctx.author.id:
            winner = ctx.author
            loser = opponent
        else:
            winner = opponent
            loser = ctx.author

        await ctx.send(
            f"🎲 {ctx.author.mention} rolled **{result.challenger_roll}**\n"
            f"🎲 {opponent.mention} rolled **{result.opponent_roll}**\n\n"
            f"🏆 **{winner.mention} WINS!** 🏆\n"
            f"{winner.mention} won **{amount}** noodle stars from {loser.mention}!\n\n"
            f"{ctx.author.mention}'s balance: **{result.challenger_new_balance}** stars\n"
            f"{opponent.mention}'s balance: **{result.opponent_new_balance}** stars"
        )


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(GamblingCog(bot))

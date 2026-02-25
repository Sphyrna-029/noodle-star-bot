"""Trading commands cog."""

import discord
from discord.ext import commands

from cogs.trading.use_cases import TradeUseCases, TRADE_COUNTDOWN_SECONDS
from cogs.trading.dto import TradeState


class TradingCog(commands.Cog):
    """Commands for player-to-player trading."""

    def __init__(self, bot):
        self.bot = bot
        self.trading = TradeUseCases()
        self.trading.set_trade_callback(self._on_trade_event)

    async def _on_trade_event(
        self,
        event: str,
        proposer_id: int,
        channel_id: int,
        session,
        extra: str = "",
    ) -> None:
        """
        Callback for trade notifications.

        Events: "timeout", "completed", "failed"
        """
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                return

        if event == "timeout":
            embed = discord.Embed(
                title="Trade Expired",
                description=(
                    f"The trade between **{session.proposer_name}** and "
                    f"**{session.opponent_name}** expired (no response)."
                ),
                color=discord.Color.greyple(),
            )
            await channel.send(embed=embed)

        elif event == "completed":
            proposer_gives = self.trading.format_offer(session.proposer_offer)
            opponent_gives = self.trading.format_offer(session.opponent_offer)
            embed = discord.Embed(
                title="Trade Complete!",
                description=(
                    f"**{session.proposer_name}** gave: {proposer_gives}\n"
                    f"**{session.opponent_name}** gave: {opponent_gives}"
                ),
                color=discord.Color.green(),
            )
            await channel.send(embed=embed)

        elif event == "failed":
            embed = discord.Embed(
                title="Trade Failed",
                description=extra or "The trade could not be completed.",
                color=discord.Color.red(),
            )
            await channel.send(embed=embed)

    @commands.command(name="trade")
    async def trade(self, ctx, *, args: str = ""):
        """Trade stars and items with another player. Use `!trade help` for details."""
        parts = args.split() if args else []

        if not parts:
            await self._handle_help(ctx)
            return

        action = parts[0].lower()

        if action == "help":
            await self._handle_help(ctx)
        elif action == "accept":
            await self._handle_accept(ctx)
        elif action == "cancel":
            await self._handle_cancel(ctx)
        else:
            await self._handle_propose(ctx, parts)

    async def _handle_help(self, ctx):
        """Send the trade help embed."""
        embed = discord.Embed(
            title="Trading Help",
            description="Trade stars and items with other players.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Propose a trade",
            value=(
                "`!trade @user <your offer> for <their offer>`\n"
                "Example: `!trade @Bob 50 stars 1 sword for 2 helmet`"
            ),
            inline=False,
        )
        embed.add_field(
            name="One-sided gift",
            value=(
                "Omit `for` to offer a gift (opponent still must accept).\n"
                "Example: `!trade @Bob 100 stars`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Accept / Cancel",
            value=(
                "`!trade accept` — accept a trade sent to you\n"
                "`!trade cancel` — cancel your current trade"
            ),
            inline=False,
        )
        embed.add_field(
            name="How it works",
            value=(
                "1. You propose a trade to another player.\n"
                "2. They have **60 seconds** to accept or it expires.\n"
                "3. After accepting, there's a **10-second countdown** "
                "where either side can still cancel.\n"
                "4. The trade executes automatically after the countdown."
            ),
            inline=False,
        )
        embed.add_field(
            name="Tradeable items",
            value=(
                "Stars, helmets, swords, potatoes, golden mushrooms, "
                "gold pickaxes, and all bait types. "
                "Use the same names as the `!store`."
            ),
            inline=False,
        )
        embed.set_footer(text="You can only be in one trade at a time.")
        await ctx.send(embed=embed)

    async def _handle_propose(self, ctx, parts: list[str]):
        """Handle a trade proposal."""
        # First arg should be a mention
        if not ctx.message.mentions:
            await ctx.send(
                "You must mention a user to trade with. "
                "Usage: `!trade @user [items] for [items]`"
            )
            return

        opponent = ctx.message.mentions[0]

        if opponent.bot:
            await ctx.send("You can't trade with a bot.")
            return

        # Remove the mention from the args to get the offer tokens
        # The mention could be in various formats: <@id>, <@!id>
        offer_args = []
        skip_next = False
        for part in parts:
            if skip_next:
                skip_next = False
                continue
            # Skip the mention token(s)
            if part.startswith("<@") and part.endswith(">"):
                continue
            # Skip @username style mentions in non-Discord contexts
            if part.startswith("@"):
                continue
            offer_args.append(part)

        result = self.trading.propose_trade(
            proposer_id=ctx.author.id,
            proposer_name=str(ctx.author),
            opponent_id=opponent.id,
            opponent_name=str(opponent),
            channel_id=ctx.channel.id,
            args=offer_args,
        )

        if not result.success:
            await ctx.send(f"{ctx.author.mention}, {result.message}")
            return

        session = result.session
        if session is None:
            return await ctx.send(f"{ctx.author.mention}, an error occurred while creating the trade session.")

        proposer_gives = self.trading.format_offer(session.proposer_offer)
        opponent_gets = self.trading.format_offer(session.opponent_offer)

        embed = discord.Embed(
            title="Trade Proposal",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name=f"{session.proposer_name} gives",
            value=proposer_gives,
            inline=True,
        )
        embed.add_field(
            name=f"{session.opponent_name} gives",
            value=opponent_gets,
            inline=True,
        )
        embed.set_footer(
            text=f"{opponent.display_name}, type !trade accept or !trade cancel (60s timeout)"
        )

        await ctx.send(
            f"{opponent.mention}, you have a trade offer!",
            embed=embed,
        )

    async def _handle_accept(self, ctx):
        """Handle accepting a trade."""
        result = self.trading.accept_trade(ctx.author.id, str(ctx.author))

        if not result.success:
            await ctx.send(f"{ctx.author.mention}, {result.message}")
            return

        session = result.session
        if session is None:
            return await ctx.send(f"{ctx.author.mention}, an error occurred while creating the trade session.")

        proposer_gives = self.trading.format_offer(session.proposer_offer)
        opponent_gives = self.trading.format_offer(session.opponent_offer)

        embed = discord.Embed(
            title="Trade Accepted — Countdown Started!",
            description=(
                f"**{session.proposer_name}** gives: {proposer_gives}\n"
                f"**{session.opponent_name}** gives: {opponent_gives}\n\n"
                f"Trade executes in **{TRADE_COUNTDOWN_SECONDS} seconds**.\n"
                f"Either party can `!trade cancel` to abort."
            ),
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

    async def _handle_cancel(self, ctx):
        """Handle cancelling a trade."""
        result = self.trading.cancel_trade(ctx.author.id)

        if not result.success:
            await ctx.send(f"{ctx.author.mention}, {result.message}")
            return

        session = result.session
        if session is None:
            return await ctx.send(f"{ctx.author.mention}, an error occurred while cancelling the trade.")

        embed = discord.Embed(
            title="Trade Cancelled",
            description=(
                f"The trade between **{session.proposer_name}** and "
                f"**{session.opponent_name}** has been cancelled by "
                f"**{ctx.author}**."
            ),
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(TradingCog(bot))

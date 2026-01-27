"""Fishing commands cog."""

import discord
from discord.ext import commands

from config import FISHING_BAIT_TIERS
from services.fishing import FishingService, FishingState, get_fishing_conditions


class FishingCog(commands.Cog):
    """Commands for the fishing minigame."""

    def __init__(self, bot):
        self.bot = bot
        self.fishing = FishingService()
        # Set up the bite notification callback
        self.fishing.set_bite_callback(self._on_bite)

    async def _on_bite(
        self,
        user_id: int,
        channel_id: int,
        pull_window: int,
    ) -> None:
        """
        Callback for bite notifications.

        pull_window: seconds remaining, or -1 if fish escaped
        """
        # Try to resolve the user first
        user = self.bot.get_user(user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                return

        # Try to get the channel from cache; if missing, attempt fetch
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                channel = None

        # Prepare messages
        if pull_window == -1:
            msg = (
                f"🐟💨 {user.mention}, the fish got away! "
                f"You didn't pull in time. Your line snapped."
            )
        else:
            msg = (
                f"🎣 **{user.mention}, you feel a tug!** "
                f"Type `!pull` within **{pull_window} seconds**!"
            )

        # Send to channel if available, otherwise DM the user
        try:
            if channel is not None:
                await channel.send(msg)
            else:
                # Fallback to DM
                try:
                    await user.send(msg)
                except Exception:
                    # If DM fails, give up silently
                    return
        except Exception:
            # Don't let callback exceptions crash the service
            return

    @commands.command(name="fish")
    async def fish(self, ctx, bait: str = None):
        """Cast your fishing line and wait for a bite.

        Usage:
        - `!fish` - Auto-selects bait if you only have one type
        - `!fish <bait>` - Use specific bait (worm, herring, sturgeon)
        """
        result = await self.fishing.cast_line(
            ctx.author.id,
            str(ctx.author),
            ctx.channel.id,
            bait_type=bait,
        )

        if not result.success:
            await ctx.send(f"🎣 {ctx.author.mention}, {result.message}")
            return

        await ctx.send(f"🎣 {ctx.author.mention}, {result.message}")

    @commands.command(name="pull")
    async def pull(self, ctx):
        """Pull your fishing line when you feel a tug!"""
        result = self.fishing.pull_line(ctx.author.id, str(ctx.author))

        if not result.success:
            await ctx.send(f"🎣 {ctx.author.mention}, {result.message}")
            return

        # Format success message based on rarity
        if result.catch_rarity == "legendary":
            header = "🌟 **LEGENDARY CATCH!** 🌟"
            color = discord.Color.gold()
        elif result.catch_rarity == "rare":
            header = "✨ **RARE CATCH!** ✨"
            color = discord.Color.blue()
        else:
            header = "🎣 **You caught something!**"
            color = discord.Color.green()

        embed = discord.Embed(title=header, color=color)

        if result.stars_earned > 0:
            embed.description = (
                f"{ctx.author.mention} caught a {result.catch_emoji} **{result.catch_name}**!\n\n"
                f"You earned **{result.stars_earned}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars"
            )
        else:
            # Junk item
            embed.description = (
                f"{ctx.author.mention} caught a {result.catch_emoji} **{result.catch_name}**!\n\n"
                f"*It's worthless junk... but at least you caught something!*\n"
                f"Balance: **{result.new_balance}** stars"
            )

        await ctx.send(embed=embed)

    @commands.command(name="fishing")
    async def fishing_status(self, ctx):
        """Check your current fishing status."""
        status = self.fishing.get_status(ctx.author.id, str(ctx.author))

        embed = discord.Embed(
            title=f"🎣 {ctx.author.display_name}'s Fishing Status",
            color=discord.Color.blue(),
        )

        # Show vague conditions hint
        embed.description = f"*{get_fishing_conditions()}*"

        # Show available bait
        available_baits = self.fishing.get_available_baits(ctx.author.id)
        if available_baits:
            bait_list = []
            for bait_type, count in available_baits:
                info = FISHING_BAIT_TIERS[bait_type]
                bait_list.append(f"{info['emoji']} {info['display_name']} x{count}")
            embed.add_field(
                name="Your Bait",
                value="\n".join(bait_list),
                inline=True,
            )
        else:
            embed.add_field(
                name="Your Bait",
                value="None - buy from `!store`",
                inline=True,
            )

        if status.is_fishing:
            if status.state == FishingState.WAITING:
                embed.add_field(
                    name="Status",
                    value="🎣 Waiting for a bite...",
                    inline=True,
                )
                if status.time_until_bite is not None:
                    # Don't show exact time, just a hint
                    if status.time_until_bite > 60:
                        hint = "Be patient..."
                    elif status.time_until_bite > 10:
                        hint = "Should be soon..."
                    else:
                        hint = "Any moment now!"
                    embed.add_field(
                        name="Hint",
                        value=hint,
                        inline=True,
                    )

            elif status.state == FishingState.BITING:
                embed.add_field(
                    name="Status",
                    value="🐟 **A FISH IS BITING!**",
                    inline=True,
                )
                if status.time_until_expires is not None:
                    embed.add_field(
                        name="Time Left",
                        value=f"**{status.time_until_expires}s** to `!pull`!",
                        inline=True,
                    )

            embed.color = discord.Color.orange()

        else:
            embed.add_field(
                name="Status",
                value="Not currently fishing",
                inline=True,
            )

            if status.cooldown_remaining is not None and status.cooldown_remaining > 0:
                minutes = status.cooldown_remaining // 60
                seconds = status.cooldown_remaining % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                embed.add_field(
                    name="Cooldown",
                    value=f"Wait **{time_str}** to fish again",
                    inline=True,
                )
                embed.color = discord.Color.red()
            else:
                embed.add_field(
                    name="Ready",
                    value="Use `!fish` to cast your line!",
                    inline=True,
                )
                embed.color = discord.Color.green()

        await ctx.send(embed=embed)

    @commands.command(name="baitshop")
    async def bait_shop(self, ctx):
        """View available bait and their effects."""
        embed = discord.Embed(
            title="🎣 Bait Shop",
            description=f"Buy bait from `!store`, then use `!fish <bait>` to cast\n\n*{get_fishing_conditions()}*",
            color=discord.Color.blue(),
        )

        # Vague descriptors for each bait tier (don't reveal exact numbers)
        bait_descriptions = {
            "worm": {
                "bite": "Quick",
                "window": "Generous",
                "rarity": "Standard",
            },
            "herring": {
                "bite": "Moderate",
                "window": "Tight",
                "rarity": "Improved",
            },
            "sturgeon": {
                "bite": "Very slow",
                "window": "Very tight",
                "rarity": "Excellent",
            },
        }

        for bait_key, bait_info in FISHING_BAIT_TIERS.items():
            desc = bait_descriptions.get(bait_key, {})
            embed.add_field(
                name=f"{bait_info['emoji']} {bait_info['display_name']}",
                value=(
                    f"**Bite speed:** {desc.get('bite', '?')}\n"
                    f"**Reaction window:** {desc.get('window', '?')}\n"
                    f"**Rare catch odds:** {desc.get('rarity', '?')}"
                ),
                inline=True,
            )

        embed.set_footer(text="Better bait costs more, but attracts rarer fish!")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(FishingCog(bot))

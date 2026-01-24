"""Shop commands cog."""

import discord
from discord.ext import commands

from services.shop import ShopService


class ShopCog(commands.Cog):
    """Commands for the store and inventory."""

    def __init__(self, bot):
        self.bot = bot
        self.shop = ShopService()

    @commands.command(name="store")
    async def store(self, ctx):
        """View items available for purchase"""
        embed = discord.Embed(title="🏪 Noodle Star Store", color=discord.Color.gold())
        embed.description = "Use `!buy <item>` to purchase items!"

        items = self.shop.get_items()
        for item in items:
            embed.add_field(
                name=f"{item.emoji} {item.display_name} - {item.price} stars",
                value=item.description,
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, *, item_name: str = None):
        """Buy an item from the store"""
        if item_name is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an item to buy! "
                f"Use `!store` to see available items."
            )
            return

        result = self.shop.buy(ctx.author.id, str(ctx.author), item_name)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"✅ {ctx.author.mention} purchased {result.item_emoji} **{result.item_name}** "
            f"for **{result.price}** stars!\n"
            f"New balance: **{result.new_balance}** stars"
        )

    @commands.command(name="inventory")
    async def inventory(self, ctx, member: discord.Member = None):
        """Check your inventory"""
        if member is None:
            member = ctx.author

        items_list = self.shop.get_inventory_display(member.id)

        embed = discord.Embed(
            title=f"🎒 {member.display_name}'s Inventory",
            color=discord.Color.blue(),
        )

        if items_list:
            embed.description = "\n".join(items_list)
        else:
            embed.description = "*Empty - Visit the !store to buy items!*"

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(ShopCog(bot))

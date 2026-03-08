"""Shop commands cog."""

import discord
from discord.ext import commands

from cogs.shop.use_case import ShopUseCases


class StoreCategoryButton(discord.ui.Button):
    """Button used to switch store category pages."""

    def __init__(self, category: str):
        super().__init__(label=category, style=discord.ButtonStyle.secondary)
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, StoreCategoryView):
            return
        await view.switch_category(interaction, self.category)


class StoreCategoryView(discord.ui.View):
    """Interactive view for browsing shop items by category."""

    def __init__(self, author_id: int, items_by_category: dict[str, list], timeout: float = 180):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.items_by_category = items_by_category
        self.categories = list(items_by_category.keys())
        self.current_category = self.categories[0]

        for category in self.categories:
            self.add_item(StoreCategoryButton(category))
        self._refresh_button_state()

    def _refresh_button_state(self):
        for child in self.children:
            if not isinstance(child, StoreCategoryButton):
                continue
            is_active = child.category == self.current_category
            child.disabled = is_active
            child.style = (
                discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
            )

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🏪 Noodle Star Store", color=discord.Color.gold())
        embed.description = "Use `!buy <item> [quantity]` to purchase items!"
        embed.add_field(name="Category", value=f"**{self.current_category}**", inline=False)

        for item in self.items_by_category[self.current_category]:
            embed.add_field(
                name=f"{item.emoji} {item.display_name} - {item.price} stars",
                value=item.description,
                inline=False,
            )
        return embed

    async def switch_category(self, interaction: discord.Interaction, category: str):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the user who opened this store menu can use these buttons.",
                ephemeral=True,
            )
            return

        if category not in self.items_by_category:
            await interaction.response.defer()
            return

        self.current_category = category
        self._refresh_button_state()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class ShopCog(commands.Cog):
    """Commands for the store and inventory."""

    def __init__(self, bot):
        self.bot = bot
        self.shop = ShopUseCases()

    @commands.command(name="store")
    async def store(self, ctx):
        """View items available for purchase"""
        items_by_category = self.shop.get_items_by_category()
        if not items_by_category:
            await ctx.send("❌ The store is currently empty.")
            return

        view = StoreCategoryView(ctx.author.id, items_by_category)
        await ctx.send(embed=view.build_embed(), view=view)

    @commands.command(name="buy")
    async def buy(self, ctx, *, item_name: str = ''):
        """Buy an item from the store (usage: !buy <item> [quantity])."""
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

        purchased_item = (
            result.item_name if result.quantity == 1 else f"{result.item_name} x{result.quantity}"
        )
        message = (
            f"✅ {ctx.author.mention} purchased {result.item_emoji} "
            f"**{purchased_item}** "
            f"for **{result.price}** stars!\n"
            f"New balance: **{result.new_balance}** stars"
        )
        if result.item_name == "Bank Insurance":
            message += (
                "\nUse `!inventory` to track remaining uses. "
                "A use is consumed only when it blocks bank loss."
            )
        await ctx.send(message)

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

    @commands.command(name="telescope")
    async def telescope(self, ctx):
        """View a random 10x10 starfield using your telescope"""
        # Check if user has telescope in inventory
        inventory = self.shop.get_inventory(ctx.author.id)
        if inventory.get("telescope", 0) <= 0:
            await ctx.send(
                f"❌ {ctx.author.mention}, you don't have a telescope! "
                f"Purchase one from the store with `!store` and `!buy telescope`"
            )
            return

        # Generate a 10x10 starfield
        import random

        # Star emojis to use for the starfield
        star_emojis = ["⭐", "✨", "🌟", "🌌", "🪐", "🌙", "🌕", "🌖", "🌗", "🌘"]

        # Create 10x10 grid
        starfield = []
        for i in range(10):
            row = ""
            for j in range(10):
                row += random.choice(star_emojis)
            starfield.append(row)

        # Create embed with starfield
        embed = discord.Embed(
            title="🔭 Telescope View",
            description="\n".join(starfield),
            color=discord.Color.blue()
        )

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(ShopCog(bot))

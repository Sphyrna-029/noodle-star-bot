"""Shop commands cog."""

import discord
from discord.ext import commands

from cogs.locations.check import require_location
from cogs.shop.use_case import ShopUseCases


# ---------------------------------------------------------------------------
# Buy confirmation view — quantity buttons for a selected item
# ---------------------------------------------------------------------------

class BuyItemView(discord.ui.View):
    """View for confirming a single item purchase."""

    def __init__(self, author_id: int, username: str, item, shop: ShopUseCases,
                 store_view_factory, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.username = username
        self.item = item
        self.shop = shop
        self.store_view_factory = store_view_factory

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your store menu! Type `!store` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{self.item.emoji} Buy {self.item.display_name}",
            description=f"{self.item.description}\n\nPrice: **{self.item.price}** stars",
            color=discord.Color.green(),
        )
        embed.set_footer(text="Press Buy to purchase, or go back to the store.")
        return embed

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Something went wrong. Try using `!store` again.", ephemeral=True
            )

    @discord.ui.button(label="Buy", style=discord.ButtonStyle.success, row=0)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = self.shop.buy(
            self.author_id, self.username, self.item.key.replace("_", " ")
        )

        if not result.success:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="❌ Purchase Failed",
                    description=result.message,
                    color=discord.Color.red(),
                ),
                view=self,
            )
            return

        success_embed = discord.Embed(
            title="✅ Purchased!",
            description=(
                f"Bought {result.item_emoji} **{result.item_name}** "
                f"for **{result.price}** stars!\n"
                f"New balance: **{result.new_balance}** stars"
            ),
            color=discord.Color.green(),
        )

        post_view = PostPurchaseView(
            self.author_id, self.username, self.item,
            self.shop, self.store_view_factory
        )
        await interaction.response.edit_message(embed=success_embed, view=post_view)

    @discord.ui.button(label="Back to Store", style=discord.ButtonStyle.danger, emoji="◀️", row=0)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = self.store_view_factory()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


# ---------------------------------------------------------------------------
# Post-purchase view — buy more or go back
# ---------------------------------------------------------------------------

class PostPurchaseView(discord.ui.View):
    """View shown after a successful purchase."""

    def __init__(self, author_id: int, username: str, item, shop: ShopUseCases,
                 store_view_factory, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.username = username
        self.item = item
        self.shop = shop
        self.store_view_factory = store_view_factory

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your store menu! Type `!store` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Something went wrong. Try using `!store` again.", ephemeral=True
            )

    @discord.ui.button(label="Buy More", style=discord.ButtonStyle.success, emoji="🔄", row=0)
    async def buy_more(self, interaction: discord.Interaction, button: discord.ui.Button):
        buy_view = BuyItemView(
            self.author_id, self.username, self.item,
            self.shop, self.store_view_factory
        )
        await interaction.response.edit_message(embed=buy_view.build_embed(), view=buy_view)

    @discord.ui.button(label="Back to Store", style=discord.ButtonStyle.danger, emoji="◀️", row=0)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = self.store_view_factory()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


# ---------------------------------------------------------------------------
# Item select dropdown
# ---------------------------------------------------------------------------

class ItemSelect(discord.ui.Select):
    """Dropdown to pick an item from the current category."""

    def __init__(self, items: list):
        options = [
            discord.SelectOption(
                label=f"{item.display_name} - {item.price} stars",
                value=item.key,
                emoji=item.emoji,
                description=item.description[:100],
            )
            for item in items
        ]
        super().__init__(
            placeholder="Select an item to buy...",
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if hasattr(view, "select_item"):
            await view.select_item(interaction, self.values[0])
        else:
            await interaction.response.send_message(
                "This store has expired. Use `!store` to open a new one.", ephemeral=True
            )


# ---------------------------------------------------------------------------
# Store category view (updated with item select)
# ---------------------------------------------------------------------------

class StoreCategoryButton(discord.ui.Button):
    """Button used to switch store category pages."""

    def __init__(self, category: str):
        super().__init__(label=category, style=discord.ButtonStyle.secondary, row=0)
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if hasattr(view, "switch_category"):
            await view.switch_category(interaction, self.category)
        else:
            await interaction.response.send_message(
                "This store has expired. Use `!store` to open a new one.", ephemeral=True
            )


class StoreCategoryView(discord.ui.View):
    """Interactive view for browsing shop items by category."""

    def __init__(self, author_id: int, username: str, items_by_category: dict[str, list],
                 shop: ShopUseCases, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.username = username
        self.items_by_category = items_by_category
        self.shop = shop
        self.categories = list(items_by_category.keys())
        self.current_category = self.categories[0]

        for category in self.categories:
            self.add_item(StoreCategoryButton(category))
        self._add_item_select()
        self._refresh_button_state()

    def _add_item_select(self):
        # Remove existing selects
        for child in list(self.children):
            if isinstance(child, ItemSelect):
                self.remove_item(child)
        items = self.items_by_category.get(self.current_category, [])
        if items:
            self.add_item(ItemSelect(items))

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
        embed.description = "Select an item from the dropdown below to buy, or use `!buy <item> [qty]`."
        embed.add_field(name="Category", value=f"**{self.current_category}**", inline=False)

        for item in self.items_by_category[self.current_category]:
            embed.add_field(
                name=f"{item.emoji} {item.display_name} - {item.price} stars",
                value=item.description,
                inline=False,
            )
        return embed

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Something went wrong. Try using `!store` again.", ephemeral=True
            )

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
        self._add_item_select()
        self._refresh_button_state()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def select_item(self, interaction: discord.Interaction, item_key: str):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the user who opened this store menu can use these buttons.",
                ephemeral=True,
            )
            return

        # Find the item
        item = None
        for cat_items in self.items_by_category.values():
            for i in cat_items:
                if i.key == item_key:
                    item = i
                    break
            if item:
                break

        if item is None:
            await interaction.response.defer()
            return

        # Create a factory that rebuilds this store view
        def store_factory():
            return StoreCategoryView(
                self.author_id, self.username,
                self.items_by_category, self.shop
            )

        buy_view = BuyItemView(
            self.author_id, self.username, item,
            self.shop, store_factory
        )
        await interaction.response.edit_message(embed=buy_view.build_embed(), view=buy_view)


# ---------------------------------------------------------------------------
# Shop cog
# ---------------------------------------------------------------------------

class ShopCog(commands.Cog):
    """Commands for the store and inventory."""

    def __init__(self, bot):
        self.bot = bot
        self.shop = ShopUseCases()

    @commands.command(name="store")
    async def store(self, ctx):
        """View items available for purchase"""
        if not await require_location(ctx, "noodle_town"):
            return
        items_by_category = self.shop.get_items_by_category()
        if not items_by_category:
            await ctx.send("❌ The store is currently empty.")
            return

        view = StoreCategoryView(
            ctx.author.id, str(ctx.author), items_by_category, self.shop
        )
        await ctx.send(embed=view.build_embed(), view=view)

    @commands.command(name="buy")
    async def buy(self, ctx, *, item_name: str = ''):
        """Buy an item from the store (usage: !buy <item> [quantity])."""
        if not await require_location(ctx, "noodle_town"):
            return
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

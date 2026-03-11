"""Shop commands cog."""

import discord
from discord.ext import commands

from cogs.locations.check import require_location
from cogs.shop.use_case import ShopUseCases
from cogs.shop.use_case.sell import SellUseCases
from cogs.shop.resources import get_resource


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
        # Must be in Noodle Town to purchase
        from cogs.locations.use_case import LocationUseCases
        loc = LocationUseCases().get_location(self.author_id)
        if loc != "noodle_town":
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="❌ Purchase Failed",
                    description="You need to be in **Noodle Town** 🏘️ to buy items!\nUse `!t town` to travel there.",
                    color=discord.Color.red(),
                ),
                view=self,
            )
            return

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
            row=2,
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

    def __init__(self, category: str, row: int = 0):
        super().__init__(label=category, style=discord.ButtonStyle.secondary, row=row)
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

        for i, category in enumerate(self.categories):
            self.add_item(StoreCategoryButton(category, row=i // 5))
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
        self.sell_uc = SellUseCases(self.shop.repo)

    @commands.command(name="store")
    async def store(self, ctx):
        """View items available for purchase"""
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

        data = self.shop.get_full_inventory(member.id)
        equipment = data["equipment"]
        items_summary = data["items_summary"]
        bag_count = data["bag_count"]
        bag_capacity = data["bag_capacity"]
        progression = data["progression"]

        # ── Color based on bag fullness ──
        if bag_capacity > 0:
            fill_pct = bag_count / bag_capacity
        else:
            fill_pct = 0
        if fill_pct >= 1.0:
            embed_color = discord.Color.red()
        elif fill_pct >= 0.9:
            embed_color = discord.Color.orange()
        else:
            embed_color = discord.Color.blue()

        embed = discord.Embed(
            title=f"🎒 {member.display_name}'s Inventory",
            color=embed_color,
        )

        # ── Equipment Section ──
        equip_lines = self._build_equipment_lines(equipment, progression)
        if equip_lines:
            embed.add_field(
                name="── EQUIPMENT ──",
                value="\n".join(equip_lines),
                inline=False,
            )

        # ── Inventory Section ──
        category_order = [
            ("mineral", "⛏️ Minerals"),
            ("fish", "🎣 Fish"),
            ("ore", "🚀 Space Ores"),
            ("crop", "🌾 Crops"),
            ("consumable", "🧪 Supplies"),
        ]
        inv_parts = []
        for cat_key, cat_header in category_order:
            cat_items = items_summary.get(cat_key, [])
            if not cat_items:
                continue
            item_strs = []
            for entry in cat_items:
                resource = get_resource(entry["item_key"])
                if resource:
                    emoji = resource.emoji
                    name = resource.display_name
                else:
                    emoji = ""
                    name = entry["item_key"].replace("_", " ").title()
                quality = entry.get("quality")
                if quality and quality != "Normal":
                    item_strs.append(f"{emoji} {name} ({quality}) x{entry['count']}")
                else:
                    item_strs.append(f"{emoji} {name} x{entry['count']}")
            inv_parts.append(f"**{cat_header}**\n{' · '.join(item_strs)}")

        if inv_parts:
            inv_header = f"── INVENTORY ({bag_count}/{bag_capacity}) ──"
            inv_body = "\n\n".join(inv_parts)
            inv_body += f"\n\nBag: {bag_count}/{bag_capacity} slots | Upgrade at `!store`"
            embed.add_field(name=inv_header, value=inv_body, inline=False)
        else:
            inv_header = f"── INVENTORY ({bag_count}/{bag_capacity}) ──"
            embed.add_field(
                name=inv_header,
                value=f"*Empty — gather resources or visit `!store`!*\n\nBag: {bag_count}/{bag_capacity} slots | Upgrade at `!store`",
                inline=False,
            )

        if not equip_lines and not inv_parts:
            embed.description = "*Nothing here yet — visit the `!store` to get started!*"

        await ctx.send(embed=embed)

    @staticmethod
    def _build_equipment_lines(equipment: dict, progression: dict) -> list[str]:
        """Build formatted equipment display lines from equipment dict."""
        # Equipment display mapping: item_key -> (emoji, display_name, format_type)
        # format_type: "permanent", "leveled", "stackable", "uses"
        _EQUIP_MAP = [
            ("gold_pickaxe", "⛏️", "Gold Pickaxe", "permanent"),
            ("telescope", "📷", "Telescope", "permanent"),
            ("rocket_ship", "🚀", "Rocket Ship", "permanent"),
            ("lucky_dice", "🎲", "Lucky Dice", "permanent"),
            ("wooden_sword", "🗡️", "Wooden Sword", "permanent"),
            ("wooden_shield", "🛡️", "Wooden Shield", "permanent"),
            ("leather_vest", "🦺", "Leather Vest", "permanent"),
            ("iron_dagger", "🔪", "Iron Dagger", "permanent"),
            ("growbot", "🤖", "Grow-Bot", "leveled"),
            ("preserver", "🏭", "Preserver", "leveled"),
            ("golden_axe", "🪓", "Golden Axe", "permanent"),
            ("mithril_shield", "🛡️", "Mithril Shield", "permanent"),
            ("bank_insurance", "💸", "Insurance", "stackable"),
            ("bucktail_jig", "🎣", "Bucktail Jig", "stackable"),
            ("rune_fragment", "🪨", "Rune Fragment", "uses"),
            ("fossilized_noodle", "🍜", "Fossilized Noodle", "uses"),
            ("ray_gun", "🔫", "Ray-Gun", "uses"),
            ("star_magnet", "🧲", "Star Magnet", "uses"),
            ("lucky_charm", "🍀", "Lucky Charm", "uses"),
            ("heart_of_leviathan", "💜", "Heart of Leviathan", "uses"),
        ]
        _LEVEL_KEYS = {
            "growbot": "growbot_level",
            "preserver": "preserver_level",
        }

        parts: list[str] = []
        for item_key, emoji, name, fmt in _EQUIP_MAP:
            uses = equipment.get(item_key, 0)
            if uses <= 0:
                continue
            if fmt == "permanent":
                parts.append(f"{emoji} {name}")
            elif fmt == "leveled":
                level_key = _LEVEL_KEYS[item_key]
                level = max(1, progression.get(level_key, 1))
                parts.append(f"{emoji} {name} (Lv.{level})")
            elif fmt == "stackable":
                parts.append(f"{emoji} {name} x{uses}")
            elif fmt == "uses":
                parts.append(f"{emoji} {name} ({uses} uses)")

        # Join into lines of up to ~3 items each for readability
        if not parts:
            return []
        lines = []
        for i in range(0, len(parts), 3):
            lines.append(" · ".join(parts[i:i + 3]))
        return lines

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


    @commands.command(name="sell")
    async def sell(self, ctx, *, args: str = ""):
        """Sell items from your inventory. Usage: !sell <item|category|all> [count]"""
        if not args:
            await ctx.send(
                f"❌ {ctx.author.mention}, usage:\n"
                f"`!sell <item_name>` — Sell all of an item\n"
                f"`!sell <item_name> <count>` — Sell N of an item\n"
                f"`!sell <category>` — Sell all minerals/fish/crops/ores\n"
                f"`!sell all` — Sell everything"
            )
            return

        # Parse optional count from end of args
        parts = args.rsplit(maxsplit=1)
        target = args
        count = 0
        if len(parts) == 2:
            try:
                count = int(parts[1])
                target = parts[0]
            except ValueError:
                pass  # Last word isn't a number, treat whole string as target

        result = self.sell_uc.sell(ctx.author.id, str(ctx.author), target, count)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Build sell receipt embed
        embed = discord.Embed(
            title="💰 Sold!",
            color=discord.Color.gold(),
        )

        # Items sold list
        item_lines = []
        for item_key, display_name, item_count, base_value in result.items_sold:
            resource = get_resource(item_key)
            emoji = resource.emoji if resource else ""
            if item_count == 1:
                item_lines.append(f"{emoji} **{display_name}** — {base_value}⭐")
            else:
                item_lines.append(f"{emoji} **{display_name}** x{item_count} — {base_value}⭐")

        if len(item_lines) > 15:
            shown = item_lines[:15]
            shown.append(f"*...and {len(item_lines) - 15} more*")
            item_lines = shown

        embed.description = "\n".join(item_lines)

        # Bonus breakdown
        bonus_parts = []
        if result.location_bonus_pct > 0:
            bonus_parts.append(f"📍 {result.location_name}: +{result.location_bonus_pct}%")
        else:
            bonus_parts.append(f"📍 {result.location_name}: +0%")
        if result.magnet_bonus_pct > 0:
            bonus_parts.append(
                f"🧲 Star Magnet: +{result.magnet_bonus_pct}% ({result.magnet_uses_left} uses left)"
            )

        if result.bonus_stars > 0:
            bonus_parts.append(f"Bonus: +{result.bonus_stars}⭐")

        embed.add_field(
            name="Breakdown",
            value=(
                f"Base value: **{result.base_total}⭐**\n"
                + "\n".join(bonus_parts)
                + f"\n\n**Total: {result.total_stars}⭐**"
            ),
            inline=False,
        )
        embed.set_footer(text=f"New balance: {result.new_balance} stars")

        await ctx.send(embed=embed)

    @commands.command(name="trash")
    async def trash(self, ctx, *, args: str = ""):
        """Discard junk items from your inventory. Usage: !trash <item> [count]"""
        if not args:
            await ctx.send(
                f"❌ {ctx.author.mention}, usage: `!trash <item_name> [count]`\n"
                f"Discards items without earning stars (for junk like Old Boot, Seaweed, etc.)."
            )
            return

        # Parse optional count
        parts = args.rsplit(maxsplit=1)
        target = args
        count = 0
        if len(parts) == 2:
            try:
                count = int(parts[1])
                target = parts[0]
            except ValueError:
                pass

        result = self.sell_uc.trash(ctx.author.id, str(ctx.author), target, count)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(f"🗑️ {ctx.author.mention}, {result.message}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(ShopCog(bot))

"""Moderator commands cog."""

import discord
from discord.ext import commands

from cogs.combat.constants import COMBAT_ITEMS
from cogs.economy.use_case import EconomyUseCases
from database.repository import UserRepository
from utils.checks import is_moderator

# ---------------------------------------------------------------------------
# Giveable item registry — organised by dropdown category
# ---------------------------------------------------------------------------
# Each entry: (item_key, display_name, emoji, grant_type, default_uses_or_value)
#   grant_type: "inventory" → add_items(), "equipment" → set_equipment()
# For "inventory" items, default_uses_or_value is the base_sell_value.
# For "equipment" items, default_uses_or_value is the default uses count.

_GIVE_ITEMS: dict[str, list[tuple[str, str, str, str, int]]] = {
    "Consumables": [
        ("raw_potato", "Raw Potato", "🥔", "inventory", 0),
        ("golden_mushroom", "Golden Mushroom", "🍄", "inventory", 0),
        ("health_potion", "Health Potion", "❤️‍🩹", "inventory", 0),
        ("stamina_elixir", "Stamina Elixir", "⚗️", "inventory", 0),
        ("minor_stamina_brew", "Minor Stamina Brew", "🧪", "inventory", 0),
        ("stamina_tonic", "Stamina Tonic", "🧴", "inventory", 0),
        ("void_energy_flask", "Void Energy Flask", "⚗️", "inventory", 0),
        ("fertilizer", "Fertilizer", "🧪", "inventory", 0),
        ("water", "Water", "💧", "inventory", 0),
        ("bait_worm", "Worm Bait", "🪱", "inventory", 0),
        ("bait_herring", "Herring Bait", "🐟", "inventory", 0),
        ("bait_sturgeon", "Sturgeon Bait", "🐋", "inventory", 0),
    ],
    "Effect Items": [
        ("ray_gun", "Ray-Gun", "🔫", "equipment", 3),
        ("star_magnet", "Star Magnet", "🧲", "equipment", 20),
        ("lucky_charm", "Lucky Charm", "🍀", "equipment", 50),
        ("rune_fragment", "Rune Fragment", "🔮", "equipment", 30),
        ("fossilized_noodle", "Fossilized Noodle", "🦴", "equipment", 30),
        ("bucktail_jig", "Bucktail Jig", "🎣", "equipment", 1),
        ("heart_of_leviathan", "Heart of Leviathan", "💜", "equipment", 1),
        ("bank_insurance", "Bank Insurance", "💸", "equipment", 1),
    ],
    "Permanent Items": [
        ("gold_pickaxe", "Gold Pickaxe", "⛏️", "equipment", 1),
        ("telescope", "Telescope", "📷", "equipment", 1),
        ("rocket_ship", "Rocket Ship", "🚀", "equipment", 1),
        ("jackhammer", "Jackhammer", "⛏️", "equipment", 1),
        ("lucky_dice", "Lucky Dice", "🎲", "equipment", 1),
    ],
    "Combat T1-3": [],
    "Combat T4-5": [],
    "Combat T6-10": [],
}

# Populate combat gear from COMBAT_ITEMS
for _key, _item in COMBAT_ITEMS.items():
    _entry = (_key, _item.name, _item.emoji, "equipment", 1)
    if _item.tier <= 3:
        _GIVE_ITEMS["Combat T1-3"].append(_entry)
    elif _item.tier <= 5:
        _GIVE_ITEMS["Combat T4-5"].append(_entry)
    else:
        _GIVE_ITEMS["Combat T6-10"].append(_entry)

# Category emojis for the first dropdown
_CATEGORY_EMOJIS = {
    "Consumables": "🧪",
    "Effect Items": "✨",
    "Permanent Items": "🔧",
    "Combat T1-3": "⚔️",
    "Combat T4-5": "🌟",
    "Combat T6-10": "🚀",
}


# ---------------------------------------------------------------------------
# Quantity Modal
# ---------------------------------------------------------------------------

class _QuantityModal(discord.ui.Modal, title="Quantity"):
    quantity = discord.ui.TextInput(
        label="How many?",
        placeholder="1",
        default="1",
        min_length=1,
        max_length=5,
    )

    def __init__(self, target: discord.Member, item_key: str, display_name: str,
                 emoji: str, grant_type: str, default_uses: int, repo: UserRepository):
        super().__init__()
        self.target = target
        self.item_key = item_key
        self.display_name = display_name
        self.item_emoji = emoji
        self.grant_type = grant_type
        self.default_uses = default_uses
        self.repo = repo

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.quantity.value)
        except ValueError:
            await interaction.response.send_message("❌ Enter a valid number.", ephemeral=True)
            return

        if amount < 1 or amount > 9999:
            await interaction.response.send_message("❌ Amount must be between 1 and 9999.", ephemeral=True)
            return

        uid = self.target.id

        if self.grant_type == "equipment":
            # For equipment, amount is added to current uses
            current = self.repo.get_user_equipment(uid).get(self.item_key, 0)
            self.repo.set_equipment(uid, self.item_key, current + amount)
        else:
            # For inventory items, add quantity
            self.repo.add_items(uid, self.item_key, amount, category="consumable")

        await interaction.response.send_message(
            f"✅ Gave **{amount}x** {self.item_emoji} **{self.display_name}** to {self.target.mention}!",
        )


# ---------------------------------------------------------------------------
# Item Select (step 2)
# ---------------------------------------------------------------------------

class _ItemSelect(discord.ui.Select):
    def __init__(self, items: list[tuple[str, str, str, str, int]],
                 target: discord.Member, repo: UserRepository):
        self.target = target
        self.repo = repo
        self._item_map = {item[0]: item for item in items}

        options = [
            discord.SelectOption(label=name, value=key, emoji=emoji)
            for key, name, emoji, _, _ in items
        ]
        super().__init__(placeholder="Select an item...", options=options)

    async def callback(self, interaction: discord.Interaction):
        view: _GiveView = self.view
        if interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your panel!", ephemeral=True)
            return

        key = self.values[0]
        item_key, display_name, emoji, grant_type, default_uses = self._item_map[key]

        modal = _QuantityModal(
            self.target, item_key, display_name, emoji,
            grant_type, default_uses, self.repo,
        )
        await interaction.response.send_modal(modal)


# ---------------------------------------------------------------------------
# Category Select (step 1)
# ---------------------------------------------------------------------------

class _CategorySelect(discord.ui.Select):
    def __init__(self, target: discord.Member, repo: UserRepository):
        self.target = target
        self.repo = repo

        options = [
            discord.SelectOption(
                label=cat, value=cat, emoji=_CATEGORY_EMOJIS.get(cat, "📦"),
                description=f"{len(items)} items",
            )
            for cat, items in _GIVE_ITEMS.items()
            if items
        ]
        super().__init__(placeholder="Select a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        view: _GiveView = self.view
        if interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your panel!", ephemeral=True)
            return

        category = self.values[0]
        items = _GIVE_ITEMS[category]

        # Replace view with item select
        new_view = _GiveView(view.author_id)
        new_view.add_item(_ItemSelect(items, self.target, self.repo))

        embed = discord.Embed(
            title=f"🎁 Give Item — {category}",
            description=f"Select an item to give to {self.target.mention}",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=new_view)


# ---------------------------------------------------------------------------
# Main View
# ---------------------------------------------------------------------------

class _GiveView(discord.ui.View):
    def __init__(self, author_id: int, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class ModeratorCog(commands.Cog):
    """Commands for moderators to manage user stars and items."""

    def __init__(self, bot):
        self.bot = bot
        self.economy = EconomyUseCases()
        self.repo = UserRepository()

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

    @commands.command(name="give")
    @is_moderator()
    async def give_item(self, ctx, member: discord.Member = None):
        """Open the mod give panel to grant items to a player."""
        if not member:
            member = ctx.author

        view = _GiveView(ctx.author.id)
        view.add_item(_CategorySelect(member, self.repo))

        embed = discord.Embed(
            title="🎁 Mod Give Panel",
            description=f"Giving items to {member.mention}\nSelect a category below.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed, view=view)

    @add_star.error
    @remove_star.error
    async def mod_error(self, ctx, error):
        """Error handler for moderator commands."""
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You need moderator permissions to use this command!")
        elif isinstance(error, (commands.MemberNotFound, commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send(f"❌ Usage: `!addstar @user <amount>` or `!removestar @user <amount>`")

    @give_item.error
    async def give_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You need moderator permissions to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Usage: `!give @user` — mention a valid user.")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(ModeratorCog(bot))

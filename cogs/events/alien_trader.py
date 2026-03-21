import asyncio
import random
from dataclasses import dataclass

import discord
from discord.ext import commands, tasks

from cogs.locations.use_case.locations import LocationUseCases
from cogs.shop.resources import get_resource
from database.repository import UserRepository
from utils.star_ledger_context import set_context, reset_context

TRIGGER_CHANCE = 0.006
ACTIVE_DURATION = 120
GRACE_TIMEOUT = 300
WARNING_DELAY = 300
EMBED_COLOR = 0x6B2FA0
WARNING_COLOR = 0x2F3136


@dataclass(frozen=True, slots=True)
class TraderItem:
    key: str
    display_name: str
    emoji: str
    price: int
    global_qty: int
    per_player_cap: int
    category: str


T6_EQUIPMENT = [
    TraderItem("spiker", "Spiker", "\U0001f4cc", 125_000, 1, 1, "equipment"),
    TraderItem("plasma_pistol", "Plasma Pistol", "\U0001f52b", 120_000, 1, 1, "equipment"),
    TraderItem("lunar_barrier", "Lunar Barrier", "\U0001f319", 130_000, 1, 1, "equipment"),
    TraderItem("lunar_exosuit", "Lunar Exosuit", "\U0001f311", 135_000, 1, 1, "equipment"),
]

T7_EQUIPMENT = [
    TraderItem("plasma_rifle", "Plasma Rifle", "\U0001f534", 200_000, 1, 1, "equipment"),
    TraderItem("plasma_repeater", "Plasma Repeater", "\U0001f7e3", 190_000, 1, 1, "equipment"),
    TraderItem("thermal_deflector", "Thermal Deflector", "\U0001f30b", 210_000, 1, 1, "equipment"),
    TraderItem("crimson_exoplate", "Crimson Exoplate", "\U0001f9f2", 220_000, 1, 1, "equipment"),
]

RARE_EFFECT_ITEMS = [
    TraderItem("heart_of_leviathan", "Heart of Leviathan", "\U0001f49c", 50_000, 1, 1, "rare_effect"),
    TraderItem("lucky_charm", "Lucky Charm", "\U0001f340", 35_000, 1, 1, "rare_effect"),
    TraderItem("star_magnet", "Star Magnet", "\U0001f9f2", 25_000, 1, 1, "rare_effect"),
    TraderItem("rune_fragment", "Rune Fragment", "\U0001faa8", 15_000, 1, 1, "rare_effect"),
    TraderItem("fossilized_noodle", "Fossilized Noodle", "\U0001f35c", 20_000, 1, 1, "rare_effect"),
    TraderItem("bucktail_jig", "Bucktail Jig", "\U0001f3a3", 18_000, 1, 1, "rare_effect"),
]

RARE_CONSUMABLES = [
    TraderItem("void_energy_flask", "Void Energy Flask", "\u2697\ufe0f", 4_500, 5, 10, "consumable"),
    TraderItem("bank_insurance", "Bank Insurance", "\U0001f4b8", 8_000, 5, 10, "consumable"),
]

_EQUIPMENT_KEYS = {
    "spiker", "plasma_pistol", "lunar_barrier", "lunar_exosuit",
    "plasma_rifle", "plasma_repeater", "thermal_deflector", "crimson_exoplate",
}

_RARE_EFFECT_KEYS = {
    "heart_of_leviathan", "lucky_charm", "star_magnet",
    "rune_fragment", "fossilized_noodle", "bucktail_jig",
    "bank_insurance",
}


def _roll_stock() -> dict[str, tuple[TraderItem, int]]:
    stock: dict[str, tuple[TraderItem, int]] = {}
    for item in T6_EQUIPMENT:
        if random.random() < 0.30:
            stock[item.key] = (item, item.global_qty)
    for item in T7_EQUIPMENT:
        if random.random() < 0.20:
            stock[item.key] = (item, item.global_qty)
    for item in RARE_EFFECT_ITEMS:
        if random.random() < 0.25:
            stock[item.key] = (item, item.global_qty)
    for item in RARE_CONSUMABLES:
        if random.random() < 0.40:
            stock[item.key] = (item, item.global_qty)
    return stock


def _build_stock_lines(stock: dict[str, tuple[TraderItem, int]]) -> str:
    lines = []
    for key, (item, qty) in stock.items():
        lines.append(
            f"{item.emoji} **{item.display_name}** — {item.price:,} stars (x{qty})"
        )
    return "\n".join(lines) if lines else "*ZYX... HAS NOTHING TODAY.*"


class AlienTradeSelect(discord.ui.Select):
    def __init__(self, stock: dict[str, tuple[TraderItem, int]]):
        options = []
        for key, (item, qty) in stock.items():
            label = f"{item.display_name} — {item.price:,} stars"
            desc = f"{qty} left"
            options.append(discord.SelectOption(
                label=label, value=key, emoji=item.emoji, description=desc,
            ))
        if not options:
            options.append(discord.SelectOption(label="No items", value="__none__"))
        super().__init__(placeholder="Select an item...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_item = self.values[0] if self.values else None
        await interaction.response.defer()


class BuyButton(discord.ui.Button):
    def __init__(self, amount: int, row: int):
        self.amount = amount
        label = f"Buy {amount}x"
        super().__init__(label=label, style=discord.ButtonStyle.green, row=row)

    async def callback(self, interaction: discord.Interaction):
        view: AlienTradeView = self.view
        await view.handle_buy(interaction, self.amount)


class DoneButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Done", style=discord.ButtonStyle.grey, row=2)

    async def callback(self, interaction: discord.Interaction):
        self.view.stop()
        await interaction.response.edit_message(
            content="*ZYX... WAVES FAREWELL.*", view=None, embed=None,
        )


class AlienTradeView(discord.ui.View):
    def __init__(
        self,
        stock: dict[str, tuple[TraderItem, int]],
        player_purchases: dict[str, int],
        user_id: int,
        username: str,
        repo: UserRepository,
        location_uc: LocationUseCases,
    ):
        super().__init__(timeout=GRACE_TIMEOUT)
        self.stock = stock
        self.player_purchases = player_purchases
        self.user_id = user_id
        self.username = username
        self.repo = repo
        self.location_uc = location_uc
        self.selected_item: str | None = None

        self.add_item(AlienTradeSelect(stock))
        self.add_item(BuyButton(1, row=1))
        self.add_item(BuyButton(5, row=1))
        self.add_item(DoneButton())

    def _refresh_select(self):
        for child in self.children:
            if isinstance(child, AlienTradeSelect):
                self.remove_item(child)
                break
        self.add_item(AlienTradeSelect(self.stock))

    async def handle_buy(self, interaction: discord.Interaction, amount: int):
        if self.selected_item is None or self.selected_item == "__none__":
            await interaction.response.send_message(
                "Select an item first.", ephemeral=True,
            )
            return

        key = self.selected_item
        if key not in self.stock:
            await interaction.response.send_message(
                "That item is sold out.", ephemeral=True,
            )
            return

        item, remaining = self.stock[key]
        bought_so_far = self.player_purchases.get(key, 0)
        can_buy = min(amount, remaining, item.per_player_cap - bought_so_far)

        if can_buy <= 0:
            if remaining <= 0:
                await interaction.response.send_message(
                    "Sold out.", ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "You've hit your purchase limit for this item.", ephemeral=True,
                )
            return

        total_cost = item.price * can_buy
        user_data = self.repo.get_user(self.user_id, self.username)
        if user_data.stars < total_cost:
            await interaction.response.send_message(
                f"Not enough stars. You need **{total_cost:,}** but have **{user_data.stars:,}**.",
                ephemeral=True,
            )
            return

        tokens = set_context("alien_trader", f"buy:{key}")
        try:
            self.repo.update_user_stars(
                self.user_id, self.username, user_data.stars - total_cost,
                reason="alien_trader:purchase",
            )
        finally:
            reset_context(tokens)

        if key in _EQUIPMENT_KEYS:
            self.repo.update_user_inventory(self.user_id, key, 1)
        elif key in _RARE_EFFECT_KEYS:
            inventory = self.repo.get_user_inventory(self.user_id)
            current = inventory.get(key, 0)
            self.repo.update_user_inventory(self.user_id, key, current + can_buy)
        else:
            resource = get_resource(key)
            category = resource.category if resource else "consumable"
            for _ in range(can_buy):
                self.repo.add_item(self.user_id, key, category, 0)

        self.stock[key] = (item, remaining - can_buy)
        if self.stock[key][1] <= 0:
            del self.stock[key]

        self.player_purchases[key] = bought_so_far + can_buy
        self._refresh_select()

        await interaction.response.edit_message(
            content=(
                f"Purchased **{can_buy}x {item.emoji} {item.display_name}** "
                f"for **{total_cost:,} stars**."
            ),
            view=self,
        )


class AlienTradeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Trade", emoji="\U0001f47d",
            style=discord.ButtonStyle.green, custom_id="zyx_trade",
        )

    async def callback(self, interaction: discord.Interaction):
        view: AlienAnnouncementView = self.view
        user_id = interaction.user.id
        username = str(interaction.user)

        location = view.location_uc.get_location(user_id)
        if location != "noodle_town":
            await interaction.response.send_message(
                "You must be in **Noodle Town** to trade with Zyx.",
                ephemeral=True,
            )
            return

        if not view.stock:
            await interaction.response.send_message(
                "*ZYX... HAS NOTHING LEFT.*", ephemeral=True,
            )
            return

        player_purchases = view.all_purchases.setdefault(user_id, {})
        trade_view = AlienTradeView(
            stock=view.stock,
            player_purchases=player_purchases,
            user_id=user_id,
            username=username,
            repo=view.repo,
            location_uc=view.location_uc,
        )
        await interaction.response.send_message(
            content=f"\U0001f47d **ZYX** stares at you expectantly.",
            view=trade_view,
            ephemeral=True,
        )


class AlienAnnouncementView(discord.ui.View):
    def __init__(
        self,
        stock: dict[str, tuple[TraderItem, int]],
        repo: UserRepository,
        location_uc: LocationUseCases,
    ):
        super().__init__(timeout=GRACE_TIMEOUT)
        self.stock = stock
        self.repo = repo
        self.location_uc = location_uc
        self.all_purchases: dict[int, dict[str, int]] = {}
        self.add_item(AlienTradeButton())


class AlienTraderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = UserRepository()
        self.location_uc = LocationUseCases()
        self._active = False
        self.alien_check.start()

    def cog_unload(self):
        self.alien_check.cancel()

    def _get_channel_id(self) -> int | None:
        with self.repo.db.get_cursor() as cursor:
            cursor.execute("SELECT value FROM bot_config WHERE key = 'trader_channel_id'")
            row = cursor.fetchone()
            if not row:
                return None
            return int(row["value"])

    @tasks.loop(hours=1)
    async def alien_check(self):
        if self._active:
            return
        if random.random() > TRIGGER_CHANCE:
            return

        channel_id = self._get_channel_id()
        if channel_id is None:
            return
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return

        self._active = True
        try:
            await self._run_appearance(channel)
        finally:
            self._active = False

    @alien_check.before_loop
    async def before_alien_check(self):
        await self.bot.wait_until_ready()

    async def _run_appearance(self, channel: discord.TextChannel):
        warning_embed = discord.Embed(
            title="\u26a1 Strange signals detected...",
            description=(
                "The air crackles with static... "
                "something approaches Noodle Town..."
            ),
            color=WARNING_COLOR,
        )
        await channel.send(embed=warning_embed)
        await asyncio.sleep(WARNING_DELAY)

        stock = _roll_stock()
        if not stock:
            stock = _roll_stock()

        view = AlienAnnouncementView(stock, self.repo, self.location_uc)

        embed = discord.Embed(
            title="\U0001f47d ZYX... HAS ARRIVED.",
            description=(
                "**TRADE... OR ZYX LEAVES. QUICKLY.**\n\n"
                + _build_stock_lines(stock)
            ),
            color=EMBED_COLOR,
        )
        embed.set_footer(text="Departing in 2 minutes | Noodle Town only")

        msg = await channel.send(embed=embed, view=view)

        await asyncio.sleep(ACTIVE_DURATION)

        departure_embed = discord.Embed(
            title="\U0001f47d ZYX... DEPARTS. DO NOT... FOLLOW.",
            color=EMBED_COLOR,
        )
        view.clear_items()
        btn = AlienTradeButton()
        btn.disabled = True
        view.add_item(btn)
        view.stop()
        await msg.edit(embed=departure_embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(AlienTraderCog(bot))

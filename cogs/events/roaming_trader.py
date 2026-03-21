import asyncio
import random
import time
from typing import Optional

import discord
from discord.ext import commands, tasks

from cogs.combat.constants import COMBAT_ITEMS
from cogs.locations.use_case.locations import LocationUseCases
from cogs.shop.resources import get_resource
from database.repository import UserRepository

SPAWN_CHANCE = 0.042
ACTIVE_DURATION = 600
GRACE_SECONDS = 180
EMBED_COLOR = 0xE67E22
PER_PLAYER_CAP = 10

GREETING = "Psst... you look like someone who appreciates quality goods. Step closer, friend."
DEPARTURE = "The Wandering Wok rolls onward... until next time!"

HIGH_AVAIL_ITEMS = [
    {"key": "seaweed", "price": 30, "qty": 20},
    {"key": "bioluminescent_jelly", "price": 400, "qty": 20},
    {"key": "coral_golem", "price": 700, "qty": 20},
]

STANDARD_ITEMS = [
    {"key": "noodle_gem", "price": 500, "qty": 20},
    {"key": "star_fragment", "price": 300, "qty": 20},
    {"key": "adamantium", "price": 400, "qty": 20},
    {"key": "titanium", "price": 250, "qty": 20},
    {"key": "dragonstone", "price": 350, "qty": 20},
    {"key": "emerald", "price": 150, "qty": 20},
    {"key": "mithril", "price": 200, "qty": 20},
    {"key": "coal", "price": 20, "qty": 20},
    {"key": "void_coral", "price": 250, "qty": 20},
    {"key": "golden_fish", "price": 200, "qty": 20},
    {"key": "river_dragon", "price": 300, "qty": 20},
    {"key": "mermaids_pearl", "price": 350, "qty": 20},
    {"key": "salmon", "price": 30, "qty": 20},
    {"key": "trout", "price": 30, "qty": 20},
    {"key": "wheat", "price": 20, "qty": 20},
    {"key": "corn", "price": 20, "qty": 20},
    {"key": "carrot", "price": 25, "qty": 20},
]

EQUIPMENT_ITEMS = [
    {"key": "noodle_gem_katana", "price": 62_500, "qty": 1},
    {"key": "void_reaper", "price": 55_000, "qty": 1},
    {"key": "eternity_bulwark", "price": 60_000, "qty": 1},
    {"key": "darkite_warplate", "price": 70_000, "qty": 1},
]

EQUIPMENT_KEYS = {item["key"] for item in EQUIPMENT_ITEMS}

_active_stock: dict[str, dict] = {}
_active_until: float = 0.0
_player_purchases: dict[int, dict[str, int]] = {}
_open_sessions: set[int] = set()
_announcement_msg: Optional[discord.Message] = None
_announcement_view: Optional["TradeButtonView"] = None


def _roll_stock() -> list[dict]:
    stock = []
    for item in HIGH_AVAIL_ITEMS:
        if random.random() < 0.75:
            stock.append(dict(item))
    for item in STANDARD_ITEMS:
        if random.random() < 0.25:
            stock.append(dict(item))
    for item in EQUIPMENT_ITEMS:
        if random.random() < 0.05:
            stock.append(dict(item))
    if not stock:
        stock.append(dict(random.choice(HIGH_AVAIL_ITEMS)))
    return stock


def _is_active() -> bool:
    return time.time() < _active_until and bool(_active_stock)


def _get_display_name(key: str) -> str:
    res = get_resource(key)
    if res:
        return f"{res.emoji} {res.display_name}"
    ci = COMBAT_ITEMS.get(key)
    if ci:
        return f"{ci.emoji} {ci.name}"
    return key.replace("_", " ").title()


def _get_emoji(key: str) -> str:
    res = get_resource(key)
    if res:
        return res.emoji
    ci = COMBAT_ITEMS.get(key)
    if ci:
        return ci.emoji
    return ""


def _build_announcement_embed() -> discord.Embed:
    embed = discord.Embed(
        title="\U0001f373 The Wandering Wok Has Arrived!",
        description=GREETING,
        color=EMBED_COLOR,
    )
    lines = []
    for key, info in _active_stock.items():
        name = _get_display_name(key)
        lines.append(f"{name} — **{info['price']:,}** \u2b50 (x{info['qty']})")
    embed.add_field(name="Today's Goods", value="\n".join(lines) or "Nothing today!", inline=False)
    remaining = max(0, int(_active_until - time.time()))
    minutes = remaining // 60
    embed.set_footer(text=f"Leaving in {minutes} minutes | Noodle Town only")
    return embed


def _build_departure_embed() -> discord.Embed:
    embed = discord.Embed(
        title="\U0001f373 The Wandering Wok",
        description=DEPARTURE,
        color=EMBED_COLOR,
    )
    return embed


class ItemSelect(discord.ui.Select):
    def __init__(self, stock: dict[str, dict], player_purchases: dict[str, int]):
        options = []
        for key, info in stock.items():
            remaining = info["qty"]
            if remaining <= 0:
                continue
            bought = player_purchases.get(key, 0)
            cap_left = PER_PLAYER_CAP - bought if key not in EQUIPMENT_KEYS else (1 - bought)
            if cap_left <= 0:
                continue
            name = _get_display_name(key)
            desc = f"{info['price']:,} stars | {remaining} left"
            options.append(discord.SelectOption(
                label=name[:100],
                value=key,
                description=desc[:100],
                emoji=_get_emoji(key) or None,
            ))
        if not options:
            options.append(discord.SelectOption(label="Sold out!", value="_sold_out"))
        super().__init__(placeholder="Select an item...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_item = self.values[0] if self.values else None
        await interaction.response.defer()


class TradeSessionView(discord.ui.View):
    def __init__(self, user_id: int, repo: UserRepository, timeout_seconds: float):
        super().__init__(timeout=timeout_seconds)
        self.user_id = user_id
        self.repo = repo
        self.selected_item: Optional[str] = None
        self.message: Optional[discord.Message] = None
        self._rebuild_select()

    def _rebuild_select(self):
        for child in list(self.children):
            if isinstance(child, ItemSelect):
                self.remove_item(child)
        purchases = _player_purchases.get(self.user_id, {})
        select = ItemSelect(_active_stock, purchases)
        self.add_item(select)

    def _build_embed(self, status: str = "") -> discord.Embed:
        embed = discord.Embed(
            title="\U0001f373 Wandering Wok — Your Trade Session",
            color=EMBED_COLOR,
        )
        lines = []
        purchases = _player_purchases.get(self.user_id, {})
        for key, info in _active_stock.items():
            remaining = info["qty"]
            bought = purchases.get(key, 0)
            name = _get_display_name(key)
            lines.append(f"{name} — **{info['price']:,}** \u2b50 (x{remaining}) [bought: {bought}]")
        embed.add_field(name="Stock", value="\n".join(lines) or "Sold out!", inline=False)
        if status:
            embed.add_field(name="Result", value=status, inline=False)
        return embed

    async def _do_buy(self, interaction: discord.Interaction, amount: int):
        if not _is_active() and self.user_id not in _open_sessions:
            await interaction.response.edit_message(
                embed=self._build_embed("The Wandering Wok has left!"),
                view=None,
            )
            return

        key = self.selected_item
        if not key or key == "_sold_out":
            await interaction.response.edit_message(
                embed=self._build_embed("Select an item first!"),
                view=self,
            )
            return

        if key not in _active_stock:
            await interaction.response.edit_message(
                embed=self._build_embed("That item is no longer available."),
                view=self,
            )
            return

        info = _active_stock[key]
        is_equipment = key in EQUIPMENT_KEYS

        purchases = _player_purchases.setdefault(self.user_id, {})
        bought = purchases.get(key, 0)
        per_cap = 1 if is_equipment else PER_PLAYER_CAP
        can_buy_player = per_cap - bought
        can_buy_stock = info["qty"]
        actual = min(amount, can_buy_player, can_buy_stock)

        if actual <= 0:
            reason = "Sold out!" if can_buy_stock <= 0 else "You've hit your purchase limit for this item."
            await interaction.response.edit_message(
                embed=self._build_embed(reason),
                view=self,
            )
            return

        total_cost = info["price"] * actual
        username = str(interaction.user)
        user_data = self.repo.get_user(self.user_id, username)

        if user_data.stars < total_cost:
            await interaction.response.edit_message(
                embed=self._build_embed(
                    f"Not enough stars! Need **{total_cost:,}**, have **{user_data.stars:,}**."
                ),
                view=self,
            )
            return

        if is_equipment:
            if self.repo.has_equipment(self.user_id, key):
                await interaction.response.edit_message(
                    embed=self._build_embed(f"You already own **{_get_display_name(key)}**!"),
                    view=self,
                )
                return
            self.repo.set_equipment(self.user_id, key, 1)
        else:
            res = get_resource(key)
            category = res.category if res else "consumable"
            added_count = 0
            for _ in range(actual):
                if not self.repo.add_item(self.user_id, key, category, info["price"]):
                    break
                added_count += 1
            actual = added_count

        if actual <= 0:
            await interaction.response.edit_message(
                embed=self._build_embed("Your inventory is full!"),
                view=self,
            )
            return

        total_cost = info["price"] * actual
        new_stars = user_data.stars - total_cost
        self.repo.update_user_stars(self.user_id, username, new_stars, reason="wandering_wok:purchase")

        info["qty"] -= actual
        purchases[key] = bought + actual

        name = _get_display_name(key)
        status = f"Bought **{actual}x** {name} for **{total_cost:,}** \u2b50!"
        self._rebuild_select()
        await interaction.response.edit_message(
            embed=self._build_embed(status),
            view=self,
        )

    @discord.ui.button(label="Buy 1x", style=discord.ButtonStyle.green, row=2)
    async def buy_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await self._do_buy(interaction, 1)

    @discord.ui.button(label="Buy 5x", style=discord.ButtonStyle.green, row=2)
    async def buy_five(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await self._do_buy(interaction, 5)

    @discord.ui.button(label="Buy 10x", style=discord.ButtonStyle.green, row=2)
    async def buy_ten(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await self._do_buy(interaction, 10)

    @discord.ui.button(label="Done", style=discord.ButtonStyle.grey, row=2)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        _open_sessions.discard(self.user_id)
        await interaction.response.edit_message(
            embed=self._build_embed("Thanks for shopping! Come again."),
            view=None,
        )
        self.stop()

    async def on_timeout(self):
        _open_sessions.discard(self.user_id)
        if self.message:
            try:
                await self.message.edit(
                    embed=self._build_embed("Session timed out."),
                    view=None,
                )
            except discord.HTTPException:
                pass


class TradeButtonView(discord.ui.View):
    def __init__(self, cog: "RoamingTraderCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="\U0001f6d2 Trade", style=discord.ButtonStyle.primary, custom_id="wandering_wok_trade")
    async def trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_active():
            await interaction.response.send_message(
                "The Wandering Wok has already left!", ephemeral=True
            )
            return

        user_id = interaction.user.id
        location_uc = LocationUseCases()
        if location_uc.get_location(user_id) != "noodle_town":
            await interaction.response.send_message(
                "You need to be in **Noodle Town** to trade with the Wandering Wok!",
                ephemeral=True,
            )
            return

        _open_sessions.add(user_id)
        remaining = max(1, _active_until - time.time() + GRACE_SECONDS)
        view = TradeSessionView(user_id, self.cog.repo, timeout_seconds=remaining)
        embed = view._build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()


class RoamingTraderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = UserRepository()
        self._trader_check.start()

    def cog_unload(self):
        self._trader_check.cancel()

    def _get_channel_id(self) -> Optional[int]:
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)"
            )
            cursor.execute(
                "SELECT value FROM bot_config WHERE key = 'trader_channel_id'"
            )
            row = cursor.fetchone()
            if row and row["value"]:
                return int(row["value"])
        return None

    def _set_channel_id(self, channel_id: int) -> None:
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)"
            )
            cursor.execute(
                "INSERT OR REPLACE INTO bot_config (key, value) VALUES ('trader_channel_id', ?)",
                (str(channel_id),),
            )

    @tasks.loop(minutes=30)
    async def _trader_check(self):
        if _is_active():
            return

        if random.random() > SPAWN_CHANCE:
            return

        channel_id = self._get_channel_id()
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        await self._spawn(channel)

    @_trader_check.before_loop
    async def _before_trader_check(self):
        await self.bot.wait_until_ready()

    async def _spawn(self, channel: discord.TextChannel):
        global _active_stock, _active_until, _player_purchases
        global _announcement_msg, _announcement_view

        stock_list = _roll_stock()
        _active_stock.clear()
        for item in stock_list:
            _active_stock[item["key"]] = {"price": item["price"], "qty": item["qty"]}
        _active_until = time.time() + ACTIVE_DURATION
        _player_purchases.clear()
        _open_sessions.clear()

        embed = _build_announcement_embed()
        view = TradeButtonView(self)
        _announcement_view = view
        _announcement_msg = await channel.send(embed=embed, view=view)

        await asyncio.sleep(ACTIVE_DURATION)
        await self._depart()

    async def _depart(self):
        global _active_stock, _active_until, _announcement_msg, _announcement_view

        _active_until = 0.0

        if _announcement_msg:
            try:
                embed = _build_departure_embed()
                view = TradeButtonView(self)
                for child in view.children:
                    child.disabled = True
                await _announcement_msg.edit(embed=embed, view=view)
            except discord.HTTPException:
                pass
            _announcement_msg = None
            _announcement_view = None

        await asyncio.sleep(GRACE_SECONDS)
        _active_stock.clear()
        _player_purchases.clear()
        _open_sessions.clear()

    @commands.command(name="settrader")
    @commands.has_permissions(manage_guild=True)
    async def set_trader_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel for Wandering Wok announcements."""
        self._set_channel_id(channel.id)
        await ctx.send(f"\U0001f373 Wandering Wok trader channel set to {channel.mention}!")

    @set_trader_channel.error
    async def set_trader_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need **Manage Server** permission to use this command.")


async def setup(bot: commands.Bot):
    await bot.add_cog(RoamingTraderCog(bot))

"""Trading commands cog — button-based UI."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import discord
from discord.ext import commands

from cogs.locations.check import require_location
from cogs.trading.dto import TradeOffer, TradeResult
from cogs.trading.use_case import MAX_TRADE_ITEMS, TradeUseCases

REVIEW_WAIT_SECONDS = 5
TRADE_VIEW_TIMEOUT = 120  # seconds of inactivity before auto-cancel


# ---------------------------------------------------------------------------
# Ephemeral helper views / modals
# ---------------------------------------------------------------------------

class _ItemSelectView(discord.ui.View):
    """Ephemeral dropdown for adding an item to a trade."""

    def __init__(
        self,
        trade_view: TradeView,
        user_id: int,
        available: list[tuple[str, str, str, int]],
    ):
        super().__init__(timeout=30)
        self.trade_view = trade_view
        self.user_id = user_id

        options = []
        for key, name, emoji, count in available[:25]:
            label = f"{name} (\u00d7{count})" if count > 1 else name
            # Emoji may be multi-char (custom); use only standard single-char ones
            opt = discord.SelectOption(label=label, value=key)
            if len(emoji) == 1 or emoji.startswith("<"):
                opt.emoji = emoji
            options.append(opt)

        self._select = discord.ui.Select(
            placeholder="Choose an item\u2026", options=options,
        )
        self._select.callback = self._on_select
        self.add_item(self._select)

    async def _on_select(self, interaction: discord.Interaction):
        item_key = self._select.values[0]
        items = self.trade_view._get_items(self.user_id)
        items.append(item_key)

        await interaction.response.edit_message(content="\u200b", view=None)
        await self.trade_view._refresh()


class _RemoveSelectView(discord.ui.View):
    """Ephemeral dropdown for removing an item from a trade."""

    def __init__(self, trade_view: TradeView, user_id: int):
        super().__init__(timeout=30)
        self.trade_view = trade_view
        self.user_id = user_id

        my_items = trade_view._get_items(user_id)
        options = []
        for i, key in enumerate(my_items):
            name, emoji = trade_view.cog.trading.item_display(key)
            opt = discord.SelectOption(label=name, value=str(i))
            if len(emoji) == 1 or emoji.startswith("<"):
                opt.emoji = emoji
            options.append(opt)

        self._select = discord.ui.Select(
            placeholder="Remove which item?", options=options,
        )
        self._select.callback = self._on_select
        self.add_item(self._select)

    async def _on_select(self, interaction: discord.Interaction):
        idx = int(self._select.values[0])
        items = self.trade_view._get_items(self.user_id)
        if 0 <= idx < len(items):
            items.pop(idx)
        await interaction.response.edit_message(content="\u200b", view=None)
        await self.trade_view._refresh()


class _StarsModal(discord.ui.Modal, title="Set Stars"):
    stars_input = discord.ui.TextInput(
        label="How many stars to offer?",
        placeholder="Enter a number (0 to clear)",
        required=True,
        max_length=10,
    )

    def __init__(self, trade_view: TradeView, user_id: int):
        super().__init__()
        self.trade_view = trade_view
        self.user_id = user_id
        current = trade_view._get_stars(user_id)
        if current > 0:
            self.stars_input.default = str(current)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.stars_input.value)
        except ValueError:
            await interaction.response.send_message(
                "Enter a valid number!", ephemeral=True,
            )
            return
        if amount < 0:
            await interaction.response.send_message(
                "Can't be negative!", ephemeral=True,
            )
            return

        user = self.trade_view.cog.trading.repo.get_user(self.user_id, "")
        if amount > user.stars:
            await interaction.response.send_message(
                f"You only have **{user.stars}** stars!", ephemeral=True,
            )
            return

        self.trade_view._set_stars(self.user_id, amount)
        await interaction.response.defer(ephemeral=True)
        await self.trade_view._refresh()


# ---------------------------------------------------------------------------
# Main trade view
# ---------------------------------------------------------------------------

class TradeView(discord.ui.View):
    """Single-message trade interface for both players."""

    def __init__(
        self,
        cog: TradingCog,
        proposer: discord.Member | discord.User,
        opponent: discord.Member | discord.User,
        channel_id: int,
    ):
        super().__init__(timeout=TRADE_VIEW_TIMEOUT)
        self.cog = cog
        self.proposer_id = proposer.id
        self.opponent_id = opponent.id
        self.proposer_name = proposer.display_name
        self.opponent_name = opponent.display_name
        self.channel_id = channel_id

        self.proposer_items: list[str] = []
        self.opponent_items: list[str] = []
        self.proposer_stars: int = 0
        self.opponent_stars: int = 0

        self.proposer_locked: bool = False
        self.opponent_locked: bool = False

        self.phase: str = "editing"  # "editing" | "review"
        self.review_started_at: datetime | None = None
        self.proposer_confirmed: bool = False
        self.opponent_confirmed: bool = False

        self.message: discord.Message | None = None
        self._rebuild()

    # ---- helpers ----

    def _is_participant(self, user_id: int) -> bool:
        return user_id in (self.proposer_id, self.opponent_id)

    def _get_items(self, user_id: int) -> list[str]:
        if user_id == self.proposer_id:
            return self.proposer_items
        return self.opponent_items

    def _get_stars(self, user_id: int) -> int:
        if user_id == self.proposer_id:
            return self.proposer_stars
        return self.opponent_stars

    def _set_stars(self, user_id: int, amount: int):
        if user_id == self.proposer_id:
            self.proposer_stars = amount
        else:
            self.opponent_stars = amount

    def _is_locked(self, user_id: int) -> bool:
        if user_id == self.proposer_id:
            return self.proposer_locked
        return self.opponent_locked

    def _set_locked(self, user_id: int, locked: bool):
        if user_id == self.proposer_id:
            self.proposer_locked = locked
        else:
            self.opponent_locked = locked

    async def _refresh(self):
        """Rebuild components and edit the main message."""
        self._rebuild()
        embed = self.build_embed()
        if self.message:
            await self.message.edit(embed=embed, view=self)

    def _do_cleanup(self):
        self.cog.trading.end_trade(self.proposer_id, self.opponent_id)
        self.cog._active_trades.pop(self.proposer_id, None)

    # ---- rebuild ----

    def _rebuild(self):
        self.clear_items()

        if self.phase == "editing":
            add_btn = discord.ui.Button(
                label="Add Item", emoji="\U0001f4e6",
                style=discord.ButtonStyle.primary, row=0,
            )
            add_btn.callback = self._add_item_cb
            self.add_item(add_btn)

            stars_btn = discord.ui.Button(
                label="Set Stars", emoji="\u2b50",
                style=discord.ButtonStyle.primary, row=0,
            )
            stars_btn.callback = self._set_stars_cb
            self.add_item(stars_btn)

            remove_btn = discord.ui.Button(
                label="Remove Item", emoji="\U0001f5d1\ufe0f",
                style=discord.ButtonStyle.secondary, row=0,
            )
            remove_btn.callback = self._remove_item_cb
            self.add_item(remove_btn)

            lock_btn = discord.ui.Button(
                label="Lock In", emoji="\U0001f512",
                style=discord.ButtonStyle.success, row=1,
            )
            lock_btn.callback = self._lock_cb
            self.add_item(lock_btn)

            cancel_btn = discord.ui.Button(
                label="Cancel Trade", emoji="\u274c",
                style=discord.ButtonStyle.danger, row=1,
            )
            cancel_btn.callback = self._cancel_cb
            self.add_item(cancel_btn)

        elif self.phase == "review":
            confirm_btn = discord.ui.Button(
                label="Confirm Trade", emoji="\u2705",
                style=discord.ButtonStyle.success, row=0,
            )
            confirm_btn.callback = self._confirm_cb
            self.add_item(confirm_btn)

            back_btn = discord.ui.Button(
                label="Go Back", emoji="\u21a9\ufe0f",
                style=discord.ButtonStyle.secondary, row=0,
            )
            back_btn.callback = self._back_cb
            self.add_item(back_btn)

            cancel_btn = discord.ui.Button(
                label="Cancel Trade", emoji="\u274c",
                style=discord.ButtonStyle.danger, row=0,
            )
            cancel_btn.callback = self._cancel_cb
            self.add_item(cancel_btn)

    # ---- embed ----

    def _format_side(self, stars: int, items: list[str]) -> str:
        lines: list[str] = []
        if stars > 0:
            lines.append(f"\u2b50 **{stars}** stars")
        for key in items:
            name, emoji = self.cog.trading.item_display(key)
            lines.append(f"{emoji} {name}")
        if self.phase == "editing":
            for _ in range(MAX_TRADE_ITEMS - len(items)):
                lines.append("\u25ab\ufe0f *empty slot*")
        if not lines:
            return "*nothing*"
        return "\n".join(lines)

    def build_embed(self) -> discord.Embed:
        if self.phase == "editing":
            p_lock = "\u2705 Locked" if self.proposer_locked else "\U0001f513 Editing"
            o_lock = "\u2705 Locked" if self.opponent_locked else "\U0001f513 Editing"
            desc = (
                f"**\U0001f464 {self.proposer_name} offers:**\n"
                f"{self._format_side(self.proposer_stars, self.proposer_items)}\n\n"
                f"**\U0001f464 {self.opponent_name} offers:**\n"
                f"{self._format_side(self.opponent_stars, self.opponent_items)}\n\n"
                f"{self.proposer_name}: {p_lock} | {self.opponent_name}: {o_lock}"
            )
            embed = discord.Embed(
                title=f"\U0001f91d Trade \u2014 {self.proposer_name} \u2194 {self.opponent_name}",
                description=desc,
                color=discord.Color.blue(),
            )
            embed.set_footer(
                text="Both players must Lock In to proceed. Click Lock In again to unlock.",
            )
            return embed

        if self.phase == "review":
            p_st = "\u2705 Confirmed" if self.proposer_confirmed else "\u23f3 Waiting"
            o_st = "\u2705 Confirmed" if self.opponent_confirmed else "\u23f3 Waiting"
            desc = (
                f"**\U0001f464 {self.proposer_name} gives:**\n"
                f"{self._format_side(self.proposer_stars, self.proposer_items)}\n\n"
                f"**\U0001f464 {self.opponent_name} gives:**\n"
                f"{self._format_side(self.opponent_stars, self.opponent_items)}\n\n"
                "\u26a0\ufe0f **Review carefully before confirming!**\n"
                f"You must wait **{REVIEW_WAIT_SECONDS} seconds** before confirming.\n\n"
                f"{self.proposer_name}: {p_st} | {self.opponent_name}: {o_st}"
            )
            return discord.Embed(
                title="\U0001f50d Trade Review \u2014 READ CAREFULLY",
                description=desc,
                color=discord.Color.orange(),
            )

        return discord.Embed(title="Trade", color=discord.Color.dark_gray())

    # ---- callbacks ----

    async def _add_item_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return
        if self._is_locked(uid):
            await interaction.response.send_message(
                "Unlock first to edit your offer!", ephemeral=True,
            )
            return

        my_items = self._get_items(uid)
        if len(my_items) >= MAX_TRADE_ITEMS:
            await interaction.response.send_message(
                f"Max {MAX_TRADE_ITEMS} items! Remove one first.", ephemeral=True,
            )
            return

        all_items = self.cog.trading.get_tradeable_items(uid)
        in_trade = Counter(my_items)
        available = [
            (key, name, emoji, count - in_trade.get(key, 0))
            for key, name, emoji, count in all_items
            if count - in_trade.get(key, 0) > 0
        ]

        if not available:
            await interaction.response.send_message(
                "You have no items to trade!", ephemeral=True,
            )
            return

        view = _ItemSelectView(self, uid, available)
        await interaction.response.send_message(
            "Select an item to add:", view=view, ephemeral=True,
        )

    async def _set_stars_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return
        if self._is_locked(uid):
            await interaction.response.send_message(
                "Unlock first to edit your offer!", ephemeral=True,
            )
            return

        modal = _StarsModal(self, uid)
        await interaction.response.send_modal(modal)

    async def _remove_item_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return
        if self._is_locked(uid):
            await interaction.response.send_message(
                "Unlock first to edit your offer!", ephemeral=True,
            )
            return

        my_items = self._get_items(uid)
        if not my_items:
            await interaction.response.send_message(
                "No items to remove!", ephemeral=True,
            )
            return

        view = _RemoveSelectView(self, uid)
        await interaction.response.send_message(
            "Select an item to remove:", view=view, ephemeral=True,
        )

    async def _lock_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return

        if self._is_locked(uid):
            # Unlock
            self._set_locked(uid, False)
            self._rebuild()
            embed = self.build_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            return

        # Lock in
        self._set_locked(uid, True)

        # Both locked → transition to review
        if self.proposer_locked and self.opponent_locked:
            self.phase = "review"
            self.review_started_at = datetime.now(timezone.utc)

        self._rebuild()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _back_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return

        self.phase = "editing"
        self.proposer_locked = False
        self.opponent_locked = False
        self.proposer_confirmed = False
        self.opponent_confirmed = False
        self.review_started_at = None
        self._rebuild()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _cancel_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return

        self._do_cleanup()
        embed = discord.Embed(
            title="\u274c Trade Cancelled",
            description=(
                f"**{interaction.user.display_name}** cancelled the trade."
            ),
            color=discord.Color.red(),
        )
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def _confirm_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return

        # Enforce 5-second wait
        if self.review_started_at:
            elapsed = (
                datetime.now(timezone.utc) - self.review_started_at
            ).total_seconds()
            remaining = REVIEW_WAIT_SECONDS - elapsed
            if remaining > 0:
                await interaction.response.send_message(
                    f"\u23f3 Please wait **{int(remaining) + 1}** more second(s).",
                    ephemeral=True,
                )
                return

        # Mark confirmed
        if uid == self.proposer_id:
            self.proposer_confirmed = True
        else:
            self.opponent_confirmed = True

        # Both confirmed → execute
        if self.proposer_confirmed and self.opponent_confirmed:
            p_offer = TradeOffer(
                stars=self.proposer_stars, items=list(self.proposer_items),
            )
            o_offer = TradeOffer(
                stars=self.opponent_stars, items=list(self.opponent_items),
            )

            result: TradeResult = self.cog.trading.execute_trade(
                self.proposer_id, self.proposer_name,
                self.opponent_id, self.opponent_name,
                p_offer, o_offer,
            )
            self._do_cleanup()

            if result.success:
                p_gives = self.cog.trading.format_offer(p_offer)
                o_gives = self.cog.trading.format_offer(o_offer)
                embed = discord.Embed(
                    title="\U0001f389 Trade Complete!",
                    description=(
                        f"**{self.proposer_name}** gave:\n{p_gives}\n\n"
                        f"**{self.opponent_name}** gave:\n{o_gives}"
                    ),
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title="\u274c Trade Failed",
                    description=result.message,
                    color=discord.Color.red(),
                )

            self.clear_items()
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
            return

        # Only one confirmed so far — update embed
        self._rebuild()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        self._do_cleanup()
        embed = discord.Embed(
            title="\u231b Trade Expired",
            description="The trade timed out due to inactivity.",
            color=discord.Color.greyple(),
        )
        self.clear_items()
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class TradingCog(commands.Cog):
    """Commands for player-to-player trading."""

    def __init__(self, bot):
        self.bot = bot
        self.trading = TradeUseCases()
        self._active_trades: dict[int, TradeView] = {}

    @commands.command(name="trade")
    async def trade(self, ctx, *, args: str = ""):
        """Trade items and stars with another player."""
        if not await require_location(ctx, "noodle_town"):
            return

        parts = args.split() if args else []

        if not parts or parts[0].lower() == "help":
            await self._send_help(ctx)
            return

        if parts[0].lower() == "cancel":
            await self._handle_cancel(ctx)
            return

        # Must be a mention
        if not ctx.message.mentions:
            await ctx.send(
                "Usage: `!trade @user` to start a trade, `!trade help` for info.",
            )
            return

        opponent = ctx.message.mentions[0]
        if opponent.bot:
            await ctx.send("You can't trade with a bot.")
            return

        err = self.trading.start_trade(ctx.author.id, opponent.id)
        if err:
            await ctx.send(f"\u274c {err}")
            return

        view = TradeView(self, ctx.author, opponent, ctx.channel.id)
        embed = view.build_embed()
        msg = await ctx.send(
            f"{opponent.mention}, **{ctx.author.display_name}** wants to trade!",
            embed=embed,
            view=view,
        )
        view.message = msg
        self._active_trades[ctx.author.id] = view

    async def _handle_cancel(self, ctx):
        if not self.trading.is_in_trade(ctx.author.id):
            await ctx.send("You don't have an active trade.")
            return

        proposer_id = self.trading._user_in_trade.get(ctx.author.id)
        view = self._active_trades.get(proposer_id) if proposer_id else None

        if view and view.message:
            view._do_cleanup()
            embed = discord.Embed(
                title="\u274c Trade Cancelled",
                description=(
                    f"**{ctx.author.display_name}** cancelled the trade."
                ),
                color=discord.Color.red(),
            )
            view.clear_items()
            try:
                await view.message.edit(embed=embed, view=view)
            except Exception:
                pass
            view.stop()
        else:
            # Fallback cleanup
            if proposer_id is not None:
                for uid, pid in list(self.trading._user_in_trade.items()):
                    if pid == proposer_id and uid != proposer_id:
                        self.trading.end_trade(proposer_id, uid)
                        break
                else:
                    self.trading._user_in_trade.pop(proposer_id, None)
                self._active_trades.pop(proposer_id, None)

        await ctx.send("Trade cancelled.")

    async def _send_help(self, ctx):
        embed = discord.Embed(
            title="Trading Help",
            description="Trade items and stars with other players!",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Start a trade",
            value="`!trade @user` \u2014 opens the trade interface",
            inline=False,
        )
        embed.add_field(
            name="How it works",
            value=(
                "1. Both players add items and/or stars using buttons.\n"
                f"2. Each side can offer up to **{MAX_TRADE_ITEMS} items** "
                "and any amount of **stars**.\n"
                "3. When both players **Lock In**, the trade moves to review.\n"
                f"4. Both must wait **{REVIEW_WAIT_SECONDS} seconds** "
                "then **Confirm** to finalise.\n"
                "5. Either player can **Cancel** at any time."
            ),
            inline=False,
        )
        embed.add_field(
            name="Cancel",
            value="`!trade cancel` \u2014 cancel your current trade",
            inline=False,
        )
        embed.set_footer(
            text="You can only be in one trade at a time. Must be in Noodle Town.",
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(TradingCog(bot))

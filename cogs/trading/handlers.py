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
TRADE_VIEW_TIMEOUT = 1800  # seconds of inactivity before auto-cancel


# ---------------------------------------------------------------------------
# Inline item select (sits on the main trade message, one per user)
# ---------------------------------------------------------------------------

class _TradeItemSelect(discord.ui.Select):
    """Dropdown for one user to add an item to their offer."""

    def __init__(
        self,
        trade_view: TradeView,
        owner_id: int,
        owner_name: str,
        available: list[tuple[str, str, str, int]],
        row: int,
    ):
        self.trade_view = trade_view
        self.owner_id = owner_id

        options = []
        for key, name, emoji, count in available[:25]:
            label = f"{name} (\u00d7{count})" if count > 1 else name
            opt = discord.SelectOption(label=label, value=key)
            if len(emoji) == 1 or emoji.startswith("<"):
                opt.emoji = emoji
            options.append(opt)

        super().__init__(
            placeholder=f"\U0001f4e6 {owner_name} \u2014 add item",
            options=options,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "That's not your dropdown!", ephemeral=True,
            )
            return

        item_key = self.values[0]
        items = self.trade_view._get_items(self.owner_id)
        items.append(item_key)

        await interaction.response.defer()
        self.trade_view._rebuild()
        embed = self.trade_view.build_embed()
        await interaction.edit_original_response(embed=embed, view=self.trade_view)


# ---------------------------------------------------------------------------
# Stars modal (only popup — needs text input)
# ---------------------------------------------------------------------------

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

        self.phase: str = "pending"  # "pending" | "editing" | "review"
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

    def _get_available_items(self, user_id: int):
        """Items the user can still add (inventory minus already offered)."""
        all_items = self.cog.trading.get_tradeable_items(user_id)
        in_trade = Counter(self._get_items(user_id))
        return [
            (key, name, emoji, count - in_trade.get(key, 0))
            for key, name, emoji, count in all_items
            if count - in_trade.get(key, 0) > 0
        ]

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

        if self.phase == "pending":
            accept_btn = discord.ui.Button(
                label="Accept Trade", emoji="\u2705",
                style=discord.ButtonStyle.success, row=0,
            )
            accept_btn.callback = self._accept_cb
            self.add_item(accept_btn)

            decline_btn = discord.ui.Button(
                label="Decline", emoji="\u274c",
                style=discord.ButtonStyle.danger, row=0,
            )
            decline_btn.callback = self._decline_cb
            self.add_item(decline_btn)

        elif self.phase == "editing":
            current_row = 0

            # Proposer's inline item select
            if (not self.proposer_locked
                    and len(self.proposer_items) < MAX_TRADE_ITEMS):
                available = self._get_available_items(self.proposer_id)
                if available:
                    self.add_item(_TradeItemSelect(
                        self, self.proposer_id, self.proposer_name,
                        available, row=current_row,
                    ))
                    current_row += 1

            # Opponent's inline item select
            if (not self.opponent_locked
                    and len(self.opponent_items) < MAX_TRADE_ITEMS):
                available = self._get_available_items(self.opponent_id)
                if available:
                    self.add_item(_TradeItemSelect(
                        self, self.opponent_id, self.opponent_name,
                        available, row=current_row,
                    ))
                    current_row += 1

            # Buttons row
            stars_btn = discord.ui.Button(
                label="Set Stars", emoji="\u2b50",
                style=discord.ButtonStyle.primary, row=current_row,
            )
            stars_btn.callback = self._set_stars_cb
            self.add_item(stars_btn)

            remove_btn = discord.ui.Button(
                label="Remove Last", emoji="\U0001f5d1\ufe0f",
                style=discord.ButtonStyle.secondary, row=current_row,
            )
            remove_btn.callback = self._remove_last_cb
            self.add_item(remove_btn)

            lock_btn = discord.ui.Button(
                label="Lock In", emoji="\U0001f512",
                style=discord.ButtonStyle.success, row=current_row,
            )
            lock_btn.callback = self._lock_cb
            self.add_item(lock_btn)

            cancel_btn = discord.ui.Button(
                label="Cancel", emoji="\u274c",
                style=discord.ButtonStyle.danger, row=current_row,
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
                label="Cancel", emoji="\u274c",
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
        if self.phase == "pending":
            return discord.Embed(
                title="\U0001f91d Trade Request",
                description=(
                    f"**{self.proposer_name}** wants to trade with "
                    f"**{self.opponent_name}**!\n\n"
                    f"{self.opponent_name}, click **Accept Trade** to begin."
                ),
                color=discord.Color.blue(),
            )

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
                title=(
                    f"\U0001f91d Trade \u2014 "
                    f"{self.proposer_name} \u2194 {self.opponent_name}"
                ),
                description=desc,
                color=discord.Color.blue(),
            )
            embed.set_footer(
                text=(
                    "Use your dropdown to add items. "
                    "Both players must Lock In to proceed. "
                    "Click Lock In again to unlock."
                ),
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
                f"You must wait **{REVIEW_WAIT_SECONDS} seconds** "
                "before confirming.\n\n"
                f"{self.proposer_name}: {p_st} | {self.opponent_name}: {o_st}"
            )
            return discord.Embed(
                title="\U0001f50d Trade Review \u2014 READ CAREFULLY",
                description=desc,
                color=discord.Color.orange(),
            )

        return discord.Embed(title="Trade", color=discord.Color.dark_gray())

    # ---- callbacks: pending phase ----

    async def _accept_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid == self.proposer_id:
            await interaction.response.send_message(
                "Waiting for the other player to accept!", ephemeral=True,
            )
            return
        if uid != self.opponent_id:
            await interaction.response.send_message(
                "This trade isn't for you!", ephemeral=True,
            )
            return

        self.phase = "editing"
        await interaction.response.defer()
        self._rebuild()
        embed = self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    async def _decline_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message(
                "This trade isn't for you!", ephemeral=True,
            )
            return

        self._do_cleanup()
        embed = discord.Embed(
            title="\u274c Trade Declined",
            description=(
                f"**{interaction.user.display_name}** declined the trade."
            ),
            color=discord.Color.red(),
        )
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    # ---- callbacks: editing phase ----

    async def _set_stars_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message(
                "Not your trade!", ephemeral=True,
            )
            return
        if self._is_locked(uid):
            await interaction.response.send_message(
                "Unlock first to edit your offer!", ephemeral=True,
            )
            return
        await interaction.response.send_modal(_StarsModal(self, uid))

    async def _remove_last_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message(
                "Not your trade!", ephemeral=True,
            )
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

        my_items.pop()
        await interaction.response.defer()
        self._rebuild()
        embed = self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    async def _lock_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message(
                "Not your trade!", ephemeral=True,
            )
            return

        if self._is_locked(uid):
            # Unlock
            self._set_locked(uid, False)
        else:
            # Lock in
            self._set_locked(uid, True)
            if self.proposer_locked and self.opponent_locked:
                self.phase = "review"
                self.review_started_at = datetime.now(timezone.utc)

        await interaction.response.defer()
        self._rebuild()
        embed = self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    # ---- callbacks: review phase ----

    async def _back_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message(
                "Not your trade!", ephemeral=True,
            )
            return

        self.phase = "editing"
        self.proposer_locked = False
        self.opponent_locked = False
        self.proposer_confirmed = False
        self.opponent_confirmed = False
        self.review_started_at = None
        await interaction.response.defer()
        self._rebuild()
        embed = self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    async def _confirm_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message(
                "Not your trade!", ephemeral=True,
            )
            return

        # Enforce wait
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

        if uid == self.proposer_id:
            self.proposer_confirmed = True
        else:
            self.opponent_confirmed = True

        await interaction.response.defer()

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
            await interaction.edit_original_response(embed=embed, view=self)
            self.stop()
            return

        self._rebuild()
        embed = self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    # ---- shared callbacks ----

    async def _cancel_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if not self._is_participant(uid):
            await interaction.response.send_message(
                "Not your trade!", ephemeral=True,
            )
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
            value="`!trade @user` \u2014 sends a trade request",
            inline=False,
        )
        embed.add_field(
            name="How it works",
            value=(
                "1. The other player must **Accept** the trade request.\n"
                "2. Both players add items and/or stars using dropdowns.\n"
                f"3. Each side can offer up to **{MAX_TRADE_ITEMS} items** "
                "and any amount of **stars**.\n"
                "4. When both players **Lock In**, the trade moves to review.\n"
                f"5. Both must wait **{REVIEW_WAIT_SECONDS} seconds** "
                "then **Confirm** to finalise.\n"
                "6. Either player can **Cancel** at any time."
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

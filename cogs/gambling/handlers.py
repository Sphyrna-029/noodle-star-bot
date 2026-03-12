"""Gambling commands cog."""

import asyncio
import traceback
from datetime import datetime

import discord
from discord.ext import commands

from cogs.combat.constants import STAMINA_PER_ATTACK, STAMINA_RECOVERY
from cogs.combat.dto import BattleTurn
from cogs.economy.constants import ACHIEVEMENT_DEFS
from cogs.locations.check import require_location
from cogs.shop.resources import get_resource
from cogs.gambling.constants import DUEL_INVITE_TIMEOUT, DUEL_TURN_TIMEOUT
from cogs.gambling.use_cases import (
    GambleUseCase,
    CoinflipUseCase,
    DuelUseCase,
    BlackJackUseCase,
    PickpocketUseCase,
    RouletteUseCase,
)
from cogs.gambling.dto import BlackJackGameState, BlackJackResult, DuelState


# ---------------------------------------------------------------------------
# Progress bar helper (same as combat)
# ---------------------------------------------------------------------------

def _progress_bar(pct: float, length: int = 10) -> str:
    filled = int(pct * length)
    return "\u2588" * filled + "\u2591" * (length - filled)


# ---------------------------------------------------------------------------
# Active duel tracking
# ---------------------------------------------------------------------------

_active_duels: set[int] = set()


def is_in_duel(user_id: int) -> bool:
    """Check if a user is currently in an active duel."""
    return user_id in _active_duels


# ---------------------------------------------------------------------------
# BlackJack View (unchanged)
# ---------------------------------------------------------------------------

class BlackJackView(discord.ui.View):
    """Interactive view for BlackJack game with Hit/Stand buttons."""

    def __init__(
        self,
        game_state: BlackJackGameState,
        use_case: BlackJackUseCase,
        author_id: int,
        player_name: str,
    ):
        super().__init__(timeout=120)  # Give users enough time to act
        self.game_state = game_state
        self.use_case = use_case
        self.author_id = author_id
        self.player_name = player_name
        self.message = None
        self._finish_lock = asyncio.Lock()

    def _disable_buttons(self) -> None:
        for item in self.children:
            item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the person who started the game can use the buttons."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your game! Start your own with `!blackjack <amount>`",
                ephemeral=True
            )
            return False
        return True

    def _create_embed(self, result: BlackJackResult, player_name: str) -> discord.Embed:
        """Create an embed showing the current game state."""
        # Format dealer hand (hide second card if game not over)
        if result.game_over:
            dealer_cards = " ".join(str(card) for card in result.dealer_hand)
            dealer_value = f"({result.dealer_value})"
        else:
            dealer_cards = f"{result.dealer_hand[0]} \U0001f0a0"  # Show only first card
            dealer_value = "(?)"

        # Format player hand
        player_cards = " ".join(str(card) for card in result.player_hand)

        # Determine embed color
        if result.game_over:
            if result.won is True:
                color = discord.Color.green()
            elif result.won is False:
                color = discord.Color.red()
            else:  # Push
                color = discord.Color.gold()
        else:
            color = discord.Color.blue()

        embed = discord.Embed(title="\U0001f0cf BlackJack \U0001f0cf", color=color)
        embed.add_field(
            name=f"Dealer's Hand {dealer_value}",
            value=dealer_cards,
            inline=False
        )
        embed.add_field(
            name=f"Your Hand ({result.player_value}) ({player_name})",
            value=player_cards,
            inline=False
        )

        # Add result message if game is over
        if result.game_over:
            if result.is_blackjack:
                result_text = f"\u2728 **{result.message}** \u2728"
            elif result.is_bust:
                result_text = f"\U0001f4a5 **{result.message}** \U0001f4a5"
            elif result.won is True:
                result_text = f"\U0001f389 **{result.message}** \U0001f389"
            elif result.won is False:
                result_text = f"\U0001f614 **{result.message}** \U0001f614"
            else:
                result_text = f"\U0001f91d **{result.message}** \U0001f91d"

            embed.add_field(name="Result", value=result_text, inline=False)

            # Show winnings/losses
            if result.amount_changed > 0:
                embed.add_field(
                    name="Winnings",
                    value=f"+{result.amount_changed} \u2b50",
                    inline=True
                )
            elif result.amount_changed < 0:
                embed.add_field(
                    name="Lost",
                    value=f"{result.amount_changed} \u2b50",
                    inline=True
                )

            embed.add_field(
                name="New Balance",
                value=f"{result.new_balance} \u2b50",
                inline=True
            )
        else:
            embed.set_footer(text="Hit to draw another card, or Stand to end your turn.")

        return embed

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="\U0001f3b4")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle Hit button press."""
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.game_state.game_over:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                result = self.use_case.hit(self.game_state)

                if result.game_over:
                    self.game_state.game_over = True
                    self._disable_buttons()

                embed = self._create_embed(result, self.player_name)
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            traceback.print_exc()
            if interaction.response.is_done():
                await interaction.followup.send(f"\u274c Error: {type(e).__name__}: {str(e)}", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"\u274c Error: {type(e).__name__}: {str(e)}",
                    ephemeral=True
                )

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="\u270b")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle Stand button press."""
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.game_state.game_over:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                result = self.use_case.stand(self.game_state)
                self.game_state.game_over = True

                # Game is always over after standing
                self._disable_buttons()

                embed = self._create_embed(result, self.player_name)
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            traceback.print_exc()
            if interaction.response.is_done():
                await interaction.followup.send(f"\u274c Error: {type(e).__name__}: {str(e)}", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"\u274c Error: {type(e).__name__}: {str(e)}",
                    ephemeral=True
                )

    async def on_timeout(self) -> None:
        """Auto-stand on timeout so bets are always resolved."""
        async with self._finish_lock:
            self._disable_buttons()
            if self.message is None:
                return

            if self.game_state.game_over:
                await self.message.edit(view=self)
                return

            try:
                result = self.use_case.stand(self.game_state)
                self.game_state.game_over = True
                embed = self._create_embed(result, self.player_name)
                await self.message.edit(embed=embed, view=self)
            except Exception:
                traceback.print_exc()
                await self.message.edit(
                    content=(
                        "\u23f0 This blackjack game timed out and could not be auto-resolved.\n"
                        "An admin should check your balance and refund the bet if needed."
                    ),
                    embed=None,
                    view=self,
                )


# ---------------------------------------------------------------------------
# PvP Duel — Invite View
# ---------------------------------------------------------------------------

class DuelInviteView(discord.ui.View):
    """Accept/Decline buttons for a duel challenge."""

    def __init__(
        self,
        challenger: discord.Member,
        opponent: discord.Member,
        amount: int,
        duel_uc: DuelUseCase,
    ):
        super().__init__(timeout=DUEL_INVITE_TIMEOUT)
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
        self.duel_uc = duel_uc
        self.message = None
        self.accepted = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "Only the challenged player can respond!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="\u2694\ufe0f")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            self.accepted = True

            # Disable invite buttons
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(view=self)

            # Check guards again (someone may have started a fight while waiting)
            from cogs.combat.handlers import is_in_battle
            for uid in (self.challenger.id, self.opponent.id):
                if is_in_battle(uid) or is_in_duel(uid):
                    await interaction.followup.send(
                        f"\u274c <@{uid}> is already in a fight! Duel cancelled."
                    )
                    self.stop()
                    return

            # Create duel state
            state, error = self.duel_uc.validate_and_create_state(
                self.challenger.id, str(self.challenger),
                self.opponent.id, str(self.opponent),
                self.amount,
            )
            if error:
                await interaction.followup.send(f"\u274c Duel cancelled: {error}")
                self.stop()
                return

            # Register both players as in-duel
            _active_duels.add(self.challenger.id)
            _active_duels.add(self.opponent.id)

            # Send battle view
            battle_view = DuelBattleView(state, self.duel_uc, self.challenger, self.opponent)
            embed = battle_view._create_embed()
            msg = await interaction.followup.send(embed=embed, view=battle_view)
            battle_view.message = msg

        except Exception:
            traceback.print_exc()
            _active_duels.discard(self.challenger.id)
            _active_duels.discard(self.opponent.id)

        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary, emoji="\u274c")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"\u274c {self.opponent.mention} declined the duel.",
            view=self,
        )
        self.stop()

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    content=f"\u23f0 Duel invite expired — {self.opponent.mention} didn't respond in time.",
                    view=self,
                )
            except Exception:
                pass


# ---------------------------------------------------------------------------
# PvP Duel — Consume dropdowns
# ---------------------------------------------------------------------------

class _DuelHPSelect(discord.ui.Select):
    """Dropdown for HP restoration items during a duel."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="\U0001f356 Consume HP item...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, DuelBattleView):
            return
        if interaction.user.id != view.duel.active_player:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        view._consume_selected_item = self.values[0]
        view._consume_selected_type = "hp"
        await view._do_consume(interaction)


class _DuelStaminaSelect(discord.ui.Select):
    """Dropdown for stamina restoration items during a duel."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="\u26a1 Consume stamina item...", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, DuelBattleView):
            return
        if interaction.user.id != view.duel.active_player:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        view._consume_selected_item = self.values[0]
        view._consume_selected_type = "stamina"
        await view._do_consume(interaction)


# ---------------------------------------------------------------------------
# PvP Duel — Battle View
# ---------------------------------------------------------------------------

class DuelBattleView(discord.ui.View):
    """Interactive PvP duel view with Attack/Defend buttons + consume items."""

    def __init__(
        self,
        duel: DuelState,
        duel_uc: DuelUseCase,
        p1_member: discord.Member,
        p2_member: discord.Member,
    ):
        super().__init__(timeout=DUEL_TURN_TIMEOUT)
        self.duel = duel
        self.duel_uc = duel_uc
        self.p1_member = p1_member
        self.p2_member = p2_member
        self.message = None
        self._finish_lock = asyncio.Lock()
        self._consume_selected_item: str | None = None
        self._consume_selected_type: str | None = None
        self._rebuild_view()

    def _disable_buttons(self) -> None:
        for item in self.children:
            item.disabled = True

    def _finish_duel(self) -> None:
        """Clean up when duel ends."""
        _active_duels.discard(self.duel.p1_id)
        _active_duels.discard(self.duel.p2_id)
        self._disable_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Allow either participant through."""
        if interaction.user.id not in (self.duel.p1_id, self.duel.p2_id):
            await interaction.response.send_message(
                "This isn't your duel!", ephemeral=True
            )
            return False
        return True

    def _active_name(self) -> str:
        if self.duel.active_player == self.duel.p1_id:
            return self.duel.p1_name
        return self.duel.p2_name

    def _create_embed(self) -> discord.Embed:
        d = self.duel
        if d.finished:
            color = discord.Color.gold()
        else:
            color = discord.Color.orange()

        embed = discord.Embed(
            title=f"\u2694\ufe0f PvP Duel \u2014 {d.p1_name} vs {d.p2_name} ({d.wager}\u2b50)",
            color=color,
        )

        # P1 stats
        p1_hp_pct = d.p1_hp / d.p1_max_hp if d.p1_max_hp else 0
        p1_stam_pct = d.p1_stamina / d.p1_max_stamina if d.p1_max_stamina else 0
        p1_defend = " \U0001f6e1\ufe0f" if d.p1_defending else ""
        embed.add_field(
            name=f"\U0001f464 {d.p1_name}{p1_defend}",
            value=(
                f"\u2764\ufe0f HP: {d.p1_hp}/{d.p1_max_hp} {_progress_bar(p1_hp_pct)}\n"
                f"\u26a1 Stam: {d.p1_stamina}/{d.p1_max_stamina} {_progress_bar(p1_stam_pct)}\n"
                f"\u2694\ufe0f ATK: {d.p1_attack}  \U0001f6e1\ufe0f DEF: {d.p1_defense}"
            ),
            inline=True,
        )

        # P2 stats
        p2_hp_pct = d.p2_hp / d.p2_max_hp if d.p2_max_hp else 0
        p2_stam_pct = d.p2_stamina / d.p2_max_stamina if d.p2_max_stamina else 0
        p2_defend = " \U0001f6e1\ufe0f" if d.p2_defending else ""
        embed.add_field(
            name=f"\U0001f464 {d.p2_name}{p2_defend}",
            value=(
                f"\u2764\ufe0f HP: {d.p2_hp}/{d.p2_max_hp} {_progress_bar(p2_hp_pct)}\n"
                f"\u26a1 Stam: {d.p2_stamina}/{d.p2_max_stamina} {_progress_bar(p2_stam_pct)}\n"
                f"\u2694\ufe0f ATK: {d.p2_attack}  \U0001f6e1\ufe0f DEF: {d.p2_defense}"
            ),
            inline=True,
        )

        # Combat log — last 4 turns
        recent = d.turns[-4:] if len(d.turns) > 4 else d.turns
        if recent:
            log_lines = [t.message for t in recent]
            embed.add_field(
                name="\U0001f4dc Combat Log",
                value="\n".join(log_lines),
                inline=False,
            )

        if not d.finished:
            embed.set_footer(
                text=f"{self._active_name()}'s turn | Wager: {d.wager}\u2b50 | \U0001f37d\ufe0f Consume (costs turn)"
            )

        return embed

    def _build_consume_options(self, user_id: int) -> tuple[list, list]:
        """Build HP and stamina dropdown options for the given user."""
        from cogs.combat.use_case.health import HealthUseCases
        health_uc = HealthUseCases(self.duel_uc.repo)

        items = self.duel_uc.repo.get_inventory_items(user_id)
        item_counts: dict[str, int] = {}
        for item in items:
            key = item["item_key"]
            item_counts[key] = item_counts.get(key, 0) + 1

        hp_options = []
        stam_options = []

        for key, count in sorted(item_counts.items()):
            heal = health_uc.get_hp_value(key)
            if heal and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "\U0001f356"
                hp_options.append(discord.SelectOption(
                    label=f"{display} (+{heal} HP) x{count}",
                    value=key,
                    emoji=emoji,
                ))

            recovery = STAMINA_RECOVERY.get(key)
            if recovery and count > 0:
                display = key.replace("_", " ").title()
                res = get_resource(key)
                emoji = res.emoji if res else "\u26a1"
                stam_options.append(discord.SelectOption(
                    label=f"{display} (+{recovery} stam) x{count}",
                    value=key,
                    emoji=emoji,
                ))

        return hp_options, stam_options

    def _rebuild_view(self):
        """Rebuild all view components for the current active player."""
        self.clear_items()
        self._consume_selected_item = None
        self._consume_selected_type = None

        # Row 0: Attack + Defend
        self.add_item(self.attack_button)
        self.add_item(self.defend_button)

        # Consume dropdowns for active player
        hp_opts, stam_opts = self._build_consume_options(self.duel.active_player)
        if hp_opts:
            self.add_item(_DuelHPSelect(hp_opts))
        if stam_opts:
            self.add_item(_DuelStaminaSelect(stam_opts))
        if hp_opts or stam_opts:
            self.add_item(self.consume_button)

    async def _do_consume(self, interaction: discord.Interaction):
        """Consume the selected item — costs a turn."""
        try:
            await interaction.response.defer()
            async with self._finish_lock:
                if self.duel.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                item_key = self._consume_selected_item
                consume_type = self._consume_selected_type
                if not item_key or not consume_type:
                    return

                turn = self.duel_uc.execute_consume(
                    self.duel, interaction.user.id, item_key, consume_type
                )
                if turn is None:
                    display = item_key.replace("_", " ").title()
                    embed = self._create_embed()
                    embed.set_footer(text=f"\u274c Could not consume {display}!")
                    await interaction.edit_original_response(embed=embed, view=self)
                    return

                self._rebuild_view()
                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)

        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="\u2694\ufe0f", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.duel.active_player:
                await interaction.response.send_message("Not your turn!", ephemeral=True)
                return

            await interaction.response.defer()
            async with self._finish_lock:
                if self.duel.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                self.duel_uc.execute_attack(self.duel)

                if self.duel.finished:
                    result = self.duel_uc.resolve_duel(self.duel)
                    self._finish_duel()
                    embed = self._create_embed()

                    winner_member = self.p1_member if result.winner_id == self.duel.p1_id else self.p2_member
                    loser_member = self.p2_member if result.winner_id == self.duel.p1_id else self.p1_member

                    embed.add_field(
                        name="\U0001f3c6 VICTORY",
                        value=(
                            f"**{winner_member.mention}** wins the duel!\n"
                            f"Won **{result.amount}** stars from {loser_member.mention}\n"
                            f"{winner_member.mention} balance: **{result.winner_new_balance}** \u2b50\n"
                            f"{loser_member.mention} balance: **{result.loser_new_balance}** \u2b50"
                        ),
                        inline=False,
                    )
                    await interaction.edit_original_response(embed=embed, view=self)

                    # Achievement unlocks
                    if result.unlocked_achievement_keys:
                        lines = _format_achievement_lines(
                            [(result.winner_id, k) for k in result.unlocked_achievement_keys],
                            {self.duel.p1_id: self.p1_member.mention,
                             self.duel.p2_id: self.p2_member.mention},
                        )
                        if lines:
                            await interaction.followup.send("\n".join(lines))
                    return

                self._rebuild_view()
                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)

        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="\U0001f6e1\ufe0f", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.duel.active_player:
                await interaction.response.send_message("Not your turn!", ephemeral=True)
                return

            await interaction.response.defer()
            async with self._finish_lock:
                if self.duel.finished:
                    self._disable_buttons()
                    await interaction.edit_original_response(view=self)
                    return

                self.duel_uc.execute_defend(self.duel)

                self._rebuild_view()
                embed = self._create_embed()
                await interaction.edit_original_response(embed=embed, view=self)

        except Exception:
            traceback.print_exc()

    @discord.ui.button(label="Select item first", emoji="\U0001f37d\ufe0f", style=discord.ButtonStyle.secondary, disabled=True, row=3)
    async def consume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.duel.active_player:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        if not self._consume_selected_item:
            await interaction.response.send_message("Select an item from the dropdown first!", ephemeral=True)
            return
        await self._do_consume(interaction)

    async def on_timeout(self) -> None:
        """Idle player forfeits."""
        async with self._finish_lock:
            if self.duel.finished:
                if self.message:
                    try:
                        await self.message.edit(view=self)
                    except Exception:
                        pass
                return

            result = self.duel_uc.resolve_timeout(self.duel)
            self._finish_duel()

            if self.message:
                try:
                    embed = self._create_embed()
                    idle_name = self.duel.p1_name if result.loser_id == self.duel.p1_id else self.duel.p2_name
                    winner_member = self.p1_member if result.winner_id == self.duel.p1_id else self.p2_member
                    loser_member = self.p2_member if result.winner_id == self.duel.p1_id else self.p1_member

                    embed.add_field(
                        name="\u23f0 TIMEOUT \u2014 FORFEIT",
                        value=(
                            f"**{idle_name}** took too long and forfeits!\n"
                            f"\U0001f3c6 {winner_member.mention} wins **{result.amount}** stars.\n"
                            f"{winner_member.mention} balance: **{result.winner_new_balance}** \u2b50\n"
                            f"{loser_member.mention} balance: **{result.loser_new_balance}** \u2b50"
                        ),
                        inline=False,
                    )
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    traceback.print_exc()


# ---------------------------------------------------------------------------
# Achievement formatting helper
# ---------------------------------------------------------------------------

_achievement_defs = {d["key"]: d for d in ACHIEVEMENT_DEFS}


def _format_achievement_lines(
    unlocked: list[tuple[int, str]],
    mentions: dict[int, str],
) -> list[str]:
    lines: list[str] = []
    for user_id, achievement_key in unlocked:
        definition = _achievement_defs.get(achievement_key)
        if definition is None:
            continue
        user_mention = mentions.get(user_id, f"<@{user_id}>")
        lines.append(
            f"\U0001f389 {user_mention} unlocked {definition['emoji']} **{definition['name']}**!"
        )
    return lines


# ---------------------------------------------------------------------------
# Gambling Cog
# ---------------------------------------------------------------------------

class GamblingCog(commands.Cog):
    """Commands for gambling games."""

    def __init__(self, bot):
        self.bot = bot
        self.gamble_use_case = GambleUseCase()
        self.coinflip_use_case = CoinflipUseCase()
        self.duel_use_case = DuelUseCase()
        self.pickpocket_use_case = PickpocketUseCase()
        self.blackjack_use_case = BlackJackUseCase()
        self.roulette_use_case = RouletteUseCase()
        self.roulette_use_case.set_game_callback(self._on_roulette_event)

    def _has_lucky_dice(self, user_id: int) -> bool:
        """Check if user owns Lucky Dice (gamble from anywhere)."""
        inv = self.gamble_use_case.repo.get_user_inventory(user_id)
        return inv.get("lucky_dice", 0) > 0

    async def _on_roulette_event(self, event: str, channel_id: int, result) -> None:
        """Handle async roulette events (e.g. timeout loss announcements)."""
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                return

        if event == "timeout_loss":
            await channel.send(
                "\u23f1\ufe0f **Cowardice!**\n"
                f"<@{result.loser_id}> took more than **1 hour** on their turn and forfeits.\n"
                f"\U0001f3c6 <@{result.winner_id}> wins **{result.amount}** stars.\n"
                f"Challenger balance: Wallet **{result.challenger_wallet}** | Bank **{result.challenger_bank}**\n"
                f"Opponent balance: Wallet **{result.opponent_wallet}** | Bank **{result.opponent_bank}**"
            )
        elif event == "timeout_error":
            await channel.send(
                "\u26a0\ufe0f Russian roulette timed out, but payout failed.\n"
                f"Loser: <@{result.loser_id}> | Winner: <@{result.winner_id}>."
            )

    @commands.command(name="gamble")
    async def gamble(self, ctx, amount: int = None):
        """Gamble your noodle stars for a chance to win more!"""
        if not self._has_lucky_dice(ctx.author.id):
            if not await require_location(ctx, "noodle_town"):
                return
        if amount is None:
            await ctx.send(
                f"\u274c {ctx.author.mention}, please specify how many stars to gamble! "
                f"Usage: `!gamble <amount>`"
            )
            return

        result = self.gamble_use_case.execute(ctx.author.id, str(ctx.author), amount)

        if not result.success:
            await ctx.send(f"\u274c {ctx.author.mention}, {result.message}")
            return

        if result.won:
            await ctx.send(
                f"\U0001f3b0 {ctx.author.mention} gambled **{amount}** stars and rolled a **{result.roll}**! \U0001f389\n"
                f"**YOU WIN!** Multiplier: **{result.multiplier}x**\n"
                f"You won **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! \u2b50"
            )
        else:
            await ctx.send(
                f"\U0001f3b0 {ctx.author.mention} gambled **{amount}** stars and rolled a **{result.roll}**... \U0001f494\n"
                f"**YOU LOSE!** You needed a 7!\n"
                f"You lost **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! \U0001f622"
            )

    @commands.command(name="coinflip")
    async def coinflip(self, ctx, amount: int = 0, choice: str = ''):
        """Flip a coin and bet on heads or tails!"""
        if not self._has_lucky_dice(ctx.author.id):
            if not await require_location(ctx, "noodle_town"):
                return
        if amount is None or choice is None:
            await ctx.send(
                f"\u274c {ctx.author.mention}, please specify an amount and choice! "
                f"Usage: `!coinflip <amount> <heads/tails>`"
            )
            return

        result = self.coinflip_use_case.execute(ctx.author.id, str(ctx.author), amount, choice)

        if not result.success:
            await ctx.send(f"\u274c {ctx.author.mention}, {result.message}")
            return

        # Normalize choice for display
        choice_display = choice.lower()
        if choice_display == "h":
            choice_display = "heads"
        elif choice_display == "t":
            choice_display = "tails"

        if result.won:
            await ctx.send(
                f"\U0001fa99 {ctx.author.mention} bet **{amount}** stars on **{choice_display}**!\n"
                f"The coin landed on... **{result.result.upper()}**! \U0001f389\n"
                f"**YOU WIN!** You won **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! \u2b50"
            )
        else:
            await ctx.send(
                f"\U0001fa99 {ctx.author.mention} bet **{amount}** stars on **{choice_display}**!\n"
                f"The coin landed on... **{result.result.upper()}**! \U0001f494\n"
                f"**YOU LOSE!** You lost **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! \U0001f622"
            )

    @commands.command(name="pickpocket", aliases=["pp"])
    async def pickpocket(self, ctx, opponent: discord.Member = None, amount: int = 0):
        """Try to pickpocket another player's stars! Both roll a D20."""
        if not self._has_lucky_dice(ctx.author.id):
            if not await require_location(ctx, "noodle_town"):
                return
        if opponent is None or amount is None:
            await ctx.send(
                f"\u274c {ctx.author.mention}, please specify a target and amount! "
                f"Usage: `!pickpocket @user <amount>`"
            )
            return

        if opponent.bot:
            await ctx.send(f"\u274c {ctx.author.mention}, you can't pickpocket a bot!")
            return

        result = self.pickpocket_use_case.execute(
            ctx.author.id,
            str(ctx.author),
            opponent.id,
            str(opponent),
            amount,
        )

        if not result.success:
            await ctx.send(f"\u274c {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"\U0001f9b9 **PICKPOCKET!** \U0001f9b9\n"
            f"{ctx.author.mention} tries to pickpocket {opponent.mention} for **{amount}** stars!\n"
            f"\U0001f4aa Stamina: **{result.challenger_stamina_before}** \u2192 **{result.challenger_stamina_after}** "
            f"(cost **{result.stamina_cost}**)\n\n"
            f"\U0001f3b2 Rolling..."
        )

        if result.winner_id == ctx.author.id:
            winner = ctx.author
            loser = opponent
        else:
            winner = opponent
            loser = ctx.author

        await ctx.send(
            f"\U0001f3b2 {ctx.author.mention} rolled **{result.challenger_roll}**\n"
            f"\U0001f3b2 {opponent.mention} rolled **{result.opponent_roll}**\n\n"
            f"\U0001f3c6 **{winner.mention} WINS!** \U0001f3c6\n"
            f"{winner.mention} took **{amount}** noodle stars from {loser.mention}!\n\n"
            f"{ctx.author.mention}'s balance: **{result.challenger_new_balance}** stars\n"
            f"{opponent.mention}'s balance: **{result.opponent_new_balance}** stars"
        )
        if result.unlocked_achievement_keys:
            lines = _format_achievement_lines(
                [(result.winner_id, key) for key in result.unlocked_achievement_keys],
                {
                    ctx.author.id: ctx.author.mention,
                    opponent.id: opponent.mention,
                },
            )
            if lines:
                await ctx.send("\n".join(lines))

    @commands.command(name="duel")
    async def duel(self, ctx, opponent: discord.Member = None, amount: int = 0):
        """Challenge another player to a turn-based PvP duel!"""
        if not await require_location(ctx, "noodle_colosseum"):
            return

        if opponent is None or amount is None:
            await ctx.send(
                f"\u274c {ctx.author.mention}, please specify an opponent and amount! "
                f"Usage: `!duel @user <amount>`"
            )
            return

        if opponent.id == ctx.author.id:
            await ctx.send(f"\u274c {ctx.author.mention}, you can't duel yourself!")
            return

        if opponent.bot:
            await ctx.send(f"\u274c {ctx.author.mention}, you can't duel a bot!")
            return

        if amount <= 0:
            await ctx.send(f"\u274c {ctx.author.mention}, you must bet at least 1 star!")
            return

        # Check neither player is in a PvE battle or duel
        from cogs.combat.handlers import is_in_battle
        if is_in_battle(ctx.author.id) or is_in_duel(ctx.author.id):
            await ctx.send(f"\u274c {ctx.author.mention}, you're already in a fight!")
            return
        if is_in_battle(opponent.id) or is_in_duel(opponent.id):
            await ctx.send(f"\u274c {ctx.author.mention}, {opponent.mention} is already in a fight!")
            return

        # Pre-validate wallets and HP/stamina
        p1_stars = self.duel_use_case.repo.get_user_stars(ctx.author.id, str(ctx.author))
        p2_stars = self.duel_use_case.repo.get_user_stars(opponent.id, str(opponent))
        if p1_stars < amount:
            await ctx.send(f"\u274c {ctx.author.mention}, you only have **{p1_stars}** stars in your wallet!")
            return
        if p2_stars < amount:
            await ctx.send(f"\u274c {ctx.author.mention}, {opponent.mention} only has **{p2_stars}** stars!")
            return

        p1_stats = self.duel_use_case.repo.get_combat_stats(ctx.author.id)
        p2_stats = self.duel_use_case.repo.get_combat_stats(opponent.id)
        if (p1_stats["current_hp"] or 100) <= 0:
            await ctx.send(f"\u274c {ctx.author.mention}, you're out of HP!")
            return
        if (p2_stats["current_hp"] or 100) <= 0:
            await ctx.send(f"\u274c {ctx.author.mention}, {opponent.mention} is out of HP!")
            return
        if (p1_stats["current_stamina"] or 100) < STAMINA_PER_ATTACK:
            await ctx.send(f"\u274c {ctx.author.mention}, you don't have enough stamina!")
            return
        if (p2_stats["current_stamina"] or 100) < STAMINA_PER_ATTACK:
            await ctx.send(f"\u274c {ctx.author.mention}, {opponent.mention} doesn't have enough stamina!")
            return

        # Send invite
        view = DuelInviteView(ctx.author, opponent, amount, self.duel_use_case)
        msg = await ctx.send(
            f"\u2694\ufe0f {opponent.mention}, {ctx.author.mention} challenges you to a **PvP Duel** "
            f"for **{amount}** stars!\n"
            f"Accept or decline within {DUEL_INVITE_TIMEOUT} seconds.",
            view=view,
        )
        view.message = msg

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx, amount: int = None):
        """Play BlackJack! Try to get 21 without going over. Dealer stands on 17."""
        if not self._has_lucky_dice(ctx.author.id):
            if not await require_location(ctx, "noodle_town"):
                return
        try:
            if amount is None:
                await ctx.send(
                    f"\u274c {ctx.author.mention}, please specify how many stars to bet! "
                    f"Usage: `!blackjack <amount>`"
                )
                return

            # Send a thinking message to show the bot is responding
            thinking_msg = await ctx.send(f"\U0001f3b4 {ctx.author.mention}, dealing cards...")

            # Start the game
            result = self.blackjack_use_case.start_game(ctx.author.id, str(ctx.author), amount)

            if not result.success:
                await thinking_msg.edit(content=f"\u274c {ctx.author.mention}, {result.message}")
                return

            # If game ended immediately (blackjack or double blackjack)
            if result.game_over:
                embed = discord.Embed(title="\U0001f0cf BlackJack \U0001f0cf", color=discord.Color.gold())

                dealer_cards = " ".join(str(card) for card in result.dealer_hand)
                player_cards = " ".join(str(card) for card in result.player_hand)

                embed.add_field(
                    name=f"Dealer's Hand ({result.dealer_value})",
                    value=dealer_cards,
                    inline=False
                )
                embed.add_field(
                    name=f"Your Hand ({result.player_value})",
                    value=player_cards,
                    inline=False
                )

                if result.won is True:
                    result_text = f"\u2728 **{result.message}** \u2728"
                    embed.color = discord.Color.green()
                else:
                    result_text = f"\U0001f91d **{result.message}** \U0001f91d"

                embed.add_field(name="Result", value=result_text, inline=False)

                if result.amount_changed > 0:
                    embed.add_field(
                        name="Winnings",
                        value=f"+{result.amount_changed} \u2b50",
                        inline=True
                    )

                embed.add_field(
                    name="New Balance",
                    value=f"{result.new_balance} \u2b50",
                    inline=True
                )

                await thinking_msg.edit(content=None, embed=embed)
                return

            # Create game state for the view
            game_state = BlackJackGameState(
                user_id=ctx.author.id,
                username=str(ctx.author),
                bet_amount=amount,
                deck=result.deck,
                player_hand=result.player_hand,
                dealer_hand=result.dealer_hand,
                game_over=False
            )

            # Create the interactive view
            view = BlackJackView(
                game_state,
                self.blackjack_use_case,
                ctx.author.id,
                ctx.author.name,
            )
            embed = view._create_embed(result, ctx.author.name)

            message = await thinking_msg.edit(content=None, embed=embed, view=view)
            view.message = message or thinking_msg
        except Exception as e:
            traceback.print_exc()
            try:
                await ctx.send(f"\u274c An error occurred: {type(e).__name__}: {str(e)}")
            except:
                pass
            # Re-raise so it appears in logs
            raise

    @commands.command(name="russian", aliases=["rr"])
    async def russian(self, ctx, *, args: str = ""):
        """Challenge another player in PvP Russian roulette."""
        if not self._has_lucky_dice(ctx.author.id):
            if not await require_location(ctx, "noodle_town"):
                return
        parts = args.split() if args else []
        if not parts:
            await ctx.send(
                "\U0001f3af **Russian Roulette**\n"
                "`!russian @user <amount>` \u2014 Send PvP invite (6h expiry)\n"
                "`!russian accept [@user]` \u2014 Accept pending PvP invite\n"
                "`!russian fire <1-6>` \u2014 Pick a chamber on your turn (1 hour limit)\n"
                "`!russian cancel [@user]` \u2014 Cancel pending PvP invite\n"
                "`!rr ...` works as shorthand."
            )
            return

        action = parts[0].lower()

        if action in {"accept", "a"}:
            challenger_id = ctx.message.mentions[0].id if ctx.message.mentions else None
            result = self.roulette_use_case.accept_pvp_invite(
                opponent_id=ctx.author.id,
                opponent_name=str(ctx.author),
                challenger_id=challenger_id,
            )
            if not result.success:
                await ctx.send(f"\u274c {ctx.author.mention}, {result.message}")
                return

            await ctx.send(
                "\U0001f52b **PvP Russian Roulette started!**\n"
                f"Bet: **{result.amount}** stars each.\n"
                f"First turn: <@{result.next_turn_user_id}>.\n"
                "Choose a chamber with `!russian fire <1-6>` within **1 hour** or forfeit."
            )
            return

        if action in {"fire", "f"}:
            if len(parts) < 2:
                await ctx.send(f"\u274c {ctx.author.mention}, usage: `!russian fire <1-6>`")
                return
            try:
                chamber_choice = int(parts[1])
            except ValueError:
                await ctx.send(f"\u274c {ctx.author.mention}, usage: `!russian fire <1-6>`")
                return

            result = self.roulette_use_case.fire_pvp_turn(
                user_id=ctx.author.id,
                username=str(ctx.author),
                chamber_choice=chamber_choice,
            )
            if not result.success:
                await ctx.send(f"\u274c {ctx.author.mention}, {result.message}")
                return

            if not result.game_over:
                await ctx.send(
                    f"*click* {ctx.author.mention} fired chamber **{result.selected_chamber}** safely.\n"
                    f"Next turn: <@{result.next_turn_user_id}>.\n"
                    "Use `!russian fire <1-6>` within **1 hour**."
                )
                return

            guild = ctx.guild
            players = {}
            for shooter_id, _chosen, _fired in result.trigger_log:
                players[shooter_id] = guild.get_member(shooter_id) if guild else None
            if result.winner_id is not None:
                players[result.winner_id] = guild.get_member(result.winner_id) if guild else None
            if result.loser_id is not None:
                players[result.loser_id] = guild.get_member(result.loser_id) if guild else None

            pull_lines = []
            for idx, (shooter_id, chosen_chamber, fired) in enumerate(result.trigger_log, start=1):
                shooter = players.get(shooter_id)
                shooter_name = shooter.mention if shooter else f"<@{shooter_id}>"
                if fired:
                    pull_lines.append(
                        f"**{idx}.** {shooter_name} chose chamber **{chosen_chamber}**... **BANG** \U0001f4a5"
                    )
                else:
                    pull_lines.append(
                        f"**{idx}.** {shooter_name} chose chamber **{chosen_chamber}**... *click*"
                    )

            winner = players.get(result.winner_id)
            loser = players.get(result.loser_id)
            winner_name = winner.mention if winner else f"<@{result.winner_id}>"
            loser_name = loser.mention if loser else f"<@{result.loser_id}>"

            await ctx.send(
                "\U0001f52b **PvP Russian Roulette**\n"
                + "\n".join(pull_lines)
                + "\n\n"
                + f"\U0001f3c6 {winner_name} wins **{result.amount}** stars.\n"
                + f"\U0001f480 {loser_name} ate the bullet.\n"
                + f"Challenger balance: Wallet **{result.challenger_wallet}** | Bank **{result.challenger_bank}**\n"
                + f"Opponent balance: Wallet **{result.opponent_wallet}** | Bank **{result.opponent_bank}**"
            )
            return

        if action in {"cancel", "decline"}:
            challenger_id = ctx.message.mentions[0].id if ctx.message.mentions else None
            result = self.roulette_use_case.cancel_pvp_invite(
                user_id=ctx.author.id,
                challenger_id=challenger_id,
            )
            if not result.success:
                await ctx.send(f"\u274c {ctx.author.mention}, {result.message}")
                return
            await ctx.send("\U0001f6ab Roulette invite cancelled.")
            return

        # PvP invite if a user is mentioned: !russian @user <amount>
        if ctx.message.mentions:
            opponent = ctx.message.mentions[0]
            if opponent.bot:
                await ctx.send(f"\u274c {ctx.author.mention}, you can't challenge a bot.")
                return

            amount_token = None
            for part in parts[1:]:
                if part.startswith("<@") and part.endswith(">"):
                    continue
                if part.startswith("@"):
                    continue
                amount_token = part
                break

            try:
                amount = int(amount_token) if amount_token is not None else None
            except (TypeError, ValueError):
                amount = None

            result = self.roulette_use_case.create_pvp_invite(
                challenger_id=ctx.author.id,
                challenger_name=str(ctx.author),
                opponent_id=opponent.id,
                opponent_name=str(opponent),
                amount=amount,
                channel_id=ctx.channel.id,
            )
            if not result.success:
                await ctx.send(f"\u274c {ctx.author.mention}, {result.message}")
                return

            expires_text = ""
            if result.expires_at:
                expires_at = datetime.fromisoformat(result.expires_at)
                expires_text = f" (expires <t:{int(expires_at.timestamp())}:R>)"

            await ctx.send(
                f"\U0001f52b {opponent.mention}, {ctx.author.mention} challenged you to PvP Russian Roulette "
                f"for **{result.amount}** stars each.\n"
                f"Accept with `!russian accept`{expires_text}."
            )
            return

        await ctx.send(
            f"\u274c {ctx.author.mention}, invalid russian roulette command.\n"
            "Use `!russian` for syntax."
        )


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(GamblingCog(bot))

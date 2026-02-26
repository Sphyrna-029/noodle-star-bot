"""Gambling commands cog."""

import discord
from discord.ext import commands

from cogs.gambling.use_cases import GambleUseCase, CoinflipUseCase, DuelUseCase, BlackJackUseCase
from cogs.gambling.dto import BlackJackGameState


class BlackJackView(discord.ui.View):
    """Interactive view for BlackJack game with Hit/Stand buttons."""

    def __init__(self, game_state: BlackJackGameState, use_case: BlackJackUseCase, author_id: int):
        super().__init__(timeout=30)  # 30 second timeout
        self.game_state = game_state
        self.use_case = use_case
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the person who started the game can use the buttons."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your game! Start your own with `!blackjack <amount>`",
                ephemeral=True
            )
            return False
        return True

    def _create_embed(self, result) -> discord.Embed:
        """Create an embed showing the current game state."""
        # Format dealer hand (hide second card if game not over)
        if result.game_over:
            dealer_cards = " ".join(str(card) for card in result.dealer_hand)
            dealer_value = f"({result.dealer_value})"
        else:
            dealer_cards = f"{result.dealer_hand[0]} 🂠"  # Show only first card
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

        embed = discord.Embed(title="🃏 BlackJack 🃏", color=color)
        embed.add_field(
            name=f"Dealer's Hand {dealer_value}",
            value=dealer_cards,
            inline=False
        )
        embed.add_field(
            name=f"Your Hand ({result.player_value})",
            value=player_cards,
            inline=False
        )

        # Add result message if game is over
        if result.game_over:
            if result.is_blackjack:
                result_text = f"✨ **{result.message}** ✨"
            elif result.is_bust:
                result_text = f"💥 **{result.message}** 💥"
            elif result.won is True:
                result_text = f"🎉 **{result.message}** 🎉"
            elif result.won is False:
                result_text = f"😔 **{result.message}** 😔"
            else:
                result_text = f"🤝 **{result.message}** 🤝"

            embed.add_field(name="Result", value=result_text, inline=False)

            # Show winnings/losses
            if result.amount_changed > 0:
                embed.add_field(
                    name="Winnings",
                    value=f"+{result.amount_changed} ⭐",
                    inline=True
                )
            elif result.amount_changed < 0:
                embed.add_field(
                    name="Lost",
                    value=f"{result.amount_changed} ⭐",
                    inline=True
                )

            embed.add_field(
                name="New Balance",
                value=f"{result.new_balance} ⭐",
                inline=True
            )
        else:
            embed.set_footer(text="Hit to draw another card, or Stand to end your turn.")

        return embed

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="🎴")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle Hit button press."""
        try:
            result = self.use_case.hit(self.game_state)

            if result.game_over:
                # Disable buttons when game is over
                for item in self.children:
                    item.disabled = True

            embed = self._create_embed(result)
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {type(e).__name__}: {str(e)}",
                ephemeral=True
            )
            raise

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle Stand button press."""
        try:
            result = self.use_case.stand(self.game_state)

            # Game is always over after standing
            for item in self.children:
                item.disabled = True

            embed = self._create_embed(result)
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {type(e).__name__}: {str(e)}",
                ephemeral=True
            )
            raise


class GamblingCog(commands.Cog):
    """Commands for gambling games."""

    def __init__(self, bot):
        self.bot = bot
        self.gamble_use_case = GambleUseCase()
        self.coinflip_use_case = CoinflipUseCase()
        self.duel_use_case = DuelUseCase()
        self.blackjack_use_case = BlackJackUseCase()

    @commands.command(name="gamble")
    async def gamble(self, ctx, amount: int = None):
        """Gamble your noodle stars for a chance to win more!"""
        if amount is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify how many stars to gamble! "
                f"Usage: `!gamble <amount>`"
            )
            return

        result = self.gamble_use_case.execute(ctx.author.id, str(ctx.author), amount)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        if result.won:
            await ctx.send(
                f"🎰 {ctx.author.mention} gambled **{amount}** stars and rolled a **{result.roll}**! 🎉\n"
                f"**YOU WIN!** Multiplier: **{result.multiplier}x**\n"
                f"You won **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! ⭐"
            )
        else:
            await ctx.send(
                f"🎰 {ctx.author.mention} gambled **{amount}** stars and rolled a **{result.roll}**... 💔\n"
                f"**YOU LOSE!** You needed a 7!\n"
                f"You lost **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! 😢"
            )

    @commands.command(name="coinflip")
    async def coinflip(self, ctx, amount: int = 0, choice: str = ''):
        """Flip a coin and bet on heads or tails!"""
        if amount is None or choice is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an amount and choice! "
                f"Usage: `!coinflip <amount> <heads/tails>`"
            )
            return

        result = self.coinflip_use_case.execute(ctx.author.id, str(ctx.author), amount, choice)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Normalize choice for display
        choice_display = choice.lower()
        if choice_display == "h":
            choice_display = "heads"
        elif choice_display == "t":
            choice_display = "tails"

        if result.won:
            await ctx.send(
                f"🪙 {ctx.author.mention} bet **{amount}** stars on **{choice_display}**!\n"
                f"The coin landed on... **{result.result.upper()}**! 🎉\n"
                f"**YOU WIN!** You won **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! ⭐"
            )
        else:
            await ctx.send(
                f"🪙 {ctx.author.mention} bet **{amount}** stars on **{choice_display}**!\n"
                f"The coin landed on... **{result.result.upper()}**! 💔\n"
                f"**YOU LOSE!** You lost **{result.amount_changed}** noodle stars!\n"
                f"New balance: **{result.new_balance}** stars! 😢"
            )

    @commands.command(name="duel")
    async def duel(self, ctx, opponent: discord.Member = None, amount: int = 0):
        """Challenge another user to a dice duel!"""
        if opponent is None or amount is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an opponent and amount! "
                f"Usage: `!duel @user <amount>`"
            )
            return

        # Check if trying to duel a bot
        if opponent.bot:
            await ctx.send(f"❌ {ctx.author.mention}, you can't duel a bot!")
            return

        result = self.duel_use_case.execute(
            ctx.author.id,
            str(ctx.author),
            opponent.id,
            str(opponent),
            amount,
        )

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Send initial duel message
        await ctx.send(
            f"⚔️ **DICE DUEL!** ⚔️\n"
            f"{ctx.author.mention} challenges {opponent.mention} to a duel for **{amount}** stars!\n"
            f"💪 Stamina: **{result.challenger_stamina_before}** → **{result.challenger_stamina_after}** "
            f"(cost **{result.stamina_cost}**)\n\n"
            f"🎲 Rolling..."
        )

        # Determine winner display
        if result.winner_id == ctx.author.id:
            winner = ctx.author
            loser = opponent
        else:
            winner = opponent
            loser = ctx.author

        await ctx.send(
            f"🎲 {ctx.author.mention} rolled **{result.challenger_roll}**\n"
            f"🎲 {opponent.mention} rolled **{result.opponent_roll}**\n\n"
            f"🏆 **{winner.mention} WINS!** 🏆\n"
            f"{winner.mention} won **{amount}** noodle stars from {loser.mention}!\n\n"
            f"{ctx.author.mention}'s balance: **{result.challenger_new_balance}** stars\n"
            f"{opponent.mention}'s balance: **{result.opponent_new_balance}** stars"
        )

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx, amount: int = None):
        """Play BlackJack! Try to get 21 without going over. Dealer stands on 17."""
        try:
            print(f"[DEBUG] Blackjack command called by {ctx.author} with amount: {amount}")
            
            if amount is None:
                await ctx.send(
                    f"❌ {ctx.author.mention}, please specify how many stars to bet! "
                    f"Usage: `!blackjack <amount>`"
                )
                return

            # Send a thinking message to show the bot is responding
            thinking_msg = await ctx.send(f"🎴 {ctx.author.mention}, dealing cards...")
            
            print("[DEBUG] Starting game...")
            # Start the game
            result = self.blackjack_use_case.start_game(ctx.author.id, str(ctx.author), amount)
            print(f"[DEBUG] Game started - success: {result.success}, game_over: {result.game_over}")

            if not result.success:
                await thinking_msg.edit(content=f"❌ {ctx.author.mention}, {result.message}")
                return

            # If game ended immediately (blackjack or double blackjack)
            if result.game_over:
                print("[DEBUG] Game ended immediately")
                embed = discord.Embed(title="🃏 BlackJack 🃏", color=discord.Color.gold())

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
                    result_text = f"✨ **{result.message}** ✨"
                    embed.color = discord.Color.green()
                else:
                    result_text = f"🤝 **{result.message}** 🤝"

                embed.add_field(name="Result", value=result_text, inline=False)

                if result.amount_changed > 0:
                    embed.add_field(
                        name="Winnings",
                        value=f"+{result.amount_changed} ⭐",
                        inline=True
                    )

                embed.add_field(
                    name="New Balance",
                    value=f"{result.new_balance} ⭐",
                    inline=True
                )

                await thinking_msg.edit(content=None, embed=embed)
                return

            print("[DEBUG] Creating game state and view...")
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
            view = BlackJackView(game_state, self.blackjack_use_case, ctx.author.id)
            print("[DEBUG] Creating embed...")
            embed = view._create_embed(result)

            print("[DEBUG] Sending message with embed and view...")
            await thinking_msg.edit(content=None, embed=embed, view=view)
            print("[DEBUG] Message sent successfully")
        except Exception as e:
            print(f"[ERROR] Exception in blackjack command: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                await ctx.send(f"❌ An error occurred: {type(e).__name__}: {str(e)}")
            except:
                pass
            # Re-raise so it appears in logs
            raise


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(GamblingCog(bot))

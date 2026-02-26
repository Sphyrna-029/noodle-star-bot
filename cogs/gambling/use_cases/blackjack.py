import random

from cogs.gambling.use_cases.base import BaseGamblingUseCase
from cogs.gambling.dto import (
    BlackJackSuits,
    BlackJackResult,
    BlackJackCard,
    BlackJackGameState,
)
from cogs.gambling.constants import BLACKJACK_DECKS, BLACKJACK_PAYOUT, BLACKJACK_WIN_MULTIPLIER


class BlackJackUseCase(BaseGamblingUseCase):
    """Handles the BlackJack gambling logic."""

    def _get_deck(self) -> list[BlackJackCard]:
        """Create a shuffled deck of cards."""
        deck = [BlackJackCard(rank, suit) for suit in BlackJackSuits for rank in range(2, 15)]
        full_deck = deck * BLACKJACK_DECKS
        random.shuffle(full_deck)
        return full_deck

    def _calculate_hand_value(self, hand: list[BlackJackCard]) -> int:
        """Calculate the value of a hand."""
        value = 0
        aces = 0

        for card in hand:
            if card.rank == 14:  # Ace
                aces += 1
                value += 11
            else:
                value += card.get_value()

        # Adjust for Aces if bust
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1

        return value

    def _is_blackjack(self, hand: list[BlackJackCard]) -> bool:
        """Check if hand is a natural blackjack."""
        return len(hand) == 2 and self._calculate_hand_value(hand) == 21

    def start_game(self, user_id: int, username: str, amount: int) -> BlackJackResult:
        """Start a new blackjack game."""
        current_stars = self.repo.get_user_stars(user_id, username)

        # Validate bet amount
        if amount <= 0:
            return BlackJackResult(
                success=False,
                message="You must bet at least 1 star!",
            )

        if current_stars < amount:
            return BlackJackResult(
                success=False,
                message=f"You don't have enough stars! You have {current_stars} stars.",
            )

        # Create deck and deal initial cards
        deck = self._get_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        player_value = self._calculate_hand_value(player_hand)
        dealer_value = self._calculate_hand_value(dealer_hand)

        # Check for immediate blackjack
        player_blackjack = self._is_blackjack(player_hand)
        dealer_blackjack = self._is_blackjack(dealer_hand)

        if player_blackjack:
            if dealer_blackjack:
                # Push - tie
                return BlackJackResult(
                    success=True,
                    message="Both you and the dealer have Blackjack! It's a push!",
                    won=None,
                    game_over=True,
                    player_hand=player_hand,
                    dealer_hand=dealer_hand,
                    player_value=player_value,
                    dealer_value=dealer_value,
                    amount_changed=0,
                    new_balance=current_stars,
                    is_blackjack=True,
                    deck=deck,
                )
            else:
                # Player wins with blackjack (3:2 payout)
                # Bet is never deducted for natural blackjack, so we add bet + (bet * 1.5)
                profit = int(amount * BLACKJACK_PAYOUT)
                new_balance = current_stars + profit
                self.repo.update_user_stars(user_id, username, new_balance)
                return BlackJackResult(
                    success=True,
                    message="BLACKJACK! You win!",
                    won=True,
                    game_over=True,
                    player_hand=player_hand,
                    dealer_hand=dealer_hand,
                    player_value=player_value,
                    dealer_value=dealer_value,
                    amount_changed=profit,
                    new_balance=new_balance,
                    is_blackjack=True,
                    deck=deck,
                )

        # Deduct bet amount
        new_balance = current_stars - amount
        self.repo.update_user_stars(user_id, username, new_balance)

        return BlackJackResult(
            success=True,
            message="Game started!",
            won=None,
            game_over=False,
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            player_value=player_value,
            dealer_value=dealer_value,
            amount_changed=0,
            new_balance=new_balance,
            deck=deck,
        )

    def hit(self, game_state: BlackJackGameState) -> BlackJackResult:
        """Player hits - draw another card."""
        # Draw a card
        game_state.player_hand.append(game_state.deck.pop())
        player_value = self._calculate_hand_value(game_state.player_hand)

        # Check for bust
        if player_value > 21:
            # Player busts - loses
            return BlackJackResult(
                success=True,
                message="You bust! Dealer wins.",
                won=False,
                game_over=True,
                player_hand=game_state.player_hand,
                dealer_hand=game_state.dealer_hand,
                player_value=player_value,
                dealer_value=self._calculate_hand_value(game_state.dealer_hand),
                amount_changed=-game_state.bet_amount,
                new_balance=self.repo.get_user_stars(game_state.user_id, game_state.username),
                is_bust=True,
                deck=game_state.deck,
            )

        # Game continues
        return BlackJackResult(
            success=True,
            message="You hit!",
            won=None,
            game_over=False,
            player_hand=game_state.player_hand,
            dealer_hand=game_state.dealer_hand,
            player_value=player_value,
            dealer_value=self._calculate_hand_value(game_state.dealer_hand),
            amount_changed=0,
            new_balance=self.repo.get_user_stars(game_state.user_id, game_state.username),
            deck=game_state.deck,
        )

    def stand(self, game_state: BlackJackGameState) -> BlackJackResult:
        """Player stands - dealer plays out their hand."""
        player_value = self._calculate_hand_value(game_state.player_hand)
        dealer_value = self._calculate_hand_value(game_state.dealer_hand)

        # Dealer draws until 17 or higher
        while dealer_value < 17:
            game_state.dealer_hand.append(game_state.deck.pop())
            dealer_value = self._calculate_hand_value(game_state.dealer_hand)

        # Get current balance (bet was already deducted)
        current_balance = self.repo.get_user_stars(game_state.user_id, game_state.username)

        # Determine winner
        if dealer_value > 21:
            # Dealer busts - player wins (return bet + winnings)
            winnings = int(game_state.bet_amount * (1 + BLACKJACK_WIN_MULTIPLIER))
            new_balance = current_balance + winnings
            self.repo.update_user_stars(game_state.user_id, game_state.username, new_balance)
            return BlackJackResult(
                success=True,
                message="Dealer busts! You win!",
                won=True,
                game_over=True,
                player_hand=game_state.player_hand,
                dealer_hand=game_state.dealer_hand,
                player_value=player_value,
                dealer_value=dealer_value,
                amount_changed=game_state.bet_amount,
                new_balance=new_balance,
                deck=game_state.deck,
            )
        elif player_value > dealer_value:
            # Player wins (return bet + winnings)
            winnings = int(game_state.bet_amount * (1 + BLACKJACK_WIN_MULTIPLIER))
            new_balance = current_balance + winnings
            self.repo.update_user_stars(game_state.user_id, game_state.username, new_balance)
            return BlackJackResult(
                success=True,
                message="You win!",
                won=True,
                game_over=True,
                player_hand=game_state.player_hand,
                dealer_hand=game_state.dealer_hand,
                player_value=player_value,
                dealer_value=dealer_value,
                amount_changed=game_state.bet_amount,
                new_balance=new_balance,
                deck=game_state.deck,
            )
        elif player_value < dealer_value:
            # Dealer wins (bet already deducted, nothing to do)
            return BlackJackResult(
                success=True,
                message="Dealer wins!",
                won=False,
                game_over=True,
                player_hand=game_state.player_hand,
                dealer_hand=game_state.dealer_hand,
                player_value=player_value,
                dealer_value=dealer_value,
                amount_changed=-game_state.bet_amount,
                new_balance=current_balance,
                deck=game_state.deck,
            )
        else:
            # Push - tie (return bet)
            new_balance = current_balance + game_state.bet_amount
            self.repo.update_user_stars(game_state.user_id, game_state.username, new_balance)
            return BlackJackResult(
                success=True,
                message="It's a push! Tie game.",
                won=None,
                game_over=True,
                player_hand=game_state.player_hand,
                dealer_hand=game_state.dealer_hand,
                player_value=player_value,
                dealer_value=dealer_value,
                amount_changed=0,
                new_balance=new_balance,
                deck=game_state.deck,
            )

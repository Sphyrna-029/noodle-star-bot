"""Trading service for player-to-player trades."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional

from config import SHOP_ITEMS, get_item_by_alias
from database.repository import UserRepository


# =============================================================================
# Constants
# =============================================================================

TRADE_PENDING_TIMEOUT = 60  # seconds before pending trade auto-cancels
TRADE_COUNTDOWN_SECONDS = 10  # seconds after accept before execution


# =============================================================================
# Enums and Data Classes
# =============================================================================


class TradeState(Enum):
    """States for the trade state machine."""
    PENDING = "pending"        # Waiting for opponent to accept
    COUNTDOWN = "countdown"    # 10s cancel window after accept
    COMPLETED = "completed"    # Trade executed successfully
    CANCELLED = "cancelled"    # Trade was cancelled


@dataclass
class TradeOffer:
    """What one side of a trade is giving."""
    stars: int = 0
    items: Dict[str, int] = field(default_factory=dict)  # item_key -> quantity


@dataclass
class TradeSession:
    """Represents an active trade between two users."""
    proposer_id: int
    proposer_name: str
    opponent_id: int
    opponent_name: str
    proposer_offer: TradeOffer
    opponent_offer: TradeOffer
    state: TradeState = TradeState.PENDING
    channel_id: int = 0
    task: Optional[asyncio.Task] = field(default=None, repr=False)


@dataclass
class TradeResult:
    """Result of a trade action."""
    success: bool
    message: str
    session: Optional[TradeSession] = None


# =============================================================================
# Parser
# =============================================================================


def parse_trade_offer(args: list[str]) -> tuple[Optional[TradeOffer], Optional[TradeOffer], str]:
    """
    Parse trade arguments into two TradeOffer objects.

    Format: "50 stars 1 sword for 2 helmet"
    The 'for' keyword splits proposer's offer from opponent's offer.
    Omitting 'for' means a one-sided gift.

    Returns:
        (proposer_offer, opponent_offer, error_message)
        On error, offers are None and error_message is set.
    """
    if not args:
        return TradeOffer(), TradeOffer(), ""

    # Split on 'for' keyword
    for_index = None
    for i, arg in enumerate(args):
        if arg.lower() == "for":
            for_index = i
            break

    if for_index is not None:
        give_args = args[:for_index]
        want_args = args[for_index + 1:]
    else:
        give_args = args
        want_args = []

    proposer_offer, err = _parse_half(give_args)
    if err:
        return None, None, f"Error in your offer: {err}"

    opponent_offer, err = _parse_half(want_args)
    if err:
        return None, None, f"Error in requested items: {err}"

    # Must offer or request something
    if (proposer_offer.stars == 0 and not proposer_offer.items
            and opponent_offer.stars == 0 and not opponent_offer.items):
        return None, None, "You must offer or request something."

    return proposer_offer, opponent_offer, ""


def _parse_half(args: list[str]) -> tuple[Optional[TradeOffer], str]:
    """
    Parse one side of a trade offer.

    Tokens are consumed as: [amount] <item_or_stars>
    Amount defaults to 1 if the next token isn't a number.
    """
    offer = TradeOffer()
    i = 0

    while i < len(args):
        token = args[i]

        # Try to read a quantity
        try:
            amount = int(token)
            if amount <= 0:
                return None, f"Amount must be positive (got {amount})."
            i += 1
            if i >= len(args):
                return None, f"Expected item name after {amount}."
            token = args[i]
        except ValueError:
            amount = 1

        # Check if it's "stars"
        if token.lower() == "stars" or token.lower() == "star":
            offer.stars += amount
            i += 1
            continue

        # Try to resolve as item — might be multi-word alias
        # Greedily try longest match first (2 words, then 1 word)
        matched = False
        for length in range(min(3, len(args) - i), 0, -1):
            candidate = " ".join(args[i:i + length])
            item = get_item_by_alias(candidate)
            if item:
                key = item["key"]
                offer.items[key] = offer.items.get(key, 0) + amount
                i += length
                matched = True
                break

        if not matched:
            return None, f"Unknown item: '{token}'."

    return offer, ""


# =============================================================================
# Trade Service
# =============================================================================


class TradeService:
    """
    Handles all trade-related business logic.

    State machine:
    1. Proposer creates trade (!trade @user ...) -> PENDING
    2. Opponent accepts (!trade accept) -> COUNTDOWN (10s)
    3. After 10s countdown, trade executes -> COMPLETED
    Either party can cancel at any point -> CANCELLED
    """

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()
        self._sessions: Dict[int, TradeSession] = {}  # keyed by proposer_id
        self._user_in_trade: Dict[int, int] = {}  # user_id -> proposer_id
        self._trade_callback: Optional[Callable] = None

    def set_trade_callback(self, callback: Callable) -> None:
        """Set the callback for trade notifications (countdown, complete, cancel)."""
        self._trade_callback = callback

    def get_session_for_user(self, user_id: int) -> Optional[TradeSession]:
        """Get the active trade session a user is involved in."""
        proposer_id = self._user_in_trade.get(user_id)
        if proposer_id is None:
            return None
        return self._sessions.get(proposer_id)

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _cleanup_session(self, proposer_id: int) -> None:
        """Clean up a trade session and its async task."""
        session = self._sessions.pop(proposer_id, None)
        if session:
            self._user_in_trade.pop(session.proposer_id, None)
            self._user_in_trade.pop(session.opponent_id, None)
            if session.task and not session.task.done():
                session.task.cancel()

    def _validate_offer(self, user_id: int, username: str, offer: TradeOffer) -> Optional[str]:
        """
        Check that a user has enough stars and items to fulfill an offer.

        Returns an error message if validation fails, None if OK.
        """
        user = self.repo.get_user(user_id, username)

        if offer.stars > 0 and user.stars < offer.stars:
            return f"Not enough stars (have {user.stars}, need {offer.stars})."

        if offer.items:
            inventory = self.repo.get_user_inventory(user_id)
            for item_key, qty in offer.items.items():
                item_info = SHOP_ITEMS.get(item_key)
                if not item_info:
                    return f"Unknown item: {item_key}."
                db_col = item_info["db_column"]
                have = inventory.get(db_col, 0)
                if have < qty:
                    return (
                        f"Not enough {item_info['display_name']} "
                        f"(have {have}, need {qty})."
                    )

        return None

    def _format_offer(self, offer: TradeOffer) -> str:
        """Format a TradeOffer as a human-readable string."""
        parts = []
        if offer.stars > 0:
            parts.append(f"**{offer.stars}** stars")
        for item_key, qty in offer.items.items():
            item_info = SHOP_ITEMS.get(item_key, {})
            emoji = item_info.get("emoji", "")
            name = item_info.get("display_name", item_key)
            parts.append(f"{emoji} **{qty}x** {name}")
        return ", ".join(parts) if parts else "*nothing*"

    def _transfer_offer(
        self,
        from_id: int,
        from_name: str,
        to_id: int,
        to_name: str,
        offer: TradeOffer,
    ) -> None:
        """Transfer stars and items from one user to another."""
        if offer.stars > 0:
            from_stars = self.repo.get_user_stars(from_id, from_name)
            to_stars = self.repo.get_user_stars(to_id, to_name)
            self.repo.update_user_stars(from_id, from_name, from_stars - offer.stars)
            self.repo.update_user_stars(to_id, to_name, to_stars + offer.stars)

        if offer.items:
            from_inv = self.repo.get_user_inventory(from_id)
            to_inv = self.repo.get_user_inventory(to_id)
            for item_key, qty in offer.items.items():
                db_col = SHOP_ITEMS[item_key]["db_column"]
                self.repo.update_user_inventory(
                    from_id, db_col, from_inv[db_col] - qty
                )
                self.repo.update_user_inventory(
                    to_id, db_col, to_inv[db_col] + qty
                )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def propose_trade(
        self,
        proposer_id: int,
        proposer_name: str,
        opponent_id: int,
        opponent_name: str,
        channel_id: int,
        args: list[str],
    ) -> TradeResult:
        """
        Create a new trade proposal.

        Validates:
        - Not self-trade
        - Neither party already in a trade
        - Proposer has offered items/stars
        """
        # Self-trade check
        if proposer_id == opponent_id:
            return TradeResult(False, "You can't trade with yourself.")

        # Already in trade check
        if proposer_id in self._user_in_trade:
            return TradeResult(
                False,
                "You're already in a trade. Use `!trade cancel` first.",
            )
        if opponent_id in self._user_in_trade:
            return TradeResult(
                False,
                f"{opponent_name} is already in a trade.",
            )

        # Parse the offer
        proposer_offer, opponent_offer, err = parse_trade_offer(args)
        if err:
            return TradeResult(False, err)

        # Validate proposer has what they're offering
        if proposer_offer.stars > 0 or proposer_offer.items:
            validation_err = self._validate_offer(
                proposer_id, proposer_name, proposer_offer
            )
            if validation_err:
                return TradeResult(False, validation_err)

        # Create session
        session = TradeSession(
            proposer_id=proposer_id,
            proposer_name=proposer_name,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            proposer_offer=proposer_offer,
            opponent_offer=opponent_offer,
            channel_id=channel_id,
        )
        self._sessions[proposer_id] = session
        self._user_in_trade[proposer_id] = proposer_id
        self._user_in_trade[opponent_id] = proposer_id

        # Schedule auto-timeout
        session.task = asyncio.create_task(
            self._pending_timeout(proposer_id)
        )

        return TradeResult(True, "", session=session)

    async def _pending_timeout(self, proposer_id: int) -> None:
        """Auto-cancel a pending trade after timeout."""
        try:
            await asyncio.sleep(TRADE_PENDING_TIMEOUT)
            session = self._sessions.get(proposer_id)
            if session and session.state == TradeState.PENDING:
                session.state = TradeState.CANCELLED
                channel_id = session.channel_id
                self._cleanup_session(proposer_id)
                if self._trade_callback:
                    try:
                        await self._trade_callback(
                            "timeout", proposer_id, channel_id, session
                        )
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass

    def accept_trade(self, user_id: int, username: str) -> TradeResult:
        """
        Accept a pending trade (must be the opponent).

        Validates:
        - User is in a trade as opponent
        - Trade is in PENDING state
        - Both parties still have their offered items/stars
        """
        session = self.get_session_for_user(user_id)
        if session is None:
            return TradeResult(False, "You don't have a pending trade.")

        if user_id != session.opponent_id:
            return TradeResult(
                False,
                "Only the other party can accept. You proposed this trade.",
            )

        if session.state != TradeState.PENDING:
            return TradeResult(False, "This trade is no longer pending.")

        # Re-validate both sides
        if session.proposer_offer.stars > 0 or session.proposer_offer.items:
            err = self._validate_offer(
                session.proposer_id, session.proposer_name, session.proposer_offer
            )
            if err:
                self._cleanup_session(session.proposer_id)
                return TradeResult(
                    False,
                    f"Trade cancelled — {session.proposer_name} {err}",
                )

        if session.opponent_offer.stars > 0 or session.opponent_offer.items:
            err = self._validate_offer(
                session.opponent_id, session.opponent_name, session.opponent_offer
            )
            if err:
                self._cleanup_session(session.proposer_id)
                return TradeResult(False, f"Trade cancelled — {username} {err}")

        # Cancel the pending timeout task
        if session.task and not session.task.done():
            session.task.cancel()

        # Transition to COUNTDOWN
        session.state = TradeState.COUNTDOWN
        session.task = asyncio.create_task(
            self._countdown_then_execute(session.proposer_id)
        )

        return TradeResult(True, "", session=session)

    async def _countdown_then_execute(self, proposer_id: int) -> None:
        """Wait for countdown, then execute the trade."""
        try:
            await asyncio.sleep(TRADE_COUNTDOWN_SECONDS)
            session = self._sessions.get(proposer_id)
            if session and session.state == TradeState.COUNTDOWN:
                await self._execute_trade(session)
        except asyncio.CancelledError:
            pass

    async def _execute_trade(self, session: TradeSession) -> None:
        """Re-validate and execute the trade, transferring items and stars."""
        # Final validation — triple check
        if session.proposer_offer.stars > 0 or session.proposer_offer.items:
            err = self._validate_offer(
                session.proposer_id, session.proposer_name, session.proposer_offer
            )
            if err:
                session.state = TradeState.CANCELLED
                channel_id = session.channel_id
                self._cleanup_session(session.proposer_id)
                if self._trade_callback:
                    try:
                        await self._trade_callback(
                            "failed", session.proposer_id, channel_id, session,
                            f"Trade failed — {session.proposer_name} {err}",
                        )
                    except Exception:
                        pass
                return

        if session.opponent_offer.stars > 0 or session.opponent_offer.items:
            err = self._validate_offer(
                session.opponent_id, session.opponent_name, session.opponent_offer
            )
            if err:
                session.state = TradeState.CANCELLED
                channel_id = session.channel_id
                self._cleanup_session(session.proposer_id)
                if self._trade_callback:
                    try:
                        await self._trade_callback(
                            "failed", session.proposer_id, channel_id, session,
                            f"Trade failed — {session.opponent_name} {err}",
                        )
                    except Exception:
                        pass
                return

        # Execute transfers
        self._transfer_offer(
            session.proposer_id, session.proposer_name,
            session.opponent_id, session.opponent_name,
            session.proposer_offer,
        )
        self._transfer_offer(
            session.opponent_id, session.opponent_name,
            session.proposer_id, session.proposer_name,
            session.opponent_offer,
        )

        session.state = TradeState.COMPLETED
        channel_id = session.channel_id
        self._cleanup_session(session.proposer_id)

        if self._trade_callback:
            try:
                await self._trade_callback(
                    "completed", session.proposer_id, channel_id, session
                )
            except Exception:
                pass

    def cancel_trade(self, user_id: int) -> TradeResult:
        """
        Cancel a trade. Either party can cancel at any point.

        Returns TradeResult with the cancelled session.
        """
        session = self.get_session_for_user(user_id)
        if session is None:
            return TradeResult(False, "You don't have an active trade.")

        session.state = TradeState.CANCELLED
        proposer_id = session.proposer_id
        self._cleanup_session(proposer_id)
        return TradeResult(True, "Trade cancelled.", session=session)

    def format_offer(self, offer: TradeOffer) -> str:
        """Public access to offer formatting."""
        return self._format_offer(offer)

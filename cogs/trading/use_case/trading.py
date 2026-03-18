"""Trading use-cases for player-to-player trades."""

from __future__ import annotations

from typing import Optional

from cogs.shop.constants import SHOP_ITEMS
from cogs.trading.dto import TradeOffer, TradeResult
from database.repository import UserRepository

MAX_TRADE_ITEMS = 3


class TradeUseCases:
    """Handles trade locking, inventory queries, validation, and execution."""

    def __init__(self, repository: UserRepository | None = None):
        self.repo = repository or UserRepository()
        self._user_in_trade: dict[int, int] = {}  # user_id -> proposer_id

    # ------------------------------------------------------------------
    # Trade lock management
    # ------------------------------------------------------------------

    def start_trade(self, proposer_id: int, opponent_id: int) -> Optional[str]:
        """Register both users as in-trade. Returns error message or None."""
        if proposer_id == opponent_id:
            return "You can't trade with yourself."
        if proposer_id in self._user_in_trade:
            return "You're already in a trade. Cancel it first."
        if opponent_id in self._user_in_trade:
            return "That player is already in a trade."
        self._user_in_trade[proposer_id] = proposer_id
        self._user_in_trade[opponent_id] = proposer_id
        return None

    def end_trade(self, proposer_id: int, opponent_id: int) -> None:
        """Remove both users from the trade lock."""
        self._user_in_trade.pop(proposer_id, None)
        self._user_in_trade.pop(opponent_id, None)

    def is_in_trade(self, user_id: int) -> bool:
        return user_id in self._user_in_trade

    # ------------------------------------------------------------------
    # Item queries
    # ------------------------------------------------------------------

    def get_tradeable_items(self, user_id: int) -> list[tuple[str, str, str, int]]:
        """Return all tradeable items for a user.

        Returns list of ``(item_key, display_name, emoji, count)``.
        Equipment items always have count=1 (whole-item trade).
        """
        items: list[tuple[str, str, str, int]] = []
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT item_key, uses FROM user_equipment "
                "WHERE user_id = ? AND uses > 0",
                (user_id,),
            )
            for row in cursor.fetchall():
                key = row["item_key"]
                name, emoji = self.item_display(key)
                items.append((key, name, emoji, 1))

            cursor.execute(
                "SELECT item_key, COUNT(*) as cnt FROM user_inventory_items "
                "WHERE user_id = ? GROUP BY item_key",
                (user_id,),
            )
            for row in cursor.fetchall():
                key = row["item_key"]
                name, emoji = self.item_display(key)
                items.append((key, name, emoji, row["cnt"]))

        return sorted(items, key=lambda x: x[1])

    @staticmethod
    def item_display(item_key: str) -> tuple[str, str]:
        """Return ``(display_name, emoji)`` for an item key."""
        shop = SHOP_ITEMS.get(item_key)
        if shop:
            return shop.display_name, shop.emoji
        return item_key.replace("_", " ").title(), "\U0001f4e6"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_offer(self, user_id: int, offer: TradeOffer) -> Optional[str]:
        """Check that the user can fulfil their offer. Returns error or None."""
        if offer.stars > 0:
            user = self.repo.get_user(user_id, "")
            if user.stars < offer.stars:
                return f"Not enough stars (have {user.stars}, need {offer.stars})."

        if offer.items:
            needed: dict[str, int] = {}
            for key in offer.items:
                needed[key] = needed.get(key, 0) + 1
            with self.repo.db.get_cursor() as cursor:
                for key, qty in needed.items():
                    # Equipment table
                    cursor.execute(
                        "SELECT uses FROM user_equipment "
                        "WHERE user_id = ? AND item_key = ?",
                        (user_id, key),
                    )
                    equip = cursor.fetchone()
                    if equip:
                        if qty > 1:
                            name, _ = self.item_display(key)
                            return f"You only have one {name}."
                        continue
                    # Inventory items
                    cursor.execute(
                        "SELECT COUNT(*) as cnt FROM user_inventory_items "
                        "WHERE user_id = ? AND item_key = ?",
                        (user_id, key),
                    )
                    cnt = cursor.fetchone()["cnt"]
                    if cnt < qty:
                        name, _ = self.item_display(key)
                        return f"Not enough {name} (have {cnt}, need {qty})."
        return None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_trade(
        self,
        proposer_id: int,
        proposer_name: str,
        opponent_id: int,
        opponent_name: str,
        proposer_offer: TradeOffer,
        opponent_offer: TradeOffer,
    ) -> TradeResult:
        """Validate and execute the trade atomically."""
        err = self.validate_offer(proposer_id, proposer_offer)
        if err:
            return TradeResult(False, f"{proposer_name}: {err}")
        err = self.validate_offer(opponent_id, opponent_offer)
        if err:
            return TradeResult(False, f"{opponent_name}: {err}")

        try:
            with self.repo.db.get_connection() as conn:
                cursor = conn.cursor()
                for uid, uname in [
                    (proposer_id, proposer_name),
                    (opponent_id, opponent_name),
                ]:
                    cursor.execute(
                        "INSERT INTO noodle_stars (user_id, username, stars, bank) "
                        "VALUES (?, ?, 0, 0) ON CONFLICT(user_id) DO NOTHING",
                        (uid, uname),
                    )
                    self.repo._ensure_inventory_row(cursor, uid)

                self._transfer_stars(
                    cursor, proposer_id, proposer_name,
                    opponent_id, opponent_name, proposer_offer.stars,
                )
                self._transfer_items(cursor, proposer_id, opponent_id, proposer_offer.items)

                self._transfer_stars(
                    cursor, opponent_id, opponent_name,
                    proposer_id, proposer_name, opponent_offer.stars,
                )
                self._transfer_items(cursor, opponent_id, proposer_id, opponent_offer.items)

        except Exception as exc:
            return TradeResult(False, f"Trade failed — {exc}")

        return TradeResult(True, "Trade completed successfully!")

    # ------------------------------------------------------------------
    # Transfer helpers (called inside a transaction)
    # ------------------------------------------------------------------

    @staticmethod
    def _transfer_stars(cursor, from_id, from_name, to_id, to_name, amount):
        if amount <= 0:
            return
        cursor.execute(
            "SELECT stars FROM noodle_stars WHERE user_id = ?", (from_id,),
        )
        row = cursor.fetchone()
        from_stars = row["stars"] if row else 0
        if from_stars < amount:
            raise ValueError(f"Insufficient stars ({from_stars} < {amount})")
        cursor.execute(
            "UPDATE noodle_stars SET stars = ?, username = ? WHERE user_id = ?",
            (from_stars - amount, from_name, from_id),
        )
        cursor.execute(
            "UPDATE noodle_stars SET stars = stars + ?, username = ? WHERE user_id = ?",
            (amount, to_name, to_id),
        )

    @staticmethod
    def _transfer_items(cursor, from_id, to_id, items: list[str]):
        for item_key in items:
            # Try equipment table first
            cursor.execute(
                "SELECT uses FROM user_equipment "
                "WHERE user_id = ? AND item_key = ?",
                (from_id, item_key),
            )
            equip_row = cursor.fetchone()
            if equip_row:
                uses = equip_row["uses"]
                cursor.execute(
                    "DELETE FROM user_equipment "
                    "WHERE user_id = ? AND item_key = ?",
                    (from_id, item_key),
                )
                cursor.execute(
                    "INSERT INTO user_equipment (user_id, item_key, uses) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(user_id, item_key) DO UPDATE SET uses = uses + ?",
                    (to_id, item_key, uses, uses),
                )
                continue

            # Inventory items — move one row
            cursor.execute(
                "SELECT id FROM user_inventory_items "
                "WHERE user_id = ? AND item_key = ? LIMIT 1",
                (from_id, item_key),
            )
            inv_row = cursor.fetchone()
            if inv_row:
                cursor.execute(
                    "UPDATE user_inventory_items SET user_id = ? WHERE id = ?",
                    (to_id, inv_row["id"]),
                )
                continue

            raise ValueError(f"Item not found: {item_key}")

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_offer(self, offer: TradeOffer) -> str:
        """Format a TradeOffer as human-readable lines."""
        parts: list[str] = []
        if offer.stars > 0:
            parts.append(f"\u2b50 **{offer.stars}** stars")
        # Group duplicate items
        counts: dict[str, int] = {}
        for key in offer.items:
            counts[key] = counts.get(key, 0) + 1
        for key, qty in counts.items():
            name, emoji = self.item_display(key)
            if qty > 1:
                parts.append(f"{emoji} **{qty}\u00d7** {name}")
            else:
                parts.append(f"{emoji} {name}")
        return "\n".join(parts) if parts else "*nothing*"

"""Blaze Goblin trader use cases."""

from cogs.aetherdepths.constants import (
    BLAZE_GOBLIN_BUY_MARKUP,
    BLAZE_GOBLIN_MAX_STASH,
    BLAZE_GOBLIN_SELL_RATE,
    BLAZE_GOBLIN_STOCK,
)
from cogs.shop.resources import get_resource
from database.repository import UserRepository


class BlazeGoblinUseCases:
    """Blaze Goblin encounter logic."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def get_stock(self, level: int) -> list[tuple[str, str, int]]:
        """Get buy stock for the goblin at a given level.

        Returns list of (item_key, display_name, price).
        """
        stock = BLAZE_GOBLIN_STOCK.get(level, BLAZE_GOBLIN_STOCK[1])
        result = []
        for item_key, base_price in stock:
            price = int(base_price * BLAZE_GOBLIN_BUY_MARKUP)
            res = get_resource(item_key)
            display = res.display_name if res else item_key.replace("_", " ").title()
            result.append((item_key, display, price))
        return result

    def deposit_stars(self, user_id: int, username: str, amount: int) -> tuple[bool, str]:
        """Move stars from wallet to bank."""
        current_stars = self.repo.get_user_stars(user_id, username)
        if amount <= 0:
            return False, "Amount must be positive!"
        if amount > current_stars:
            return False, f"You only have **{current_stars:,}** stars in your wallet!"
        self.repo.update_user_stars(user_id, username, current_stars - amount)
        current_bank = self.repo.get_user_bank(user_id)
        self.repo.update_user_bank(user_id, username, current_bank + amount)
        return True, f"Deposited **{amount:,}** stars to your bank! 🏦"

    def sell_item(self, user_id: int, item_id: int) -> tuple[bool, str, int]:
        """Sell an inventory item at goblin rates (70% value).

        Returns (success, message, stars_earned).
        """
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, item_key, base_sell_value FROM user_inventory_items WHERE id = ? AND user_id = ?",
                (item_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                return False, "Item not found!", 0

            sell_value = max(1, int(row["base_sell_value"] * BLAZE_GOBLIN_SELL_RATE))
            item_key = row["item_key"]

            cursor.execute(
                "DELETE FROM user_inventory_items WHERE id = ? AND user_id = ?",
                (item_id, user_id),
            )

        # Add stars
        res = get_resource(item_key)
        display = res.display_name if res else item_key.replace("_", " ").title()
        username = ""  # not needed for adding
        current = self.repo.get_user_stars(user_id, username)
        self.repo.update_user_stars(user_id, username, current + sell_value)

        return True, f"Sold **{display}** for **{sell_value}** stars (goblin rate).", sell_value

    # Equipment items that route through _OWNERSHIP_MAP instead of add_item
    _EQUIPMENT_ITEMS = {"jackhammer"}

    def buy_item(self, user_id: int, username: str, item_key: str, price: int) -> tuple[bool, str]:
        """Buy an item from the goblin's stock."""
        # Check if player already owns equipment items
        if item_key in self._EQUIPMENT_ITEMS:
            inv = self.repo.get_user_inventory(user_id)
            if inv.get(item_key, 0) > 0:
                return False, "You already own that item!"

        current_stars = self.repo.get_user_stars(user_id, username)
        if current_stars < price:
            return False, f"You need **{price}** stars! You have **{current_stars:,}**."

        self.repo.update_user_stars(user_id, username, current_stars - price)

        res = get_resource(item_key)
        display = res.display_name if res else item_key.replace("_", " ").title()

        if item_key in self._EQUIPMENT_ITEMS:
            # Equipment: route through update_user_inventory (hits _OWNERSHIP_MAP)
            self.repo.update_user_inventory(user_id, item_key, 1)
        else:
            # Consumable: add to inventory_items table
            category = res.category if res else "consumable"
            sell_value = int(price / BLAZE_GOBLIN_BUY_MARKUP)
            self.repo.add_item(user_id, item_key, category, sell_value)

        return True, f"Bought **{display}** for **{price}** stars!"

    def stash_item(self, user_id: int, item_id: int) -> tuple[bool, str]:
        """Stash an item (protected from death)."""
        count = self.repo.get_stash_count(user_id)
        if count >= BLAZE_GOBLIN_MAX_STASH:
            return False, f"Stash is full! Max **{BLAZE_GOBLIN_MAX_STASH}** items."

        success = self.repo.stash_item(user_id, item_id)
        if not success:
            return False, "Item not found in your inventory!"

        return True, "Item stashed! It will survive death. 📦"

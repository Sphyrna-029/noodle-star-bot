"""Shop service for store and purchases."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from config import SHOP_ITEMS, get_item_by_alias
from database.repository import UserRepository


@dataclass
class PurchaseResult:
    """Result of a purchase operation."""

    success: bool
    message: str
    item_name: str = ""
    item_emoji: str = ""
    price: int = 0
    new_balance: int = 0


@dataclass
class ShopItem:
    """Represents an item in the shop."""

    key: str
    price: int
    db_column: str
    consumable: bool
    emoji: str
    display_name: str
    description: str


class ShopService:
    """Handles all shop-related business logic."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def get_items(self) -> List[ShopItem]:
        """Get all items available in the shop."""
        items = []
        for key, data in SHOP_ITEMS.items():
            items.append(
                ShopItem(
                    key=key,
                    price=data["price"],
                    db_column=data["db_column"],
                    consumable=data["consumable"],
                    emoji=data["emoji"],
                    display_name=data["display_name"],
                    description=data["description"],
                )
            )
        return items

    def get_item(self, item_name: str) -> Optional[ShopItem]:
        """Get a shop item by name or alias."""
        item_data = get_item_by_alias(item_name)
        if item_data is None:
            return None

        return ShopItem(
            key=item_data["key"],
            price=item_data["price"],
            db_column=item_data["db_column"],
            consumable=item_data["consumable"],
            emoji=item_data["emoji"],
            display_name=item_data["display_name"],
            description=item_data["description"],
        )

    def buy(self, user_id: int, username: str, item_name: str) -> PurchaseResult:
        """
        Purchase an item from the store.

        Args:
            user_id: Discord user ID
            username: Discord username
            item_name: Name of item to purchase

        Returns:
            PurchaseResult with outcome
        """
        if item_name is None:
            return PurchaseResult(
                success=False,
                message="Please specify an item to buy! Use `!store` to see available items.",
            )

        item = self.get_item(item_name)
        if item is None:
            return PurchaseResult(
                success=False,
                message="That item doesn't exist! Use `!store` to see available items.",
            )

        current_stars = self.repo.get_user_stars(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)

        # Check if user has enough stars
        if current_stars < item.price:
            return PurchaseResult(
                success=False,
                message=f"You need **{item.price}** stars to buy {item.emoji} **{item.display_name}**!\nYou only have **{current_stars}** stars.",
                item_name=item.display_name,
                item_emoji=item.emoji,
                price=item.price,
            )

        # Check if user already owns gold pickaxe (permanent item)
        if item.db_column == "gold_pickaxe" and inventory["gold_pickaxe"] > 0:
            return PurchaseResult(
                success=False,
                message=f"You already own a {item.emoji} **{item.display_name}**!",
                item_name=item.display_name,
                item_emoji=item.emoji,
            )

        # Deduct stars
        new_stars = current_stars - item.price
        self.repo.update_user_stars(user_id, username, new_stars)

        # Add item to inventory
        current_amount = inventory[item.db_column]
        self.repo.update_user_inventory(user_id, item.db_column, current_amount + 1)

        return PurchaseResult(
            success=True,
            message=f"Purchased {item.emoji} **{item.display_name}** for **{item.price}** stars!",
            item_name=item.display_name,
            item_emoji=item.emoji,
            price=item.price,
            new_balance=new_stars,
        )

    def get_inventory(self, user_id: int) -> Dict[str, int]:
        """Get user's inventory."""
        return self.repo.get_user_inventory(user_id)

    def get_inventory_display(self, user_id: int) -> List[str]:
        """
        Get user's inventory formatted for display.

        Returns list of formatted strings for each owned item.
        """
        inventory = self.repo.get_user_inventory(user_id)
        items = []

        if inventory["gold_pickaxe"] > 0:
            items.append("⛏️ **Gold Pickaxe** (Permanent)")

        if inventory["helmet"] > 0:
            items.append(f'🪖 **Mining Helmet** x{inventory["helmet"]}')

        if inventory["sword"] > 0:
            items.append(f'⚔️ **Sword** x{inventory["sword"]}')

        if inventory["raw_potato"] > 0:
            items.append(f'🥔 **Raw Potato** x{inventory["raw_potato"]}')

        if inventory["golden_mushroom"] > 0:
            items.append(f'🍄 **Golden Mushroom** x{inventory["golden_mushroom"]}')

        return items

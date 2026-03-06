"""Shop use-cases for store and purchases."""

from typing import Dict, List, Optional

from cogs.shop.constants import SHOP_ITEMS, get_item_by_alias
from database.repository import UserRepository
from ..dto import PurchaseResult, ShopItem


class ShopUseCases:
    """Handles all shop-related business logic."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()
        self._non_store_items = {"golden_mushroom"}

    def get_items(self) -> List[ShopItem]:
        """Get all items available in the shop."""
        items = []
        for key, data in SHOP_ITEMS.items():
            if key in self._non_store_items:
                continue
            items.append(
                ShopItem(
                    key=key,
                    price=data.price,
                    db_column=data.db_column,
                    consumable=data.consumable,
                    emoji=data.emoji,
                    display_name=data.display_name,
                    description=data.description,
                )
            )
        return items

    def get_item(self, item_name: str) -> Optional[ShopItem]:
        """Get a shop item by name or alias."""
        match = get_item_by_alias(item_name)
        if match is not None:
            key, shop_item = match
            return ShopItem(
                key=key,
                price=shop_item.price,
                db_column=shop_item.db_column,
                consumable=shop_item.consumable,
                emoji=shop_item.emoji,
                display_name=shop_item.display_name,
                description=shop_item.description,
            )

    @staticmethod
    def _parse_buy_request(item_name: str, quantity: int) -> tuple[str, int]:
        """
        Parse buy input into normalized item name and quantity.

        Supports:
        - !buy potato 5
        - !buy potato x5
        """
        clean_item_name = item_name.strip()
        if quantity != 1:
            return clean_item_name, quantity

        parts = clean_item_name.rsplit(maxsplit=1)
        if len(parts) != 2:
            return clean_item_name, quantity

        maybe_qty = parts[1]
        if maybe_qty.lower().startswith("x"):
            maybe_qty = maybe_qty[1:]

        if maybe_qty == "":
            return clean_item_name, quantity

        try:
            parsed_quantity = int(maybe_qty)
        except ValueError:
            return clean_item_name, quantity

        return parts[0].strip(), parsed_quantity

    def buy(
        self,
        user_id: int,
        username: str,
        item_name: str,
        quantity: int = 1,
    ) -> PurchaseResult:
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

        parsed_item_name, quantity = self._parse_buy_request(item_name, quantity)
        if not parsed_item_name:
            return PurchaseResult(
                success=False,
                message="Please specify an item to buy! Use `!store` to see available items.",
            )

        if quantity <= 0:
            return PurchaseResult(
                success=False,
                message="Quantity must be a positive number.",
            )

        item = self.get_item(parsed_item_name)
        if item is None:
            return PurchaseResult(
                success=False,
                message="That item doesn't exist! Use `!store` to see available items.",
            )

        if item.key in self._non_store_items:
            return PurchaseResult(
                success=False,
                message="Golden Mushrooms are not sold in the store. Harvest crops with `!harvest` to find them.",
                item_name=item.display_name,
                item_emoji=item.emoji,
                quantity=quantity,
            )

        current_stars = self.repo.get_user_stars(user_id, username)
        inventory = self.repo.get_user_inventory(user_id)
        total_price = item.price * quantity
        display_name = (
            f"{item.display_name} x{quantity}" if quantity > 1 else item.display_name
        )

        # Check if user has enough stars
        if current_stars < total_price:
            max_affordable = current_stars // item.price
            return PurchaseResult(
                success=False,
                message=(
                    f"You need **{total_price}** stars to buy {item.emoji} "
                    f"**{display_name}**!\n"
                    f"You only have **{current_stars}** stars "
                    f"(max affordable: **{max_affordable}**)."
                ),
                item_name=item.display_name,
                item_emoji=item.emoji,
                price=total_price,
                quantity=quantity,
            )

        # Permanent items cannot be stacked
        if not item.consumable and quantity > 1:
            return PurchaseResult(
                success=False,
                message=(
                    f"{item.emoji} **{item.display_name}** is a permanent item, "
                    "so you can only buy one."
                ),
                item_name=item.display_name,
                item_emoji=item.emoji,
                quantity=quantity,
            )

        # Check prerequisite for rocket ship
        if item.key == "rocket_ship":
            mine_level = inventory.get("mine_level", 1)
            if mine_level < 5:
                return PurchaseResult(
                    success=False,
                    message=f"You need mine level 5 to buy a {item.emoji} **{item.display_name}**! You're at level {mine_level}.",
                    item_name=item.display_name,
                    item_emoji=item.emoji,
                )

        # Check if user already owns permanent item
        if not item.consumable and inventory[item.db_column] > 0:
            return PurchaseResult(
                success=False,
                message=f"You already own a {item.emoji} **{item.display_name}**!",
                item_name=item.display_name,
                item_emoji=item.emoji,
            )

        # Deduct stars
        new_stars = current_stars - total_price
        self.repo.update_user_stars(user_id, username, new_stars)

        # Add item to inventory
        current_amount = inventory[item.db_column]
        self.repo.update_user_inventory(user_id, item.db_column, current_amount + quantity)

        return PurchaseResult(
            success=True,
            message=(
                f"Purchased {item.emoji} **{display_name}** "
                f"for **{total_price}** stars!"
            ),
            item_name=item.display_name,
            item_emoji=item.emoji,
            price=total_price,
            quantity=quantity,
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
            items.append(f"🪖 **Mining Helmet** x{inventory['helmet']}")

        if inventory["sword"] > 0:
            items.append(f"⚔️ **Sword** x{inventory['sword']}")

        if inventory["raw_potato"] > 0:
            items.append(f"🥔 **Raw Potato** x{inventory['raw_potato']}")

        if inventory["golden_mushroom"] > 0:
            items.append(f"🍄 **Golden Mushroom** x{inventory['golden_mushroom']}")

        if inventory["telescope"] > 0:
            items.append("📷 **Telescope** (Permanent)")

        if inventory.get("golden_axe", 0) > 0:
            items.append(f"🪓 **Golden Axe** ({inventory['golden_axe']} uses)")

        if inventory.get("mithril_shield", 0) > 0:
            items.append(f"🛡️ **Mithril Shield** ({inventory['mithril_shield']} uses)")

        if inventory.get("rune_fragment", 0) > 0:
            items.append(f"🪨 **Rune Fragment** ({inventory['rune_fragment']} uses)")

        if inventory.get("fossilized_noodle", 0) > 0:
            items.append(f"🍜 **Fossilized Noodle** ({inventory['fossilized_noodle']} uses)")

        if inventory.get("bucktail_jig", 0) > 0:
            jig_count = inventory["bucktail_jig"]
            active = " *(1 active)*" if inventory.get("jig_active", 0) else ""
            items.append(f"🎣 **Bucktail Jig** x{jig_count}{active}")

        if inventory.get("ray_gun", 0) > 0:
            items.append(f"🔫 **Ray-Gun** ({inventory['ray_gun']} uses)")

        if inventory.get("star_magnet", 0) > 0:
            items.append(f"🧲 **Star Magnet** ({inventory['star_magnet']} uses)")

        if inventory.get("lucky_charm", 0) > 0:
            items.append(f"🍀 **Lucky Charm** ({inventory['lucky_charm']} uses)")

        if inventory.get("heart_of_leviathan", 0) > 0:
            items.append(f"💜 **Heart of Leviathan** ({inventory['heart_of_leviathan']} uses)")

        if inventory.get("rocket_ship", 0) > 0:
            items.append("🚀 **Rocket Ship** (Permanent)")

        # Fishing bait
        if inventory.get("bait_worm", 0) > 0:
            items.append(f"🪱 **Worm Bait** x{inventory['bait_worm']}")

        if inventory.get("bait_herring", 0) > 0:
            items.append(f"🐟 **Herring Bait** x{inventory['bait_herring']}")

        if inventory.get("bait_sturgeon", 0) > 0:
            items.append(f"🐋 **Sturgeon Bait** x{inventory['bait_sturgeon']}")

        return items

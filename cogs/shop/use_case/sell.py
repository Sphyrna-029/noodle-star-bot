"""Sell use-case — convert inventory items back to stars."""

from cogs.locations.use_case import LocationUseCases
from cogs.locations.constants import LOCATIONS
from cogs.shop.resources import (
    get_resource,
    resolve_item,
    resolve_category,
    get_home_location,
    RESOURCES,
)
from cogs.shop.dto import SellResult, TrashResult
from database.repository import UserRepository


class SellUseCases:
    """Handles selling and trashing inventory items."""

    NOODLE_TOWN_BONUS = 25   # +25%
    NON_HOME_BONUS = 10      # +10%
    MAGNET_BONUS = 15         # +15%

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()
        self.location_uc = LocationUseCases()

    def _get_location_bonus(self, user_id: int, category: str) -> tuple[int, str]:
        """Return (bonus_percent, location_name) for the user's current location."""
        location_key = self.location_uc.get_location(user_id)
        loc = LOCATIONS.get(location_key)
        location_name = loc.name if loc else "Unknown"

        if location_key == "noodle_town":
            return self.NOODLE_TOWN_BONUS, location_name

        home = get_home_location(category)
        if location_key == home:
            return 0, location_name

        # At a non-home activity location
        return self.NON_HOME_BONUS, location_name

    def sell(
        self,
        user_id: int,
        username: str,
        target: str,
        count: int = 0,
    ) -> SellResult:
        """Sell items from inventory.

        target can be:
        - An item name/alias (sells all or count of that item)
        - "all" (sells everything with base_sell_value > 0)
        - A category name (sells all items in that category)
        """
        # Ensure user exists
        self.repo.get_user_stars(user_id, username)

        count = max(0, count)
        target_lower = target.strip().lower()

        # Handle "all"
        if target_lower == "all":
            return self._sell_all(user_id, username)

        # Check if it's a category
        category = resolve_category(target_lower)
        if category is not None:
            return self._sell_category(user_id, username, category)

        # Try as item name
        resource = resolve_item(target_lower)
        if resource is None:
            return SellResult(
                success=False,
                message=f"Unknown item: **{target}**. Check `!inventory` for your items.",
            )

        return self._sell_item(user_id, username, resource.item_key, count)

    def _sell_item(self, user_id: int, username: str, item_key: str, count: int) -> SellResult:
        """Sell a specific item type."""
        # Get items from inventory
        items = self._get_user_items_by_key(user_id, item_key)
        if not items:
            resource = get_resource(item_key)
            name = resource.display_name if resource else item_key
            return SellResult(
                success=False,
                message=f"You don't have any **{name}** to sell.",
            )

        # Filter out zero-value items
        sellable = [i for i in items if i["base_sell_value"] > 0]
        if not sellable:
            resource = get_resource(item_key)
            name = resource.display_name if resource else item_key
            return SellResult(
                success=False,
                message=f"**{name}** has no sell value. Use `!trash {name.lower()}` to discard it.",
            )

        # Limit by count if specified
        if count > 0:
            sellable = sellable[:count]

        return self._execute_sell(user_id, username, sellable)

    def _sell_category(self, user_id: int, username: str, category: str) -> SellResult:
        """Sell all items in a category."""
        items = self.repo.get_items_by_category(user_id, category)
        sellable = [i for i in items if i["base_sell_value"] > 0]
        if not sellable:
            return SellResult(
                success=False,
                message=f"You don't have any sellable **{category}** items.",
            )
        return self._execute_sell(user_id, username, sellable)

    def _sell_all(self, user_id: int, username: str) -> SellResult:
        """Sell everything with value > 0."""
        all_items = self.repo.get_inventory_items(user_id)
        sellable = [i for i in all_items if i["base_sell_value"] > 0]
        if not sellable:
            return SellResult(
                success=False,
                message="You don't have anything to sell! Go mining, fishing, or farming first.",
            )
        return self._execute_sell(user_id, username, sellable)

    def _execute_sell(self, user_id: int, username: str, items: list[dict]) -> SellResult:
        """Execute the sell: calculate bonuses, remove items, add stars."""
        # Determine the primary category for location bonus
        # Use the most common category among items being sold
        category_counts: dict[str, int] = {}
        for item in items:
            cat = item.get("category", "consumable")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        primary_category = max(category_counts, key=category_counts.get)

        # Location bonus
        location_bonus_pct, location_name = self._get_location_bonus(user_id, primary_category)

        # Star Magnet check
        magnet_uses = self.repo.get_equipment_uses(user_id, "star_magnet")
        magnet_bonus_pct = 0
        if magnet_uses > 0:
            magnet_bonus_pct = self.MAGNET_BONUS
            self.repo.consume_equipment_use(user_id, "star_magnet")
            magnet_uses -= 1

        # Calculate base total
        base_total = sum(i["base_sell_value"] for i in items)

        # Apply bonuses (additive)
        total_bonus_pct = location_bonus_pct + magnet_bonus_pct
        bonus_stars = int(base_total * total_bonus_pct / 100)
        total_stars = base_total + bonus_stars

        # Group sold items for display
        sold_groups: dict[str, list[int]] = {}  # item_key -> [base_sell_values]
        for item in items:
            key = item["item_key"]
            if key not in sold_groups:
                sold_groups[key] = []
            sold_groups[key].append(item["base_sell_value"])

        items_sold = []
        for key, values in sold_groups.items():
            resource = get_resource(key)
            display = resource.display_name if resource else key
            items_sold.append((key, display, len(values), sum(values)))

        # Remove items from inventory (by id)
        ids_to_remove = [i["id"] for i in items]
        self._remove_items_by_ids(user_id, ids_to_remove)

        # Add stars
        current_stars = self.repo.get_user_stars(user_id, username)
        new_balance = current_stars + total_stars
        self.repo.update_user_stars(user_id, username, new_balance)

        return SellResult(
            success=True,
            message="Sold!",
            items_sold=items_sold,
            base_total=base_total,
            location_bonus_pct=location_bonus_pct,
            location_name=location_name,
            magnet_bonus_pct=magnet_bonus_pct,
            magnet_uses_left=magnet_uses,
            bonus_stars=bonus_stars,
            total_stars=total_stars,
            new_balance=new_balance,
        )

    def trash(self, user_id: int, username: str, target: str, count: int = 0) -> TrashResult:
        """Discard items from inventory without earning stars."""
        count = max(0, count)
        self.repo.get_user_stars(user_id, username)

        resource = resolve_item(target)
        if resource is None:
            return TrashResult(success=False, message=f"Unknown item: **{target}**.")

        items = self._get_user_items_by_key(user_id, resource.item_key)
        if not items:
            return TrashResult(
                success=False,
                message=f"You don't have any **{resource.display_name}** to trash.",
            )

        to_remove = items if count <= 0 else items[:count]
        ids_to_remove = [i["id"] for i in to_remove]
        self._remove_items_by_ids(user_id, ids_to_remove)

        return TrashResult(
            success=True,
            message=f"Trashed **{len(to_remove)}x** {resource.emoji} {resource.display_name}.",
            item_name=resource.display_name,
            item_emoji=resource.emoji,
            count=len(to_remove),
        )

    def _get_user_items_by_key(self, user_id: int, item_key: str) -> list[dict]:
        """Get all inventory items matching an item_key."""
        return self.repo.get_items_by_key(user_id, item_key)

    def _remove_items_by_ids(self, user_id: int, ids: list[int]) -> None:
        """Remove specific inventory item rows by id."""
        self.repo.remove_items_by_ids(user_id, ids)

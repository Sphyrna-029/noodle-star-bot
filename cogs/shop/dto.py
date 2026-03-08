"""DTOs for shop use-cases."""

from dataclasses import dataclass


@dataclass(slots=True)
class PurchaseResult:
    """Result of a purchase operation."""

    success: bool
    message: str
    item_name: str = ""
    item_emoji: str = ""
    price: int = 0
    quantity: int = 1
    new_balance: int = 0


@dataclass(slots=True)
class ShopItem:
    """Represents an item in the shop."""

    key: str
    price: int
    db_column: str
    consumable: bool
    emoji: str
    display_name: str
    description: str
    category: str

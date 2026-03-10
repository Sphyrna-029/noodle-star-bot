"""DTOs for shop use-cases."""

from dataclasses import dataclass, field


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


@dataclass(slots=True)
class SellResult:
    """Result of a sell operation."""

    success: bool
    message: str
    items_sold: list[tuple[str, str, int, int]] = field(default_factory=list)  # (item_key, display_name, count, base_value)
    base_total: int = 0
    location_bonus_pct: int = 0
    location_name: str = ""
    magnet_bonus_pct: int = 0
    magnet_uses_left: int = 0
    bonus_stars: int = 0
    total_stars: int = 0
    new_balance: int = 0


@dataclass(slots=True)
class TrashResult:
    """Result of trashing items."""

    success: bool
    message: str
    item_name: str = ""
    item_emoji: str = ""
    count: int = 0

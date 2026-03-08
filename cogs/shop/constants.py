from typing import Final

from config.models import ShopItem

__all__ = ["SHOP_ITEMS", "get_item_by_alias"]

SHOP_ITEMS: Final[dict[str, ShopItem]] = {
    "gold_pickaxe": ShopItem(
        price=500,
        db_column="gold_pickaxe",
        consumable=False,
        emoji="⛏️",
        display_name="Gold Pickaxe",
        description="Permanently increases your mining luck! Find rare minerals more often.",
        aliases=("gold pickaxe", "pickaxe"),
    ),
    "helmet": ShopItem(
        price=50,
        db_column="helmet",
        consumable=True,
        emoji="🪖",
        display_name="Mining Helmet",
        description="Protects you from one mine collapse. Single use.",
        aliases=("helmet", "mining helmet"),
    ),
    "sword": ShopItem(
        price=75,
        db_column="sword",
        consumable=True,
        emoji="⚔️",
        display_name="Sword",
        description="Protects you from one goblin attack. Single use.",
        aliases=("sword",),
    ),
    "raw_potato": ShopItem(
        price=2,
        db_column="raw_potato",
        consumable=True,
        emoji="🥔",
        display_name="Raw Potato",
        description="Mine early after 5 min instead of waiting 30 min. Single use. Use: `!mine potato`",
        aliases=("raw potato", "potato"),
    ),
    "golden_mushroom": ShopItem(
        price=25,
        db_column="golden_mushroom",
        consumable=True,
        emoji="🍄",
        display_name="Golden Mushroom",
        description="Mine instantly with no cooldown! Single use. Gained from farming harvests.",
        aliases=("golden mushroom", "mushroom"),
    ),
    "fertilizer": ShopItem(
        price=90,
        db_column="fertilizer",
        consumable=True,
        emoji="🧪",
        display_name="Fertilizer",
        description="Use with `!tend <plot> fertilizer` to restore soil condition by 25.",
        aliases=("fertilizer", "fert"),
    ),
    "water": ShopItem(
        price=40,
        db_column="water",
        consumable=True,
        emoji="💧",
        display_name="Water",
        description="Use with `!tend <plot> water` to restore soil condition by 10.",
        aliases=("water",),
    ),
    "bait_worm": ShopItem(
        price=33,
        db_column="bait_worm",
        consumable=True,
        emoji="🪱",
        display_name="Worm Bait",
        description="Basic bait. Fast bite (15-60s), large pull window (60s). Consistent returns. Use: `!use bait worm`",
        aliases=("worm", "worm bait", "bait worm"),
    ),
    "bait_herring": ShopItem(
        price=79,
        db_column="bait_herring",
        consumable=True,
        emoji="🐟",
        display_name="Herring Bait",
        description="Medium bait. Better fish, longer bite (90-180s), tighter window (35s). Use: `!use bait herring`",
        aliases=("herring", "herring bait", "bait herring"),
    ),
    "bait_sturgeon": ShopItem(
        price=110,
        db_column="bait_sturgeon",
        consumable=True,
        emoji="🐋",
        display_name="Sturgeon Bait",
        description="Premium bait. Best fish odds, long bite (5-8min), tiny window (20s). High risk/reward! Use: `!use bait sturgeon`",
        aliases=("sturgeon", "sturgeon bait", "bait sturgeon"),
    ),
    "telescope": ShopItem(
        price=200,
        db_column="telescope",
        consumable=False,
        emoji="📷",
        display_name="Telescope",
        description="See the stars in a whole new way! Use `!telescope` to view a random starfield.",
        aliases=("telescope",),
    ),
    "bank_insurance": ShopItem(
        price=250,
        db_column="bank_insurance",
        consumable=True,
        emoji="💸",
        display_name="Bank Insurance",
        description="Protects your bank from one disaster at Level 4-5. Single use. Your wallet is still at risk!",
        aliases=("bank insurance", "insurance", "bank shield"),
    ),
    "ray_gun": ShopItem(
        price=5000,
        db_column="ray_gun",
        consumable=True,
        emoji="🔫",
        display_name="Ray-Gun",
        description="Protects your items from alien abduction! 3 uses. Your stars are still at risk.",
        aliases=("ray gun", "ray-gun", "raygun"),
    ),
    "rocket_ship": ShopItem(
        price=10000,
        db_column="rocket_ship",
        consumable=False,
        emoji="🚀",
        display_name="Rocket Ship",
        description="Launch into space and mine on 5 new planets! Requires mine level 5. Use `!launch` after buying.",
        aliases=("rocket ship", "rocket", "rocketship"),
    ),
}


def _build_alias_index(items: dict[str, ShopItem]) -> dict[str, str]:
    index: dict[str, str] = {}
    for key, item in items.items():
        for alias in item.aliases:
            norm = alias.casefold().strip()
            if not norm:
                continue
            prev = index.get(norm)
            if prev is not None and prev != key:
                raise ValueError(
                    f"Alias collision: {alias!r} maps to both {prev!r} and {key!r}"
                )
            index[norm] = key
    return index


_ALIAS_INDEX: Final[dict[str, str]] = _build_alias_index(SHOP_ITEMS)


def get_item_by_alias(alias: str) -> tuple[str, ShopItem] | None:
    norm = alias.casefold().strip()
    key = _ALIAS_INDEX.get(norm)
    if key is None:
        return None
    return key, SHOP_ITEMS[key]

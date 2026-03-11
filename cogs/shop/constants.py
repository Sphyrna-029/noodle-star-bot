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
    "raw_potato": ShopItem(
        price=2,
        db_column="raw_potato",
        consumable=True,
        emoji="🥔",
        display_name="Raw Potato",
        description="Restores 6 stamina. Use: `!drink potato`",
        aliases=("raw potato", "potato"),
    ),
    "golden_mushroom": ShopItem(
        price=25,
        db_column="golden_mushroom",
        consumable=True,
        emoji="🍄",
        display_name="Golden Mushroom",
        description="Restores 40 stamina. Gained from farming harvests. Use: `!drink mushroom`",
        aliases=("golden mushroom", "mushroom"),
    ),
    "fertilizer": ShopItem(
        price=90,
        db_column="fertilizer",
        consumable=True,
        emoji="🧪",
        display_name="Fertilizer",
        description="Use with `!tend <plot> fertilizer` to restore soil condition by 30.",
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
    "growbot": ShopItem(
        price=2500,
        db_column="growbot_owned",
        consumable=False,
        emoji="🤖",
        display_name="Grow-Bot 3000",
        description="Farm helper robot. Use `!farm growbot harvest|tend|plant` for bulk actions.",
        aliases=("growbot", "grow-bot", "grow bot", "agri bot"),
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
    "preserver": ShopItem(
        price=15000,
        db_column="preserver_owned",
        consumable=False,
        emoji="🏭",
        display_name="Preserver",
        description="Unlocks the crop preserver. Use `!farm preserver`, `!farm preserver start`, and `!farm preserver upgrade`.",
        aliases=("preserver", "processing plant", "plant"),
    ),
    "bank_insurance": ShopItem(
        price=2000,
        db_column="bank_insurance",
        consumable=True,
        emoji="💸",
        display_name="Bank Insurance",
        description="Protects your bank from one combat defeat at Level 4-5. Single use. Your wallet is still at risk!",
        aliases=("bank insurance", "insurance", "bank shield"),
    ),
    "ray_gun": ShopItem(
        price=5000,
        db_column="ray_gun",
        consumable=True,
        emoji="🔫",
        display_name="Ray-Gun",
        description="Gives you a chance to fight the alien during abduction (+75 ATK both sides)! 3 uses.",
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
    "bag_upgrade": ShopItem(
        price=1000,  # Base price, actual price varies by current capacity
        db_column="inventory_capacity",
        consumable=True,
        emoji="🎒",
        display_name="Bag Upgrade",
        description="Increase inventory capacity by 5 slots. Price scales with current capacity.",
        aliases=("bag upgrade", "bag", "backpack", "bag expansion"),
    ),
    "lucky_dice": ShopItem(
        price=500,
        db_column="lucky_dice",
        consumable=False,
        emoji="🎲",
        display_name="Lucky Dice",
        description="Lets you gamble from anywhere! No need to travel to Noodle Town.",
        aliases=("lucky dice", "dice"),
    ),
    # ── Combat starter items (Tier 1) ──────────────────────
    "wooden_sword": ShopItem(
        price=200,
        db_column="wooden_sword",
        consumable=False,
        emoji="🗡️",
        display_name="Wooden Sword",
        description="A basic combat weapon for the Noodle Colosseum. +8 ATK.",
        aliases=("wooden sword",),
    ),
    "wooden_shield": ShopItem(
        price=150,
        db_column="wooden_shield",
        consumable=False,
        emoji="🛡️",
        display_name="Wooden Shield",
        description="A simple combat shield. +6 DEF.",
        aliases=("wooden shield",),
    ),
    "leather_vest": ShopItem(
        price=250,
        db_column="leather_vest",
        consumable=False,
        emoji="🦺",
        display_name="Leather Vest",
        description="Light combat armor. +4 DEF, +15 max HP.",
        aliases=("leather vest", "vest"),
    ),
    "iron_dagger": ShopItem(
        price=175,
        db_column="iron_dagger",
        consumable=False,
        emoji="🔪",
        display_name="Iron Dagger",
        description="A quick combat dagger. +6 ATK, low stamina cost.",
        aliases=("iron dagger", "dagger"),
    ),
}


def _build_alias_index(items: dict[str, ShopItem]) -> dict[str, str]:
    index: dict[str, str] = {}
    for key, item in items.items():
        # Include the internal key itself so lookups by key always work
        index[key] = key
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

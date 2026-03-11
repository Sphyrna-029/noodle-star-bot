"""Convert legacy helmet/sword to iron_shield/iron_sword combat equipment.

Existing users with helmets get iron_shield (permanent combat gear, uses=1).
Existing users with swords get iron_sword (permanent combat gear, uses=1).
Golden_axe and mithril_shield are also normalized to uses=1 (permanent).
"""

DESCRIPTION = "Convert legacy helmet/sword to iron_shield/iron_sword; normalize golden_axe/mithril_shield"


def upgrade(cursor) -> None:
    # ── 1. Convert helmet -> iron_shield ──
    # Any user who has a helmet entry gets iron_shield=1 (if they don't already have one)
    cursor.execute(
        """
        INSERT OR IGNORE INTO user_equipment (user_id, item_key, uses)
        SELECT user_id, 'iron_shield', 1
        FROM user_equipment
        WHERE item_key = 'helmet' AND uses > 0
        """
    )
    # Remove all helmet entries
    cursor.execute("DELETE FROM user_equipment WHERE item_key = 'helmet'")

    # ── 2. Convert sword -> iron_sword ──
    cursor.execute(
        """
        INSERT OR IGNORE INTO user_equipment (user_id, item_key, uses)
        SELECT user_id, 'iron_sword', 1
        FROM user_equipment
        WHERE item_key = 'sword' AND uses > 0
        """
    )
    cursor.execute("DELETE FROM user_equipment WHERE item_key = 'sword'")

    # ── 3. Normalize golden_axe to uses=1 (permanent) ──
    cursor.execute(
        "UPDATE user_equipment SET uses = 1 WHERE item_key = 'golden_axe' AND uses > 1"
    )

    # ── 4. Normalize mithril_shield to uses=1 (permanent) ──
    cursor.execute(
        "UPDATE user_equipment SET uses = 1 WHERE item_key = 'mithril_shield' AND uses > 1"
    )


def downgrade(cursor) -> None:
    # Cannot reverse this conversion meaningfully
    pass

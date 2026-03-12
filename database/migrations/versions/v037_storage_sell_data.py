"""Add category and base_sell_value to user_storage so unstashed items
retain their sell properties."""

DESCRIPTION = "Add category and base_sell_value to user_storage"


def upgrade(cursor) -> None:
    cursor.execute(
        "ALTER TABLE user_storage ADD COLUMN category TEXT NOT NULL DEFAULT 'consumable'"
    )
    cursor.execute(
        "ALTER TABLE user_storage ADD COLUMN base_sell_value INTEGER NOT NULL DEFAULT 0"
    )


def downgrade(cursor) -> None:
    pass

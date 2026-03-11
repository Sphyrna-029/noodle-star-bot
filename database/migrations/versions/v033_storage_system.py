"""Storage system — safe deposit box for items.

Items in user_storage are completely immune to all disasters,
death penalties, and alien abductions.
"""

DESCRIPTION = "Storage system: safe item vault immune to all wipes"


def upgrade(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_storage (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            item_key    TEXT    NOT NULL,
            item_type   TEXT    NOT NULL DEFAULT 'inventory',
            uses        INTEGER NOT NULL DEFAULT 1,
            stored_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_storage_user
        ON user_storage(user_id)
        """
    )


def downgrade(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS user_storage")

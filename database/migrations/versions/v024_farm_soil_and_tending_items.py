"""Add farm plot soil state and tending shop items."""

DESCRIPTION = "Add farm soil state table and tending inventory columns"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def upgrade(cursor) -> None:
    """Create farm plot state table and add tending item columns."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS farm_plot_state (
            user_id INTEGER NOT NULL,
            plot_number INTEGER NOT NULL,
            soil_condition INTEGER NOT NULL DEFAULT 100,
            last_crop_type TEXT,
            same_crop_streak INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, plot_number)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_farm_plot_state_user
        ON farm_plot_state(user_id)
        """
    )

    if not _column_exists(cursor, "user_inventory", "fertilizer"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN fertilizer INTEGER DEFAULT 0
            """
        )

    if not _column_exists(cursor, "user_inventory", "water"):
        cursor.execute(
            """
            ALTER TABLE user_inventory
            ADD COLUMN water INTEGER DEFAULT 0
            """
        )


def downgrade(cursor) -> None:
    """Drop farm plot state table.

    Note: user_inventory columns are left in place because SQLite DROP COLUMN
    support is inconsistent across deployed environments.
    """
    cursor.execute("DROP TABLE IF EXISTS farm_plot_state")

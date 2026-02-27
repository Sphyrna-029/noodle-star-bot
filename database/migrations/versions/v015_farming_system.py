"""
Farming system migration.

Creates the planted_crops table for tracking planted crops,
and adds farm_plots column to user_inventory.
"""

DESCRIPTION = "Add farming system with plots and planted crops"


def upgrade(cursor) -> None:
    """Apply the migration."""
    # Add farm_plots column to user_inventory
    cursor.execute(
        """
        ALTER TABLE user_inventory ADD COLUMN farm_plots INTEGER DEFAULT 0
        """
    )

    # Create planted_crops table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS planted_crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plot_number INTEGER NOT NULL,
            crop_type TEXT NOT NULL,
            planted_at TEXT NOT NULL,
            ready_at TEXT NOT NULL,
            UNIQUE(user_id, plot_number)
        )
        """
    )

    # Index for quick lookups by user
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_planted_crops_user
        ON planted_crops(user_id)
        """
    )


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute("DROP TABLE IF EXISTS planted_crops")
    # Note: SQLite doesn't support DROP COLUMN easily, so we leave farm_plots

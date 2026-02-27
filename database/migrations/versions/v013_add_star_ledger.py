"""
Track star balance changes over time for monthly reporting.
"""

DESCRIPTION = "Add star ledger for monthly earned and top gainers"


def upgrade(cursor) -> None:
    """Apply the migration."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS star_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            delta INTEGER NOT NULL,
            changed_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_star_ledger_changed_at
        ON star_ledger(changed_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_star_ledger_user_changed_at
        ON star_ledger(user_id, changed_at)
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_noodle_stars_stars_ledger
        AFTER UPDATE OF stars ON noodle_stars
        FOR EACH ROW
        WHEN NEW.stars != OLD.stars
        BEGIN
            INSERT INTO star_ledger (user_id, delta, changed_at)
            VALUES (
                NEW.user_id,
                NEW.stars - OLD.stars,
                strftime('%Y-%m-%dT%H:%M:%f', 'now')
            );
        END
    """)


def downgrade(cursor) -> None:
    """Rollback the migration."""
    cursor.execute("DROP TRIGGER IF EXISTS trg_noodle_stars_stars_ledger")
    cursor.execute("DROP INDEX IF EXISTS idx_star_ledger_user_changed_at")
    cursor.execute("DROP INDEX IF EXISTS idx_star_ledger_changed_at")
    cursor.execute("DROP TABLE IF EXISTS star_ledger")

"""
Replace roulette-specific invite table with generic game_invites table.
"""

DESCRIPTION = "Add generic game invites table"


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cursor.fetchone() is not None


def upgrade(cursor) -> None:
    """Create generic game invites and migrate roulette invites if present."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS game_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            challenger_id INTEGER NOT NULL,
            challenger_name TEXT NOT NULL,
            opponent_id INTEGER NOT NULL,
            opponent_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_game_invites_opponent
        ON game_invites (game_type, opponent_id, expires_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_game_invites_challenger
        ON game_invites (game_type, challenger_id, expires_at)
        """
    )

    if _table_exists(cursor, "roulette_invites"):
        cursor.execute(
            """
            INSERT INTO game_invites (
                game_type, challenger_id, challenger_name, opponent_id, opponent_name,
                amount, channel_id, created_at, expires_at
            )
            SELECT
                'russian_roulette', challenger_id, challenger_name, opponent_id, opponent_name,
                amount, channel_id, created_at, expires_at
            FROM roulette_invites
            """
        )
        cursor.execute("DROP TABLE roulette_invites")


def downgrade(cursor) -> None:
    """Restore roulette_invites shape and drop generic table."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS roulette_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenger_id INTEGER NOT NULL,
            challenger_name TEXT NOT NULL,
            opponent_id INTEGER NOT NULL,
            opponent_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_roulette_invites_opponent
        ON roulette_invites (opponent_id, expires_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_roulette_invites_challenger
        ON roulette_invites (challenger_id, expires_at)
        """
    )
    if _table_exists(cursor, "game_invites"):
        cursor.execute(
            """
            INSERT INTO roulette_invites (
                challenger_id, challenger_name, opponent_id, opponent_name,
                amount, channel_id, created_at, expires_at
            )
            SELECT
                challenger_id, challenger_name, opponent_id, opponent_name,
                amount, channel_id, created_at, expires_at
            FROM game_invites
            WHERE game_type = 'russian_roulette'
            """
        )
        cursor.execute("DROP TABLE game_invites")

"""Create user_feedback table for player-submitted feedback."""

DESCRIPTION = "Create user_feedback table"


def upgrade(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            feedback_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)


def downgrade(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS user_feedback")

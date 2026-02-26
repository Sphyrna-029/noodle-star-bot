"""SQLite connection manager for Noodle Star Bot."""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DATABASE_FILE


class DatabaseConnection:
    """Manages SQLite database connections."""

    def __init__(self, db_path: str = DATABASE_FILE):
        self.db_path = db_path

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database cursor with auto-commit."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            yield cursor


# Global instance for convenience
_db = DatabaseConnection()


def get_connection() -> DatabaseConnection:
    """Get the global database connection instance."""
    return _db

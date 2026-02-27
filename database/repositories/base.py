"""Shared base class for repositories."""

from database.connection import get_connection


class BaseRepository:
    """Provides database connection to repository classes."""

    def __init__(self):
        self.db = get_connection()

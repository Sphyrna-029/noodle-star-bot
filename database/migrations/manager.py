"""Migration manager for database schema versioning."""

import importlib
import pkgutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from database.connection import get_connection


class MigrationManager:
    """
    Manages database migrations with version tracking.

    Features:
    - Creates schema_version table to track applied migrations
    - Auto-discovers migrations in versions/ folder
    - Applies migrations in order by version number
    - Stores version + description + timestamp for each applied migration
    """

    def __init__(self):
        self.db = get_connection()
        self._ensure_schema_version_table()

    def _ensure_schema_version_table(self) -> None:
        """Create the schema_version table if it doesn't exist."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
            """)

    def get_applied_versions(self) -> List[int]:
        """Get list of already applied migration versions."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT version FROM schema_version ORDER BY version")
            return [row[0] for row in cursor.fetchall()]

    def _discover_migrations(self) -> List[Tuple[int, str, object]]:
        """
        Discover all migration modules in the versions package.

        Returns list of (version_number, description, module) tuples.
        """
        migrations = []

        # Import the versions package
        from database.migrations import versions

        # Get the package path
        package_path = Path(versions.__file__).parent

        # Iterate through all modules in versions/
        for importer, modname, ispkg in pkgutil.iter_modules([str(package_path)]):
            if modname.startswith("v") and not ispkg:
                # Parse version number from filename (e.g., v001_initial_schema -> 1)
                try:
                    version_str = modname.split("_")[0][1:]  # Remove 'v' prefix
                    version_num = int(version_str)

                    # Import the module
                    module = importlib.import_module(
                        f"database.migrations.versions.{modname}"
                    )

                    # Get description from module
                    description = getattr(
                        module, "DESCRIPTION", modname.replace("_", " ")
                    )

                    migrations.append((version_num, description, module))
                except (ValueError, IndexError):
                    # Skip files that don't match the naming convention
                    continue

        # Sort by version number
        migrations.sort(key=lambda x: x[0])
        return migrations

    def run_migrations(self) -> List[str]:
        """
        Run all pending migrations.

        Returns list of applied migration descriptions.
        """
        applied = self.get_applied_versions()
        migrations = self._discover_migrations()
        newly_applied = []

        for version, description, module in migrations:
            if version not in applied:
                print(f"Applying migration v{version:03d}: {description}")

                # Run the migration
                with self.db.get_cursor() as cursor:
                    module.upgrade(cursor)

                    # Record the migration
                    cursor.execute(
                        """
                        INSERT INTO schema_version (version, description, applied_at)
                        VALUES (?, ?, ?)
                    """,
                        (version, description, datetime.now().isoformat()),
                    )

                newly_applied.append(f"v{version:03d}: {description}")

        return newly_applied

    def rollback(self, target_version: int = 0) -> List[str]:
        """
        Rollback migrations to a target version.

        Args:
            target_version: The version to rollback to (exclusive).
                          Default 0 means rollback all.

        Returns list of rolled back migration descriptions.
        """
        applied = sorted(self.get_applied_versions(), reverse=True)
        migrations = {v: (d, m) for v, d, m in self._discover_migrations()}
        rolled_back = []

        for version in applied:
            if version > target_version:
                if version in migrations:
                    description, module = migrations[version]
                    print(f"Rolling back migration v{version:03d}: {description}")

                    # Check if downgrade function exists
                    if hasattr(module, "downgrade"):
                        with self.db.get_cursor() as cursor:
                            module.downgrade(cursor)

                            # Remove the migration record
                            cursor.execute(
                                "DELETE FROM schema_version WHERE version = ?",
                                (version,),
                            )

                        rolled_back.append(f"v{version:03d}: {description}")
                    else:
                        print(f"  Warning: No downgrade function for v{version:03d}")

        return rolled_back

    def get_status(self) -> dict:
        """Get current migration status."""
        applied = self.get_applied_versions()
        all_migrations = self._discover_migrations()

        return {
            "applied_count": len(applied),
            "total_count": len(all_migrations),
            "pending_count": len(all_migrations) - len(applied),
            "current_version": max(applied) if applied else 0,
            "latest_version": max(v for v, _, _ in all_migrations)
            if all_migrations
            else 0,
        }

"""Aetherdepths repository operations."""

from datetime import datetime

from database.repositories.base import BaseRepository


class AetherdepthsRepository(BaseRepository):
    """Aetherdepths-related database operations."""

    # ── Progression ─────────────────────────────────────────

    def get_aether_stats(self, user_id: int) -> dict:
        """Get aether progression fields."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                """SELECT aether_level, active_aether_level, aether_active
                   FROM user_progression WHERE user_id = ?""",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {"aether_level": 0, "active_aether_level": 0, "aether_active": 0}
            return {
                "aether_level": row["aether_level"] or 0,
                "active_aether_level": row["active_aether_level"] or 0,
                "aether_active": row["aether_active"] or 0,
            }

    def update_aether_level(self, user_id: int, level: int) -> None:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                "UPDATE user_progression SET aether_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def update_active_aether_level(self, user_id: int, level: int) -> None:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                "UPDATE user_progression SET active_aether_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def set_aether_active(self, user_id: int, active: int) -> None:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                "UPDATE user_progression SET aether_active = ? WHERE user_id = ?",
                (active, user_id),
            )

    def get_all_active_aether_players(self) -> list[dict]:
        """Get all players currently in the Aetherdepths (for restart recovery)."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT user_id, active_aether_level
                   FROM user_progression WHERE aether_active = 1"""
            )
            return [
                {"user_id": row["user_id"], "level": row["active_aether_level"] or 1}
                for row in cursor.fetchall()
            ]

    # ── Stash ───────────────────────────────────────────────

    def stash_item(self, user_id: int, item_id: int) -> bool:
        """Move an item from inventory to aether stash. Returns True on success."""
        now = datetime.utcnow().isoformat()
        with self.db.get_cursor() as cursor:
            # Get the item from inventory
            cursor.execute(
                "SELECT id, item_key, category, base_sell_value FROM user_inventory_items WHERE id = ? AND user_id = ?",
                (item_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                return False
            # Move to stash
            cursor.execute(
                """INSERT INTO aether_stash (user_id, item_key, category, base_sell_value, stashed_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, row["item_key"], row["category"], row["base_sell_value"], now),
            )
            cursor.execute(
                "DELETE FROM user_inventory_items WHERE id = ? AND user_id = ?",
                (item_id, user_id),
            )
            return True

    def get_stashed_items(self, user_id: int) -> list[dict]:
        """Get all items in a player's aether stash."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, item_key, category, base_sell_value FROM aether_stash WHERE user_id = ?",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_stash_count(self, user_id: int) -> int:
        """Count items in stash."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM aether_stash WHERE user_id = ?",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

    def return_stashed_items(self, user_id: int) -> int:
        """Move all stashed items back to inventory. Returns count moved."""
        now = datetime.utcnow().isoformat()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, item_key, category, base_sell_value FROM aether_stash WHERE user_id = ?",
                (user_id,),
            )
            rows = cursor.fetchall()
            for row in rows:
                cursor.execute(
                    """INSERT INTO user_inventory_items (user_id, item_key, category, base_sell_value, acquired_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, row["item_key"], row["category"], row["base_sell_value"], now),
                )
            cursor.execute(
                "DELETE FROM aether_stash WHERE user_id = ?",
                (user_id,),
            )
            return len(rows)

    def clear_stash(self, user_id: int) -> None:
        """Remove all stashed items (lost on death)."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM aether_stash WHERE user_id = ?",
                (user_id,),
            )

    # ── PvP Log ─────────────────────────────────────────────

    def log_pvp(
        self,
        attacker_id: int,
        defender_id: int,
        aether_level: int,
        result: str,
        attacker_stars_change: int = 0,
        defender_stars_change: int = 0,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO pvp_log
                   (attacker_id, defender_id, aether_level, result,
                    attacker_stars_change, defender_stars_change, fought_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (attacker_id, defender_id, aether_level, result,
                 attacker_stars_change, defender_stars_change, now),
            )

    def get_last_pvp_time(self, victim_id: int) -> str | None:
        """Get the last time this user was attacked (for cooldown)."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT fought_at FROM pvp_log
                   WHERE defender_id = ?
                   ORDER BY fought_at DESC LIMIT 1""",
                (victim_id,),
            )
            row = cursor.fetchone()
            return row["fought_at"] if row else None

    # ── Daily Modifier ──────────────────────────────────────

    def get_daily_modifier(self) -> dict | None:
        """Get the current daily modifier, or None if not active."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT modifier_key, active_date, rolled_at FROM aether_daily_modifier WHERE id = 1"
            )
            row = cursor.fetchone()
            if not row or not row["modifier_key"]:
                return None
            return {
                "modifier_key": row["modifier_key"],
                "active_date": row["active_date"],
                "rolled_at": row["rolled_at"],
            }

    def set_daily_modifier(self, modifier_key: str | None, active_date: str) -> None:
        now = datetime.utcnow().isoformat()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """UPDATE aether_daily_modifier
                   SET modifier_key = ?, active_date = ?, rolled_at = ?
                   WHERE id = 1""",
                (modifier_key, active_date, now),
            )

"""Combat repository operations."""

import json
from datetime import datetime

from database.repositories.base import BaseRepository


class CombatRepository(BaseRepository):
    """Combat-related database operations (user_progression combat cols + combat_log)."""

    # ── Health & Stamina ──────────────────────────────────────

    def get_combat_stats(self, user_id: int) -> dict:
        """Get combat-related progression fields."""
        with self.db.get_cursor() as cursor:
            # Ensure row exists
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                """SELECT current_hp, max_hp, hp_updated_at,
                          current_stamina, max_stamina, stamina_updated_at,
                          combat_level, active_combat_level,
                          equipped_weapon, equipped_shield, equipped_armor
                   FROM user_progression WHERE user_id = ?""",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return self._default_combat_stats()
            return {
                "current_hp": row["current_hp"] if row["current_hp"] is not None else 100,
                "max_hp": row["max_hp"] if row["max_hp"] is not None else 100,
                "hp_updated_at": row["hp_updated_at"],
                "current_stamina": row["current_stamina"] if row["current_stamina"] is not None else 50,
                "max_stamina": row["max_stamina"] if row["max_stamina"] is not None else 50,
                "stamina_updated_at": row["stamina_updated_at"],
                "combat_level": row["combat_level"] if row["combat_level"] is not None else 0,
                "active_combat_level": row["active_combat_level"] if row["active_combat_level"] is not None else 1,
                "equipped_weapon": row["equipped_weapon"],
                "equipped_shield": row["equipped_shield"],
                "equipped_armor": row["equipped_armor"],
            }

    def _default_combat_stats(self) -> dict:
        return {
            "current_hp": 100, "max_hp": 100, "hp_updated_at": None,
            "current_stamina": 50, "max_stamina": 50, "stamina_updated_at": None,
            "combat_level": 0, "active_combat_level": 1,
            "equipped_weapon": None, "equipped_shield": None, "equipped_armor": None,
        }

    def update_hp(self, user_id: int, current_hp: int, max_hp: int = None) -> None:
        """Update user's HP and timestamp."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            now = datetime.utcnow().isoformat()
            if max_hp is not None:
                cursor.execute(
                    """UPDATE user_progression
                       SET current_hp = ?, max_hp = ?, hp_updated_at = ?
                       WHERE user_id = ?""",
                    (current_hp, max_hp, now, user_id),
                )
            else:
                cursor.execute(
                    """UPDATE user_progression
                       SET current_hp = ?, hp_updated_at = ?
                       WHERE user_id = ?""",
                    (current_hp, now, user_id),
                )

    def update_stamina(self, user_id: int, current_stamina: int, max_stamina: int = None) -> None:
        """Update user's stamina and timestamp."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            now = datetime.utcnow().isoformat()
            if max_stamina is not None:
                cursor.execute(
                    """UPDATE user_progression
                       SET current_stamina = ?, max_stamina = ?, stamina_updated_at = ?
                       WHERE user_id = ?""",
                    (current_stamina, max_stamina, now, user_id),
                )
            else:
                cursor.execute(
                    """UPDATE user_progression
                       SET current_stamina = ?, stamina_updated_at = ?
                       WHERE user_id = ?""",
                    (current_stamina, now, user_id),
                )

    # ── Combat level & equipment slots ────────────────────────

    def update_combat_level(self, user_id: int, level: int) -> None:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                "UPDATE user_progression SET combat_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def update_active_combat_level(self, user_id: int, level: int) -> None:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                "UPDATE user_progression SET active_combat_level = ? WHERE user_id = ?",
                (level, user_id),
            )

    def set_equipped_combat_item(self, user_id: int, slot: str, item_key: str | None) -> None:
        """Set equipped combat item for a slot (weapon/shield/armor). None to unequip."""
        col_map = {
            "weapon": "equipped_weapon",
            "shield": "equipped_shield",
            "armor": "equipped_armor",
        }
        col = col_map.get(slot)
        if not col:
            raise ValueError(f"Invalid combat slot: {slot}")
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO user_progression (user_id) VALUES (?)",
                (user_id,),
            )
            cursor.execute(
                f"UPDATE user_progression SET {col} = ? WHERE user_id = ?",
                (item_key, user_id),
            )

    # ── Combat log ────────────────────────────────────────────

    def log_combat(
        self,
        user_id: int,
        dungeon_level: int,
        mob_key: str,
        result: str,
        stars_change: int = 0,
        items_lost: list[str] | None = None,
        equipment_lost: list[str] | None = None,
        bank_loss: int = 0,
    ) -> None:
        """Record a combat encounter in the log."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO combat_log
                   (user_id, dungeon_level, mob_key, result, stars_change,
                    items_lost, equipment_lost, bank_loss)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id, dungeon_level, mob_key, result, stars_change,
                    json.dumps(items_lost) if items_lost else None,
                    json.dumps(equipment_lost) if equipment_lost else None,
                    bank_loss,
                ),
            )

    def get_combat_wins(self, user_id: int) -> int:
        """Count total combat wins."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM combat_log WHERE user_id = ? AND result = 'win'",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

    def get_combat_wins_at_level(self, user_id: int, level: int) -> int:
        """Count wins at a specific dungeon level."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*) as cnt FROM combat_log
                   WHERE user_id = ? AND dungeon_level = ? AND result = 'win'""",
                (user_id, level),
            )
            return cursor.fetchone()["cnt"]

    def get_combat_losses(self, user_id: int) -> int:
        """Count total combat losses."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM combat_log WHERE user_id = ? AND result = 'loss'",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

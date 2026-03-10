"""Data models for Noodle Star Bot."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Represents a user in the noodle stars system."""

    user_id: int
    username: str
    stars: int = 0
    bank: int = 0
    stamina: int = 100
    stamina_last_updated: Optional[datetime] = None
    stamina_last_reset: Optional[datetime] = None
    last_duel_amount: int = 0
    last_duel_at: Optional[datetime] = None
    last_mine: Optional[datetime] = None
    mine_level: int = 1
    active_mine_level: int = 1

    @property
    def total_stars(self) -> int:
        """Total stars (wallet + bank)."""
        return self.stars + self.bank

    @classmethod
    def from_row(cls, row) -> "User":
        """Create a User from a database row."""
        last_mine = None
        if row["last_mine"]:
            last_mine = datetime.fromisoformat(row["last_mine"])

        stamina_last_updated = None
        if "stamina_last_updated" in row.keys() and row["stamina_last_updated"]:
            stamina_last_updated = datetime.fromisoformat(row["stamina_last_updated"])

        stamina_last_reset = None
        if "stamina_last_reset" in row.keys() and row["stamina_last_reset"]:
            stamina_last_reset = datetime.fromisoformat(row["stamina_last_reset"])

        last_duel_at = None
        if "last_duel_at" in row.keys() and row["last_duel_at"]:
            last_duel_at = datetime.fromisoformat(row["last_duel_at"])

        stamina = 100
        if "stamina" in row.keys() and row["stamina"] is not None:
            stamina = row["stamina"]

        last_duel_amount = 0
        if "last_duel_amount" in row.keys() and row["last_duel_amount"] is not None:
            last_duel_amount = row["last_duel_amount"]

        return cls(
            user_id=row["user_id"],
            username=row["username"],
            stars=row["stars"],
            bank=row["bank"],
            stamina=stamina,
            stamina_last_updated=stamina_last_updated,
            stamina_last_reset=stamina_last_reset,
            last_duel_amount=last_duel_amount,
            last_duel_at=last_duel_at,
            last_mine=last_mine,
            mine_level=row["mine_level"] if "mine_level" in row.keys() else 1,
            active_mine_level=row["active_mine_level"] if "active_mine_level" in row.keys() else 1,
        )


@dataclass
class Inventory:
    """Represents a user's inventory."""

    gold_pickaxe: int = 0
    helmet: int = 0
    sword: int = 0
    raw_potato: int = 0
    golden_mushroom: int = 0
    telescope: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "gold_pickaxe": self.gold_pickaxe,
            "helmet": self.helmet,
            "sword": self.sword,
            "raw_potato": self.raw_potato,
            "golden_mushroom": self.golden_mushroom,
        }

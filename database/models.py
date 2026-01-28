"""Data models for Noodle Star Bot."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Represents a user in the noodle stars system."""

    user_id: int
    username: str
    stars: int = 0
    bank: int = 0
    last_mine: Optional[datetime] = None
    gold_pickaxe: int = 0
    helmet: int = 0
    sword: int = 0
    raw_potato: int = 0
    golden_mushroom: int = 0
    telescope: int = 0

    @property
    def total_stars(self) -> int:
        """Total stars (wallet + bank)."""
        return self.stars + self.bank

    @property
    def inventory(self) -> dict:
        """Get inventory as a dictionary."""
        return {
            "gold_pickaxe": self.gold_pickaxe,
            "helmet": self.helmet,
            "sword": self.sword,
            "raw_potato": self.raw_potato,
            "golden_mushroom": self.golden_mushroom,
        }

    @classmethod
    def from_row(cls, row) -> "User":
        """Create a User from a database row."""
        last_mine = None
        if row["last_mine"]:
            last_mine = datetime.fromisoformat(row["last_mine"])

        return cls(
            user_id=row["user_id"],
            username=row["username"],
            stars=row["stars"],
            bank=row["bank"],
            last_mine=last_mine,
            gold_pickaxe=row["gold_pickaxe"],
            helmet=row["helmet"],
            sword=row["sword"],
            raw_potato=row["raw_potato"],
            golden_mushroom=row["golden_mushroom"],
            telescope=row["telescope"],
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

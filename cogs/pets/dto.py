"""DTOs for pet features."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class PetStatus:
    """Represents the current state of a pet."""

    user_id: int
    pet_key: str
    pet_name: str
    pet_nickname: Optional[str]
    pet_emoji: str
    is_active: bool
    hunger: int
    cleanliness: int
    happiness: int
    mood: str
    sprite_state: str
    sprite_path: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Name to show in UI, preferring nickname when set."""
        if self.pet_nickname:
            return f"{self.pet_nickname} ({self.pet_name})"
        return self.pet_name


@dataclass(slots=True)
class ActionResult:
    """Standard result for pet interactions."""

    success: bool
    message: str
    pet: Optional[PetStatus] = None


@dataclass(slots=True)
class BuyPetResult:
    """Result for buying/adopting a pet."""

    success: bool
    message: str
    pet: Optional[PetStatus] = None
    price: int = 0
    new_balance: int = 0


@dataclass(slots=True)
class PetListResult:
    """Collection of owned pets for a user."""

    pets: list[PetStatus] = field(default_factory=list)

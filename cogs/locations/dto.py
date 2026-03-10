"""DTOs for location use-cases."""

from dataclasses import dataclass


@dataclass(slots=True)
class TravelResult:
    success: bool
    message: str
    destination: str = ""
    cooldown_remaining: int = 0

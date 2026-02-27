"""DTOs for economy use-cases."""

from dataclasses import dataclass


@dataclass(slots=True)
class BalanceResult:
    """Result of a balance operation."""

    success: bool
    message: str
    wallet: int = 0
    bank: int = 0

    @property
    def total(self) -> int:
        return self.wallet + self.bank

@dataclass(slots=True)
class EconomyStats:
    """Stats of the economy."""

    success: bool
    message: str
    total_stars: int = 0

"""DTOs for economy use-cases."""

from dataclasses import dataclass, field


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


@dataclass(slots=True)
class AchievementStatus:
    """Represents one achievement and whether it is unlocked."""

    key: str
    name: str
    emoji: str
    description: str
    unlocked: bool
    progress_current: int | None = None
    progress_target: int | None = None


@dataclass(slots=True)
class ProfileResult:
    """User profile snapshot for profile command display."""

    success: bool
    message: str
    wallet: int = 0
    bank: int = 0
    achievements: list[AchievementStatus] = field(default_factory=list)
    newly_unlocked: list[AchievementStatus] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.wallet + self.bank

    @property
    def unlocked_achievements(self) -> int:
        return sum(1 for achievement in self.achievements if achievement.unlocked)

    @property
    def total_achievements(self) -> int:
        return len(self.achievements)

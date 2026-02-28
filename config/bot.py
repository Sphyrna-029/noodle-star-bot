from typing import Final

__all__ = ["COMMAND_PREFIX", "DEV_USER_IDS"]

COMMAND_PREFIX: Final[str] = "!"
DEV_USER_IDS: Final[frozenset[int]] = frozenset(
    {
        249969537066205185,
        85538959156850688,
        445641460507869185,
    }
)

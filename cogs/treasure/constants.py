"""Constants for the treasure chest lock-picking event."""

from datetime import timedelta
from typing import Final

# =============================================================================
# Core gameplay tuning
# =============================================================================

# Number of pins in the lock (length of the combo)
LOCK_PIN_COUNT: Final[int] = 3

# Range for each pin value (inclusive)
LOCK_PIN_MIN: Final[int] = 1
LOCK_PIN_MAX: Final[int] = 4

# Attempts allowed per lock-picking session
LOCK_ATTEMPTS: Final[int] = 5

# Time a single user can hold the lock before it resets
LOCK_OWNER_TIMEOUT: Final[timedelta] = timedelta(seconds=60)

# Time a chest stays available before expiring (if enabled)
CHEST_LIFETIME: Final[timedelta] = timedelta(hours=1)

# Cooldown between chest spawns (if used)
CHEST_SPAWN_COOLDOWN: Final[timedelta] = timedelta(minutes=5)

# =============================================================================
# Rewards
# =============================================================================

# Reward range in stars for a successful pick
TREASURE_REWARD_MIN: Final[int] = 75
TREASURE_REWARD_MAX: Final[int] = 200

# Channel ID for treasure chest announcements (set per server)
TREASURE_ANNOUNCEMENT_CHANNEL_ID: Final[int] = 1464375861800210688

# =============================================================================
# Messaging
# =============================================================================

CHEST_ANNOUNCEMENT: Final[str] = (
    "🧰 A locked treasure chest appears! Use `!pick start` to begin."
)

LOCK_INSTRUCTIONS: Final[str] = (
    "🔐 Lock has **{pins} pins**. Each pin is a number **{min_pin}-{max_pin}**. "
    "You have **{attempts} tries**. Make a guess like: `!pick 1 3 2`."
)

SUCCESS_MESSAGE: Final[str] = (
    "🎉 {mention} picked the lock and won **{reward}** stars!"
)

FAIL_MESSAGE: Final[str] = (
    "❌ Wrong combo. Correct position: **{exact}**, "
    "correct number wrong position: **{misplaced}**. "
    "Attempts left: **{attempts_left}**."
)

TIMEOUT_MESSAGE: Final[str] = (
    "⌛ The lock jammed and reset. The chest is now up for grabs again!"
)

EXPIRED_MESSAGE: Final[str] = (
    "🕳️ The chest vanished before anyone could open it."
)

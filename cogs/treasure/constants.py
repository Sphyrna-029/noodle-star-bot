"""Constants for the treasure chest lock-picking event."""

from datetime import timedelta
from typing import Final

# =============================================================================
# Core gameplay tuning
# =============================================================================

# Number of pins in the standard lock (length of the combo)
LOCK_PIN_COUNT: Final[int] = 3

# Number of pins for harder, item-capable chests
LOCK_PIN_COUNT_ITEM_CHEST: Final[int] = 4

# Range for each pin value (inclusive)
LOCK_PIN_MIN: Final[int] = 1
LOCK_PIN_MAX: Final[int] = 4

# Attempts allowed per lock-picking session
LOCK_ATTEMPTS: Final[int] = 5

# Time a single user can hold the lock before it resets
LOCK_OWNER_TIMEOUT: Final[timedelta] = timedelta(seconds=120)

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

# Chance a spawned chest is item-capable (harder lock, item roll enabled)
CHEST_ITEM_TIER_CHANCE: Final[float] = 0.35

# If item-capable, chance an item actually drops when opened
CHEST_ITEM_DROP_CHANCE: Final[float] = 0.60

# If an item drops, chance it is from the rare item pool
CHEST_RARE_ITEM_DROP_CHANCE: Final[float] = 0.20

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
    "You have **{attempts} tries**. Make a guess like: `{example_guess}`."
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

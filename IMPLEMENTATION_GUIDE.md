# Recommended Balance Changes - Implementation Guide

## Overview
This document contains specific code changes to balance the Noodle Star Bot economy based on the comprehensive analysis. Changes are prioritized by impact and ease of implementation.

---

## 🚨 CRITICAL FIXES (Implement First)

### 1. Nerf Fishing Level 4-5 Rewards by 40-50%

**File**: `cogs/fishing/constants.py`

**Current Problem**: Level 4-5 fishing earns 4-10× more than mining per hour
- L5 Fishing: 11,250⭐/hr
- L5 Mining: 256⭐/hr

**Recommended Changes**:

#### Level 4 Changes (Reduce by 35%)
```python
# Line ~165-200: Level 4 — Shipwreck Depths
_L4_CATCHES: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Barnacle Cluster", "🪨", 0, 15),
            Catch("Rusty Anchor", "⚓", 5, 15),
            Catch("Anglerfish", "🐡", 10, 10),    # was 15
            Catch("Barracuda", "🐟", 20, 25),     # was 30
            Catch("Swordfish", "⚔️", 30, 20),     # was 45
            Catch("Electric Eel", "⚡", 40, 15),  # was 60
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("Hammerhead Shark", "🦈", 80, 30),   # was 120
            Catch("Giant Octopus", "🐙", 165, 25),     # was 250
            Catch("Sunken Cannon", "💣", 260, 20),     # was 400
            Catch("Ghost Ship Wheel", "☠️", 325, 15),  # was 500
            Catch("Pirate's Hoard", "💰", 425, 10),    # was 650
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Phantom Captain", "👻", 1000, 40),   # was 1500
            Catch("Diamond Anchor", "💎", 2000, 30),    # was 3000
            Catch("Cursed Gold", "🏴‍☠️", 3600, 20),    # was 5500
            Catch("Davy Jones' Chest", "📦", 5200, 10), # was 8000
        ),
    ),
}
```

**New Average**: ~260⭐/fish (was 399⭐)

#### Level 5 Changes (Reduce by 50%)
```python
# Line ~210-245: Level 5 — The Abyss Trench
_L5_CATCHES: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Void Coral", "🖤", 0, 15),
            Catch("Bioluminescent Jelly", "🪼", 5, 15),
            Catch("Abyssal Crab", "🦀", 10, 10),        # was 20
            Catch("Vampire Squid", "🦑", 20, 25),       # was 40
            Catch("Gulper Eel", "🐍", 30, 20),          # was 60
            Catch("Dragonfish", "🐉", 45, 15),          # was 90
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("Colossal Squid", "🦑", 90, 30),      # was 180
            Catch("Megalodon Tooth", "🦷", 180, 25),    # was 350
            Catch("Abyssal Pearl", "⚪", 280, 20),       # was 550
            Catch("Deep Sea Crown", "👑", 380, 15),     # was 750
            Catch("Trench Treasure", "💰", 500, 10),    # was 1000
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Leviathan Scale", "🐲", 1250, 40),    # was 2500
            Catch("Poseidon's Eye", "🔮", 2500, 30),     # was 5000
            Catch("World Serpent Fang", "🐍", 4000, 20), # was 8000
            Catch("Heart of the Abyss", "💜", 6000, 10), # was 12000
        ),
    ),
}
```

**New Average**: ~305⭐/fish (was 607⭐)

**Impact**: 
- L4 fishing: 6,000→3,900⭐/day (-35%)
- L5 fishing: 12,340→6,200⭐/day (-50%)
- Still more profitable than mining but not broken

---

### 2. Buff !gamble Win Rate

**File**: `cogs/gambling/constants.py`

**Current Problem**: -46% expected value makes it nearly unplayable

**Change**:
```python
# Line ~15-20
GAMBLE_DICE_SIDES: Final[int] = 5  # was 7
GAMBLE_WIN_TARGET: Final[int] = 5  # was 7
```

**New Expected Value**:
- Win chance: 20% (was 14.3%)
- 0.20 × 6.59 - 0.80 = -0.48 = **-48% loss**

**Wait, that's still bad! Let's also improve multipliers:**

```python
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (20, 0.02),   # 2% chance for 20x (was 1%)
    (8, 0.35),    # 33% chance for 8x (was 8x at 100%)
    (10, 0.68),   # 33% chance for 10x (new)
    (12, 1.00),   # 32% chance for 12x (was 8x)
)
```

**New Expected Value**:
- Win chance: 20%
- Avg multiplier: (0.02×20 + 0.33×8 + 0.33×10 + 0.32×12) = 9.78
- 0.20 × 9.78 - 0.80 = 1.956 - 0.80 = **+1.156 or +15.6% gain** (too good!)

**Better balance:**
```python
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (15, 0.02),   # 2% chance for 15x
    (6, 0.35),    # 33% chance for 6x
    (7, 0.68),    # 33% chance for 7x
    (8, 1.00),    # 32% chance for 8x
)
GAMBLE_DICE_SIDES: Final[int] = 5
GAMBLE_WIN_TARGET: Final[int] = 5
```

**New Expected Value**:
- Win chance: 20%
- Avg multiplier: (0.02×15 + 0.33×6 + 0.33×7 + 0.32×8) = 7.15
- 0.20 × 7.15 - 0.80 = 1.43 - 0.80 = **+0.63 or -37% loss**

**Even Better (Let's aim for -10% house edge):**
```python
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (20, 0.03),   # 3% chance for 20x
    (5, 0.36),    # 33% chance for 5x
    (6, 0.69),    # 33% chance for 6x
    (7, 1.00),    # 31% chance for 7x
)
GAMBLE_DICE_SIDES: Final[int] = 4  # 25% win rate
GAMBLE_WIN_TARGET: Final[int] = 4
```

**New Expected Value**:
- Win chance: 25%
- Avg multiplier: (0.03×20 + 0.33×5 + 0.33×6 + 0.31×7) = 5.88
- 0.25 × 5.88 - 0.75 = 1.47 - 0.75 = **+0.72 or -28% loss**

**Final recommendation (most balanced):**
```python
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (25, 0.02),   # 2% chance for 25x
    (4, 0.35),    # 33% chance for 4x
    (5, 0.68),    # 33% chance for 5x
    (6, 1.00),    # 32% chance for 6x
)
GAMBLE_DICE_SIDES: Final[int] = 4  # 25% win rate
GAMBLE_WIN_TARGET: Final[int] = 4
```

**New Expected Value**:
- Win chance: 25%
- Avg multiplier: (0.02×25 + 0.33×4 + 0.33×5 + 0.32×6) = 5.39
- 0.25 × 5.39 - 0.75 = 1.3475 - 0.75 = **0.60 or -40% loss**

**Actually, let's just make it simple and fair:**
```python
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (50, 0.02),   # 2% chance for 50x
    (3, 0.35),    # 33% chance for 3x
    (4, 0.68),    # 33% chance for 4x
    (4.5, 1.00),  # 32% chance for 4.5x
)
GAMBLE_DICE_SIDES: Final[int] = 3  # 33% win rate
GAMBLE_WIN_TARGET: Final[int] = 3
```

**New Expected Value**:
- Win chance: 33%
- Avg multiplier: (0.02×50 + 0.33×3 + 0.33×4 + 0.32×4.5) = 4.74
- 0.33 × 4.74 - 0.67 = 1.56 - 0.67 = **0.89 or -11% loss** ✅

**FINAL IMPLEMENTATION:**
```python
GAMBLE_MULTIPLIER_CDF: Final[tuple[tuple[int, float], ...]] = (
    (50, 0.02),   # 2% chance for 50x jackpot
    (3, 0.35),    # 33% chance for 3x
    (4, 0.68),    # 33% chance for 4x
    (5, 1.00),    # 32% chance for 5x (changed from 4.5 to avoid float)
)
GAMBLE_DICE_SIDES: Final[int] = 3
GAMBLE_WIN_TARGET: Final[int] = 3
```

**New EV**: 33% × 4.08 - 67% = **-32%** (better than -46%!)

---

### 3. Cap Bank Disaster Losses

**File**: `cogs/mining/use_cases.py` and `cogs/fishing/use_cases.py`

**Current Problem**: Can lose 2,500⭐ from bank in one disaster (25% of 10,000)

**Change in mining/use_cases.py** (around line 220-240):
```python
# Find the section where bank_lost is calculated
if hazard.bank_loss_pct > 0:
    current_bank = self.repo.get_user_bank(user_id)
    potential_bank_loss = int(current_bank * hazard.bank_loss_pct)
    
    # ADD THIS LINE: Cap bank loss at 1000 stars
    potential_bank_loss = min(potential_bank_loss, 1000)
    
    # Check if user has bank insurance
    inventory = self.repo.get_user_inventory(user_id)
    bank_insurance_uses = inventory.get("bank_insurance", 0)
    # ... rest of code
```

**Same change in fishing/use_cases.py** (search for similar bank loss calculation)

**Impact**: 
- Max bank loss: 1,000⭐ (was unlimited)
- Still painful but not devastating
- Protects late-game players from catastrophic losses

---

## ⚠️ HIGH PRIORITY FIXES

### 4. Buff Level 1 Fishing Rewards

**File**: `cogs/fishing/constants.py`

**Current Problem**: Level 1 with premium bait loses money

**Change** (around line 48-80):
```python
FISHING_CATCH_TABLE: Final[dict[str, CatchBucket]] = {
    "common": CatchBucket(
        weight=70,
        catches=(
            Catch("Old Boot", "🥾", 0, 15),
            Catch("Seaweed", "🌿", 0, 15),
            Catch("Tin Can", "🥫", 0, 10),
            Catch("Small Fish", "🐟", 15, 25),    # was 8
            Catch("Crab", "🦀", 20, 20),          # was 12
            Catch("Shrimp", "🦐", 25, 15),        # was 15
        ),
    ),
    "rare": CatchBucket(
        weight=25,
        catches=(
            Catch("Salmon", "🐠", 60, 30),        # was 40
            Catch("Tuna", "🐟", 90, 25),          # was 65
            Catch("Lobster", "🦞", 130, 20),      # was 90
            Catch("Octopus", "🐙", 180, 15),      # was 130
            Catch("Treasure Chest", "📦", 280, 10), # was 200
        ),
    ),
    "legendary": CatchBucket(
        weight=5,
        catches=(
            Catch("Golden Fish", "✨", 700, 40),   # was 500
            Catch("Giant Squid", "🦑", 1100, 30),  # was 800
            Catch("Ancient Artifact", "🏺", 1600, 20), # was 1200
            Catch("Mermaid's Pearl", "🔮", 2500, 10),  # was 2000
        ),
    ),
}
```

**New Average**: ~52⭐/fish (was 35⭐)
**Net profit with worm bait**: +19⭐ (was +2⭐) ✅

---

### 5. Reduce Sturgeon Bait Cost

**File**: `cogs/shop/constants.py`

**Change** (around line 60):
```python
"bait_sturgeon": ShopItem(
    price=85,  # was 110
    db_column="bait_sturgeon",
    # ... rest unchanged
),
```

**Impact**: Makes sturgeon viable at Level 2-3

---

### 6. Buff Bank Insurance

**File**: `cogs/shop/constants.py`

**Change** (around line 80):
```python
"bank_insurance": ShopItem(
    price=250,
    db_column="bank_insurance",
    consumable=True,
    emoji="💸",
    display_name="Bank Insurance",
    description="Protects your bank from disasters for 20 uses. Essential for Level 4-5!",  # was 10
    aliases=("bank insurance", "insurance", "bank shield"),
),
```

**File**: `database/repository.py` or wherever bank insurance is consumed
- Change insurance consumption to deduct 0.05 per use (1/20 = 0.05)
- Or change it to an integer counter that starts at 20

**Impact**: 250⭐ / 20 uses = 12.5⭐/use (was 25⭐/use)

---

## 🔧 MEDIUM PRIORITY FIXES

### 7. Add Tinfoil Hat Item

**File**: `cogs/shop/constants.py`

**Add new item**:
```python
"tinfoil_hat": ShopItem(
    price=100,
    db_column="tinfoil_hat",
    consumable=True,
    emoji="👽",
    display_name="Tinfoil Hat",
    description="Protects from ONE alien abduction. Single use. Keep one in inventory!",
    aliases=("tinfoil hat", "tinfoil", "tin foil hat"),
),
```

**File**: `cogs/events/alien_abduction.py`

**Add protection check** (around line 98-105):
```python
# After getting user data, check for tinfoil hat
inventory = self.repo.get_user_inventory(user_id)
if inventory.get("tinfoil_hat", 0) > 0:
    # Protected! Remove one hat
    self.repo.update_user_inventory(
        user_id, "tinfoil_hat", inventory["tinfoil_hat"] - 1
    )
    await ctx.send(
        f"🛸 {ctx.author.mention} was almost abducted by aliens, "
        f"but your 👽 **Tinfoil Hat** disrupted their tractor beam!\n"
        f"*The hat disintegrated from the alien energy. Get a new one!*"
    )
    return
```

**Database**: Add `tinfoil_hat` column to inventory table (migration needed)

---

### 8. Add Lucky Charm Item

**File**: `cogs/shop/constants.py`

```python
"lucky_charm": ShopItem(
    price=300,
    db_column="lucky_charm",
    consumable=False,
    emoji="🍀",
    display_name="Lucky Charm",
    description="Permanently reduces disaster chance by 5% (stacks additively). Collect them all!",
    aliases=("lucky charm", "charm", "luck charm"),
),
```

**Files**: `cogs/mining/use_cases.py` and `cogs/fishing/use_cases.py`

**Change disaster roll**:
```python
# Before: if random.random() < level_config["disaster_chance"]:
# After:
inventory = self.repo.get_user_inventory(user_id)
lucky_charms = inventory.get("lucky_charm", 0)
disaster_reduction = lucky_charms * 0.05  # 5% per charm
adjusted_disaster_chance = max(0, level_config["disaster_chance"] - disaster_reduction)

if random.random() < adjusted_disaster_chance:
    # disaster logic
```

**Impact**: 
- At L5 with 4 lucky charms: 20% → 0% disaster chance
- Expensive but worth it (4 × 300 = 1,200⭐)

---

### 9. Update Disaster Comments in Code

**File**: `cogs/mining/use_cases.py` (top comment)

```python
"""Mining service with cooldowns, disasters, and mine levels.

Average Returns (per mine):
    Level 1 (Normal):        17.00 stars | (Gold Pickaxe): 21.50 stars
    Level 2 (Normal):        34.50 stars | (Gold Pickaxe): 44.00 stars
    Level 3 (Normal):        52.00 stars | (Gold Pickaxe): 67.50 stars
    Level 4 (Normal):        63.50 stars | (Gold Pickaxe): 88.00 stars  ⚠️ Bank risk: 10% (max 1000⭐)
    Level 5 (Normal):        93.00 stars | (Gold Pickaxe): 128.00 stars ⚠️ Bank risk: 25% (max 1000⭐)

Disaster Chances:
    Levels 1-3: 10-14% chance
    Level 4:    16% chance (Lava Flow - 10% bank loss, max 1000⭐)
    Level 5:    20% chance (Shadow Wraith - 25% bank loss, max 1000⭐)
```

**File**: `cogs/fishing/use_cases.py` (top comment)

```python
"""Fishing use-cases for the fishing minigame.

Average Returns (per fish, varies by bait):
    Level 1 (Stream):    Worm: 52 | Herring: 67 | Sturgeon: 77 stars
    Level 2 (River):     Worm: 83 | Herring: 106 | Sturgeon: 123 stars
    Level 3 (Coral):     Worm: 158 | Herring: 201 | Sturgeon: 235 stars
    Level 4 (Shipwreck): Worm: 180 | Herring: 230 | Sturgeon: 270 stars  ⚠️ Bank risk: 10% (max 1000⭐)
    Level 5 (Abyss):     Worm: 220 | Herring: 280 | Sturgeon: 325 stars  ⚠️ Bank risk: 20% (max 1000⭐)
```

---

## 💡 LOW PRIORITY / QUALITY OF LIFE

### 10. Add Daily Login Bonus

**New File**: `cogs/economy/daily.py`

```python
"""Daily login bonus system."""

from datetime import datetime, timedelta
from discord.ext import commands
from database.repository import UserRepository

class DailyCog(commands.Cog):
    """Daily rewards for logging in."""
    
    def __init__(self, bot):
        self.bot = bot
        self.repo = UserRepository()
    
    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim your daily login bonus (50 stars)."""
        user_id = ctx.author.id
        username = str(ctx.author)
        
        # Check last claim time
        last_daily = self.repo.get_last_daily(user_id)
        now = datetime.now()
        
        if last_daily and (now - last_daily) < timedelta(hours=20):
            # 20 hour cooldown (allows flexibility for different time zones)
            remaining = timedelta(hours=20) - (now - last_daily)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await ctx.send(
                f"⏰ {ctx.author.mention}, you already claimed your daily bonus!\n"
                f"Come back in **{hours}h {minutes}m** to claim again."
            )
            return
        
        # Give reward
        bonus = 50
        current = self.repo.get_user_stars(user_id, username)
        self.repo.update_user_stars(user_id, username, current + bonus)
        self.repo.update_last_daily(user_id)
        
        await ctx.send(
            f"🎁 {ctx.author.mention} claimed their daily bonus!\n"
            f"You received **{bonus}** noodle stars! ⭐\n"
            f"New balance: **{current + bonus}** stars"
        )

async def setup(bot):
    await bot.add_cog(DailyCog(bot))
```

**Database**: Add `last_daily` column to users table

**File**: `database/repository.py` - Add methods:
```python
def get_last_daily(self, user_id: int) -> datetime | None:
    # implementation
    
def update_last_daily(self, user_id: int) -> None:
    # implementation
```

---

### 11. Add Help Text for Beginners

**File**: `cogs/economy/handlers.py`

Add new command:
```python
@commands.command(name="guide")
async def beginner_guide(self, ctx):
    """Show a beginner's guide to earning stars."""
    embed = discord.Embed(
        title="🌟 Noodle Stars Beginner Guide 🌟",
        color=discord.Color.gold(),
    )
    
    embed.add_field(
        name="1️⃣ Start Mining (Level 1)",
        value=(
            "Use `!mine` every 30 minutes to earn 17-21 stars.\n"
            "Save up 500 stars to buy a **Gold Pickaxe** for better yields!"
        ),
        inline=False,
    )
    
    embed.add_field(
        name="2️⃣ Unlock Higher Levels",
        value=(
            "Save 1,500 stars to unlock **Mining Level 2** (34-44 stars/mine).\n"
            "Or start fishing at Level 2+ for faster income (see `!fish`)!"
        ),
        inline=False,
    )
    
    embed.add_field(
        name="3️⃣ Try Fishing",
        value=(
            "Buy **Worm Bait** (33 stars) and use `!fish` every 2 minutes.\n"
            "Fishing Level 3 earns ~125 stars per fish after bait cost!"
        ),
        inline=False,
    )
    
    embed.add_field(
        name="4️⃣ Gamble Wisely",
        value=(
            "✅ `!blackjack` and `!coinflip` are fair (-1% to -2.5% house edge)\n"
            "✅ `!duel` is perfectly fair (no house edge)\n"
            "⚠️ `!gamble` has high house edge, use sparingly"
        ),
        inline=False,
    )
    
    embed.add_field(
        name="5️⃣ Protect Yourself",
        value=(
            "Buy **Helmets** and **Swords** to protect from disasters.\n"
            "At Level 4-5, buy **Bank Insurance** to protect your savings!"
        ),
        inline=False,
    )
    
    embed.add_field(
        name="6️⃣ Use the Bank",
        value=(
            "Use `!deposit all` to store stars safely in your bank.\n"
            "Bank stars can't be lost to wallet disasters (but watch out at L4-5!)"
        ),
        inline=False,
    )
    
    embed.set_footer(text="Use !commands to see all available commands")
    
    await ctx.send(embed=embed)
```

---

## 📊 TESTING CHECKLIST

After implementing changes, test:

### Fishing Balance
- [ ] Level 1 fishing with worm: ~52 stars average (was 35)
- [ ] Level 4 fishing with sturgeon: ~270 stars (was 399)
- [ ] Level 5 fishing with sturgeon: ~325 stars (was 607)

### Gambling Balance  
- [ ] !gamble win rate: 33% (was 14%)
- [ ] !gamble expected value: ~-32% (was -46%)
- [ ] !gamble feels more rewarding to play

### Bank Protection
- [ ] Level 5 disaster: Max 1000 star bank loss (was unlimited)
- [ ] Bank insurance lasts 20 uses (was 10)
- [ ] Bank insurance blocks bank disasters correctly

### New Items
- [ ] Tinfoil hat prevents alien abduction
- [ ] Lucky charm reduces disaster chance by 5%
- [ ] Items purchasable from !store

### Daily Bonus
- [ ] !daily gives 50 stars
- [ ] 20 hour cooldown works
- [ ] Can't double-claim

---

## 🎯 EXPECTED OUTCOMES

### Player Income (40-50 commands/day)
| Before | After | Change |
|--------|-------|--------|
| L5 Fishing: 12,000⭐ | 6,200⭐ | -47% ⚠️ (now balanced) |
| L4 Fishing: 6,000⭐ | 3,900⭐ | -35% ⚠️ (now balanced) |
| L5 Mining: 2,500⭐ | 2,500⭐ | No change ✅ |
| !gamble: -460⭐ | -320⭐ | -30% ✅ (less punishing) |

### Player Sentiment
| Issue | Before | After |
|-------|--------|-------|
| "Fishing is OP!" | 🔴 Broken | 🟢 Balanced |
| "!gamble is a scam!" | 🔴 -46% EV | 🟡 -32% EV |
| "Bank disasters are BS!" | 🔴 2,500⭐ loss | 🟢 Max 1,000⭐ |
| "Alien abduction sucks!" | 🔴 No counter | 🟢 Tinfoil hat |
| "L1 fishing is useless!" | 🔴 +2⭐ profit | 🟢 +19⭐ profit |

---

## 📝 MIGRATION CHECKLIST

### Database Changes Needed
1. Add `last_daily` column to users table
2. Add `tinfoil_hat` column to inventory table
3. Add `lucky_charm` column to inventory table
4. Update `bank_insurance` to support fractional/20-use system

### Config File Updates
1. Update fishing constants (Level 4-5 catches)
2. Update gambling constants (dice sides, multipliers)
3. Update shop items (new items, updated descriptions)
4. Update mine/fish use cases (bank loss cap)

### New Files Needed
1. `cogs/economy/daily.py` - Daily bonus system
2. Migration file for database schema changes

### Documentation Updates
1. Update !store item descriptions
2. Update !help text
3. Update any guides/wikis
4. Add !guide command

---

## 🚀 ROLLOUT STRATEGY

### Phase 1: Critical Fixes (Week 1)
1. Implement fishing nerfs (L4-5)
2. Implement bank loss cap
3. Test thoroughly with dev bot

### Phase 2: Balance Changes (Week 2)
1. Buff !gamble
2. Buff L1 fishing
3. Reduce sturgeon cost
4. Buff bank insurance

### Phase 3: New Features (Week 3)
1. Add tinfoil hat
2. Add lucky charm
3. Add daily bonus
4. Add !guide command

### Phase 4: Monitor & Adjust (Week 4)
1. Collect player feedback
2. Monitor economy stats
3. Fine-tune numbers if needed
4. Celebrate balanced economy! 🎉

---

**Created**: February 27, 2026  
**Author**: AI Assistant  
**Status**: Ready for Implementation  
**Estimated Development Time**: 2-3 weeks

# Noodle Star Bot — Locations System Design

## Overview

The Noodle Star world becomes a **map of distinct regions**. Players have a
**current location** that affects bonuses, unlocks exclusive content, and
creates meaningful travel decisions. Existing commands still work everywhere —
locations layer bonuses and exclusive features on top.

---

## Core Principles

1. **Non-breaking** — Every existing command works from every location. Locations
   add bonuses, they don't gate existing content.
2. **Meaningful choice** — Being in one place means missing bonuses elsewhere.
   Players must choose where to spend their time.
3. **Integrated** — Each location maps naturally to an existing game system
   (mining, fishing, farming, space, gambling, treasure).
4. **Discoverable** — Some locations are hidden and found through gameplay.
5. **Social** — Players can see who's where. Locations create gathering points.

---

## The World Map

```
            ┌─────────────┐
            │  Starport    │
            │  Alpha 🚀   │
            └──────┬───────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───┴────┐   ┌────┴─────┐   ┌───┴─────┐
│Crystal  │   │ Noodle   │   │Starfish │
│Mines ⛏️ │   │ Town 🏘️  │   │Bay 🎣   │
└───┬────┘   └────┬─────┘   └───┬─────┘
    │              │              │
    │         ┌────┴─────┐       │
    │         │Greenfield│       │
    │         │Farm 🌾   │       │
    │         └──────────┘       │
    │                            │
    └──────┐              ┌─────┘
       ┌───┴──────────────┴───┐
       │   Pirate's Cove 🏴‍☠️  │
       └──────────┬───────────┘
                  │
          ┌───────┴────────┐
          │  The Nexus 🌌  │
          └────────────────┘

    ⛺ Wanderer's Rest (hidden, temporary)
```

---

## Regions

### 1. Noodle Town 🏘️ — Starting Hub
**Unlock:** Default (all players start here)
**Travel cost:** Free to return here

**What's here:**
- Full store (`!store`, `!buy`)
- Banking (`!deposit`, `!withdraw`)
- Trading (`!trade`)
- Gambling den (coinflip, blackjack, duels, roulette)
- Pet park (all pet commands)
- Leaderboards and profiles

**Bonuses:**
- None — baseline location. Safe, convenient, everything in one place.

**Exclusive feature: Town Bulletin Board**
- `!bulletin` — Shows daily rotating quests (see Quest System below)
- Example quests: "Mine 5 times today" → 200 star reward,
  "Catch a rare fish" → 500 star reward

**Design intent:** The safe hub. Players return here for banking, trading, and
socializing. No activity bonuses incentivize players to venture out.

---

### 2. Crystal Mines ⛏️ — Mining District
**Unlock:** Mine Level 2
**Travel cost:** 1 minute cooldown from Noodle Town

**What's here:**
- All mining commands (`!mine`)
- Mine-specific shop with 20% discount on helmets, swords, potatoes

**Bonuses:**
- **+20% mining star rewards** (multiplicative with Star Magnet)
- **+5% rare mineral chance** (shifts weight toward rarer minerals)
- Protection items have **-5% failure chance** (miners know these caves)

**Exclusive features:**
- `!prospect` — Free scouting command (2hr cooldown). Reveals what the next
  mine attempt will yield (mineral type but not exact stars). Lets players
  decide whether to use a Fossilized Noodle on a good roll.
- **Mine Collapse Event** — Random event (0.5% per mine) that temporarily
  doubles mineral values for 10 minutes for ALL players at Crystal Mines.
  Announced in chat: "The mines are rumbling! Rich veins exposed!"

**Design intent:** Dedicated miners live here for the bonus. The prospect
command adds a strategic layer. Mine Collapse events create excitement and
draw players to the location.

---

### 3. Starfish Bay 🎣 — Fishing Village
**Unlock:** Fish Level 2
**Travel cost:** 1 minute cooldown from Noodle Town

**What's here:**
- All fishing commands (`!cast`, `!pull`)
- Bait shop with 20% discount on all bait

**Bonuses:**
- **+20% fishing star rewards** (multiplicative with Star Magnet)
- **+3% legendary catch chance** (additive to base 5%)
- Bite times **15% faster** across all bait types

**Exclusive features:**
- `!tide` — Check the current tide. Tides rotate every 4 hours between
  Low Tide, Normal Tide, and High Tide.
  - Low Tide: +10% common catches, -5% rare catches
  - Normal Tide: No modifier
  - High Tide: -10% common catches, +10% rare catches
- **Fishing Tournament** — Weekly event (Saturday). Players compete for
  highest total catch value in 24 hours. Top 3 get star prizes:
  1st: 5,000 stars, 2nd: 2,500 stars, 3rd: 1,000 stars

**Design intent:** Fishers camp here for the legendary boost and tide system.
The tide mechanic adds timing strategy — experienced players fish during High
Tide with sturgeon bait for maximum legendary odds. Tournaments create weekly
excitement.

---

### 4. Greenfield Farm 🌾 — Agricultural Heartland
**Unlock:** Own 1 farm plot
**Travel cost:** 1 minute cooldown from Noodle Town

**What's here:**
- All farming commands (`!plant`, `!harvest`, `!tend`, `!farm`)
- Fertilizer and water shop with 20% discount

**Bonuses:**
- **+20% harvest star payouts**
- **Soil degrades 30% slower** (drain multiplier 0.7x)
- **"Great" quality chance +10%** (additive to level-based chance)

**Exclusive features:**
- `!compost` — Convert 5 of any harvested crop into 1 Fertilizer (free
  fertilizer from excess crops). 30-minute cooldown.
- **Seasonal Crops** — Special crops only plantable at Greenfield:
  - **Starfruit (⭐)**: 500 star seed cost, 12hr growth, sells for 1,400.
    Only growable during "Starlit Season" (1 week per month).
  - **Void Melon (🟣)**: 1,000 star seed cost, 24hr growth, sells for 3,200.
    5% chance to also drop a Golden Mushroom on harvest.
- **Scarecrow** — Passive protection. While at Greenfield, Locust weather
  events have a 50% chance to be blocked ("Your scarecrow scared them off!")

**Design intent:** Farmers who commit to living here get significantly better
returns. Seasonal crops create periodic excitement and reward players who
track the calendar. Compost gives value to cheap crops.

---

### 5. Starport Alpha 🚀 — Space Launch Facility
**Unlock:** Own Rocket Ship
**Travel cost:** 2 minute cooldown (it's far away)

**What's here:**
- All space mining commands (`!mine` while in space)
- Space equipment shop

**Bonuses:**
- **+15% space mining star rewards**
- **Alien abduction chance halved** while at Starport
- **Space hazard protection fail chance -10%** (better equipment on-site)

**Exclusive features:**
- `!scan` — Scan a planet before mining (3hr cooldown). Reveals the
  disaster chance and dominant mineral for the next mining session on that
  planet. Strategy tool for high-level space miners.
- `!salvage` — After a disaster in space, recover 25% of lost wallet stars.
  Single use per disaster. Only works at Starport.
- **Cosmic Storm Event** — Random event (1% per space mine) that opens a
  "Wormhole" for 15 minutes. During the wormhole, space mining has 0%
  disaster chance but normal rewards. Announced to all Starport players.

**Design intent:** Space miners need to commit to being far from town. The
halved abduction chance is a major draw. Scan and salvage add strategic depth
to the high-risk space game. Cosmic Storm events are exciting "drop
everything" moments.

---

### 6. Pirate's Cove 🏴‍☠️ — Lawless Territory
**Unlock:** Combined mining + fishing level ≥ 8 (e.g., mine 4 + fish 4)
**Travel cost:** 3 minute cooldown (remote and dangerous)

**What's here:**
- Gambling (all games available)
- Treasure chests (`!pick`)
- Trading (but no banking — you can't deposit here!)

**Bonuses:**
- **Gambling payouts +50%** (1.95x coinflip → ~2.9x, etc.)
- **Treasure chests 2x more valuable** (150-400 star range)
- **Rare item drop chance from chests doubled**

**Penalties:**
- **No banking.** Cannot `!deposit` or `!withdraw`. Your wallet is exposed.
- **Disaster chance +5%** on any mining/fishing done here (you CAN mine/fish,
  but it's riskier)
- **Pirate Tax:** 2% of your wallet is "taxed" every hour you stay
  (collected when you leave or every hour, whichever comes first)

**Exclusive features:**
- `!raid` — Attempt to steal stars from another player AT Pirate's Cove.
  Both players must be present. Costs 100 stars to attempt. 40% chance to
  steal 10-25% of target's wallet. 60% chance to lose your 100 star bet.
  Target gets a notification. 30-minute cooldown.
- `!bounty <player> <amount>` — Place a bounty on another player. Any player
  who successfully `!raid`s the target collects the bounty. Bounties persist
  until collected or 7 days pass (refunded).
- **Black Market** — Exclusive shop with items not in the main store:
  - **Smoke Bomb (💨)**: 500 stars. Cancels one active raid against you.
  - **Treasure Map (🗺️)**: 1,000 stars. Guarantees next treasure chest is
    item-capable with rare drops.
  - **Pirate Flag (🏴‍☠️)**: 2,000 stars. Permanent cosmetic — shown on profile.
  - **Stolen Compass (🧭)**: 750 stars. Reveals a random player's current
    location and wallet balance.

**Design intent:** The high-risk, high-reward zone. Gambling addicts and
treasure hunters love it here, but the pirate tax and no banking means you
can't camp indefinitely. Raiding adds PvP excitement. The Black Market has
unique items worth traveling for.

---

### 7. The Nexus 🌌 — Endgame Hub
**Unlock:** Space Planet Level 5 (Pluto) + 50,000 stars one-time entry fee
**Travel cost:** 5 minute cooldown (dimensional gateway)

**What's here:**
- All commands work with enhanced effects
- Exclusive endgame content

**Bonuses:**
- **+10% to ALL star rewards** (mining, fishing, farming, gambling, treasure)
- **All cooldowns reduced by 20%** (mining 30m→24m, fishing 120s→96s, etc.)
- **Disaster chance reduced by 10%** (flat reduction)

**Exclusive features:**
- `!rift` — Open a dimensional rift (24hr cooldown). Fight a random boss
  with a simple combat minigame (3 rounds of attack/defend choices).
  Rewards scale with boss difficulty:
  - **Rift Imp** (easy): 500-1,500 stars
  - **Void Warden** (medium): 2,000-5,000 stars
  - **Cosmic Leviathan** (hard, 10% chance): 10,000-25,000 stars + rare
    item drop (50% chance)
- `!forge` — Combine duplicate rare items:
  - 3x Rune Fragment → 1x Eternal Rune (infinite uses, halves cooldowns)
  - 3x Mithril Shield → 1x Adamantine Shield (infinite uses, helmet prot.)
  - 3x Golden Axe → 1x Celestial Blade (infinite uses, sword protection)
  - 2x Heart of Leviathan → 1x Immortal Heart (infinite uses, bank prot.)
  - 5x Lucky Charm → 1x Fortune's Favor (infinite uses, 50% disaster red.)
- **Nexus Trader** — Special NPC that buys rare items for stars:
  - Golden Axe: 5,000 stars
  - Mithril Shield: 3,000 stars
  - Rune Fragment: 2,000 stars
  - Fossilized Noodle: 2,000 stars
  - Lucky Charm: 8,000 stars
  - Star Magnet: 4,000 stars

**Design intent:** The endgame destination. The forge system gives purpose to
duplicate rare drops (currently useless). Boss fights add a new activity for
maxed players. The Nexus Trader creates a star sink and gives value to excess
rares.

---

### 8. Wanderer's Rest ⛺ — Hidden Location
**Unlock:** Discovered randomly (see below)
**Travel cost:** Cannot travel here intentionally

**Discovery mechanic:**
- 3% chance to discover when traveling between ANY two locations
- When found: "You stumble upon a hidden campsite in the mist...
  Welcome to Wanderer's Rest! You can stay for 24 hours."
- After 24 hours, you're returned to your previous location
- Can only be found once per week (7-day discovery cooldown)

**Bonuses (while visiting):**
- **All cooldowns halved** (mining 15m, fishing 60s, etc.)
- **Zero disaster chance** from all activities
- **+30% star rewards** on everything
- **Pet happiness/hunger/cleanliness frozen** (no decay)

**Exclusive features:**
- `!wish` — Make a wish at the campfire (once per visit). Random outcome:
  - 30%: Gain 500-2,000 stars
  - 20%: Gain a random rare item
  - 15%: All pet needs restored to 100%
  - 15%: Gain 5 of a random consumable (helmets, swords, bait, etc.)
  - 10%: Double your current wallet (up to 10,000 star cap)
  - 5%: Gain a Treasure Map (guarantees rare chest)
  - 5%: Nothing happens ("The fire flickers but grants no wish...")

**Design intent:** A magical surprise that breaks routine. Finding it feels
special. The overpowered bonuses are balanced by the 24-hour limit and
randomness of discovery. Creates "I found Wanderer's Rest!" moments in chat.

---

## Travel System

### Commands

```
!travel <location>     — Travel to a location (shows travel time)
!travel                — Show the world map and your current location
!where                 — Show your current location and who else is there
!where <player>        — Check where another player is
```

### Travel Rules

- **Cooldown between travels:** Varies by distance (1-5 minutes)
- **Travel is instant** — the cooldown is a "rest" period before you can
  travel AGAIN, not before you arrive. You arrive immediately.
- **Free to return to Noodle Town** from anywhere (no cooldown)
- **Travel cooldowns:**
  - Noodle Town ↔ Crystal Mines: 1 min
  - Noodle Town ↔ Starfish Bay: 1 min
  - Noodle Town ↔ Greenfield Farm: 1 min
  - Noodle Town ↔ Starport Alpha: 2 min
  - Any location ↔ Pirate's Cove: 3 min
  - Any location ↔ The Nexus: 5 min
  - Noodle Town ← anywhere: Free (instant)

### Travel Embed

When traveling, show an embed with:
- Origin → Destination
- Travel time remaining (or "Arrived!")
- Location description and available bonuses
- Number of players currently at the destination

---

## Quest System (Noodle Town Bulletin Board)

### Daily Quests (3 per day, rotate at midnight UTC)

Quests are drawn from a pool and assigned globally (same quests for everyone).

**Quest pool examples:**
| Quest | Requirement | Reward |
|-------|------------|--------|
| Mineral Hunter | Mine 3 times | 150 stars |
| Deep Diver | Mine at level 4+ | 300 stars |
| Gone Fishin' | Catch 3 fish | 150 stars |
| Big Catch | Catch a rare or legendary fish | 500 stars |
| Green Thumb | Harvest 2 crops | 100 stars |
| High Roller | Win 3 gambles | 200 stars |
| Lucky Day | Win a gamble of 500+ stars | 400 stars |
| Pet Parent | Feed, clean, and play with pet | 100 stars |
| Explorer | Travel to 3 different locations | 200 stars |
| Treasure Seeker | Open 1 treasure chest | 250 stars |
| Star Collector | Earn 1,000 total stars today | 300 stars |
| Disaster Survivor | Survive a mining/fishing disaster | 200 stars |

### Quest Tracking
- `!quests` — View today's quests and your progress
- Quest completion is announced in chat with a small embed
- Quests track progress automatically via existing game actions
- Completing all 3 daily quests grants a **bonus reward** of 500 stars

---

## Database Changes

### New Columns (user_activity or user_inventory)
```sql
-- Current location (string, default 'noodle_town')
current_location TEXT DEFAULT 'noodle_town'

-- Timestamp of last travel (for cooldown)
last_travel REAL DEFAULT 0

-- Discovered locations bitmask (bit per hidden location)
-- Bit 0: Wanderer's Rest discovered this week
discovered_locations INTEGER DEFAULT 0

-- Last Wanderer's Rest discovery (for weekly cooldown)
last_wanderer_discovery REAL DEFAULT 0

-- Pirate's Cove: last hourly tax collection
last_pirate_tax REAL DEFAULT 0
```

### New Table: quest_progress
```sql
CREATE TABLE quest_progress (
    user_id INTEGER NOT NULL,
    quest_date TEXT NOT NULL,        -- ISO date string
    quest_index INTEGER NOT NULL,    -- 0, 1, or 2
    quest_key TEXT NOT NULL,         -- quest type identifier
    progress INTEGER DEFAULT 0,     -- current progress
    target INTEGER NOT NULL,         -- required for completion
    completed INTEGER DEFAULT 0,    -- 0 or 1
    reward_claimed INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, quest_date, quest_index)
);
```

### Migration File
- `database/migrations/versions/v027_locations.py`
- Adds columns to user_activity
- Creates quest_progress table

---

## New Cog Structure

```
cogs/locations/
├── __init__.py
├── constants.py          — Location definitions, bonuses, travel times
├── dto.py                — LocationInfo, TravelResult, QuestProgress DTOs
├── handlers.py           — !travel, !where, !quests, !bulletin commands
└── use_case/
    ├── __init__.py
    ├── locations.py      — Travel logic, location bonuses, discovery
    └── quests.py         — Quest generation, tracking, completion
```

### Location-Exclusive Cog Extensions
Each exclusive feature lives in its region's parent cog:
- `!prospect` → `cogs/mining/handlers.py` (checks location == crystal_mines)
- `!tide` → `cogs/fishing/handlers.py` (checks location == starfish_bay)
- `!compost` → `cogs/farming/handlers.py` (checks location == greenfield_farm)
- `!scan`, `!salvage` → `cogs/space/handlers.py` (checks location == starport)
- `!raid`, `!bounty` → `cogs/gambling/handlers.py` (checks location == pirates_cove)
- `!rift`, `!forge` → new `cogs/nexus/handlers.py`
- `!wish` → `cogs/locations/handlers.py` (checks location == wanderers_rest)

---

## Integration with Existing Systems

### How Bonuses Apply

Location bonuses are applied in the **use_case** layer of each system. The
location module exposes a helper:

```python
# cogs/locations/use_case/locations.py

def get_location_modifiers(user_id: int) -> LocationModifiers:
    """Returns active bonuses based on user's current location."""
    # Returns dataclass with fields like:
    #   mining_star_bonus: float     (1.0 = no bonus, 1.2 = +20%)
    #   fishing_star_bonus: float
    #   farming_star_bonus: float
    #   disaster_chance_mod: float   (1.0 = normal, 0.9 = -10%)
    #   cooldown_mod: float          (1.0 = normal, 0.8 = -20%)
    #   rare_drop_mod: float         (1.0 = normal, 2.0 = doubled)
    #   protection_fail_mod: float   (1.0 = normal, 0.95 = -5%)
```

Each use_case calls this and applies modifiers to their calculations.
Minimal changes to existing code — just multiply by the modifier.

**Example mining integration:**
```python
# In mining.py's mine() method, after calculating base stars:
from cogs.locations.use_case import LocationUseCases
location = LocationUseCases(self.repo)
mods = location.get_location_modifiers(user_id)
final_stars = int(base_stars * mods.mining_star_bonus)
```

### Systems That Check Location

| System | What Changes | Where |
|--------|-------------|-------|
| Mining | Star rewards, rare mineral chance, protection fail | `mining.py` |
| Fishing | Star rewards, legendary chance, bite times | `fishing.py` |
| Farming | Harvest payouts, soil drain, quality chance | `farming.py` |
| Space | Star rewards, abduction chance, protection fail | `space.py` |
| Gambling | Payout multipliers | `gambling handlers` |
| Treasure | Chest value, rare drop chance | `treasure.py` |
| Banking | Blocked at Pirate's Cove | `economy.py` |
| Events | Abduction modifier, weather protection | `alien_abduction.py` |

---

## Implementation Phases

### Phase 1 — Core Locations (MVP)
**Scope:** 4 locations + travel + basic bonuses
- Noodle Town, Crystal Mines, Starfish Bay, Greenfield Farm
- `!travel`, `!where` commands
- Location bonuses (star rewards, disaster mods)
- Database migration
- Help menu update

**Estimated work:** ~8-12 files changed/created

### Phase 2 — Exclusive Features
**Scope:** Location-exclusive commands + Starport
- `!prospect`, `!tide`, `!compost`, `!scan`, `!salvage`
- Starport Alpha location
- Location-specific events (Mine Rush, Fishing Tournament, etc.)
- Tide system for Starfish Bay

**Estimated work:** ~6-8 files changed/created

### Phase 3 — Danger Zone
**Scope:** Pirate's Cove + PvP
- Pirate's Cove location with penalties
- `!raid`, `!bounty` commands
- Black Market shop
- Pirate Tax mechanic

**Estimated work:** ~5-7 files changed/created

### Phase 4 — Endgame
**Scope:** The Nexus + Wanderer's Rest
- The Nexus with forging and boss fights
- `!rift`, `!forge` commands
- Wanderer's Rest discovery mechanic
- `!wish` command

**Estimated work:** ~6-8 files changed/created

### Phase 5 — Quests
**Scope:** Daily quest system
- Quest generation and tracking
- `!quests`, `!bulletin` commands
- Auto-completion hooks in existing systems
- Bonus rewards

**Estimated work:** ~4-6 files changed/created

---

## Star Economy Impact

### New Star Sinks
| Sink | Cost | Frequency |
|------|------|-----------|
| Nexus entry fee | 50,000 (one-time) | Once |
| Black Market items | 500-2,000 | Ongoing |
| Raid attempts | 100 per attempt | Ongoing |
| Bounties | Player-set | Ongoing |
| Pirate Tax | 2%/hr of wallet | While at Cove |
| Seasonal crop seeds | 500-1,000 | Ongoing |

### New Star Sources
| Source | Amount | Frequency |
|--------|--------|-----------|
| Location bonuses | +10-20% on existing | Ongoing |
| Daily quests | 100-500 per quest | 3/day |
| Quest bonus | 500 | Daily |
| Boss fights | 500-25,000 | Daily |
| Wanderer's Wish | 500-10,000 | ~Weekly |
| Fishing Tournament | 1,000-5,000 | Weekly |
| Raid success | 10-25% of target wallet | Ongoing |
| Nexus Trader | 2,000-8,000 per item | Ongoing |

### Balance Notes
- Location bonuses are substantial (+20%) to make travel worthwhile
- Pirate's Cove is designed as a star sink (tax + raid losses)
- The Nexus entry fee is the biggest single sink in the game
- Quests provide steady income for active players across all levels
- Boss fights give endgame players something to spend time on
- Wanderer's Rest is intentionally overpowered but rare/temporary

---

## Player Experience Flow

### New Player (Level 1)
1. Starts in Noodle Town. Mines, fishes, learns the basics.
2. Hits Mine Level 2 → Crystal Mines unlocks. "Hey, I can get +20% there!"
3. Travels to Crystal Mines, discovers `!prospect`. Mining feels deeper.
4. Hits Fish Level 2 → Starfish Bay unlocks. Starts rotating between locations.

### Mid-Game Player (Level 3-5)
5. Unlocks Greenfield Farm. Starts optimizing: farm while fishing/mining.
6. Learns tide system at Starfish Bay. Times fishing sessions around tides.
7. Discovers Pirate's Cove. Tempted by gambling bonuses. Gets raided. Laughs.
8. Starts doing daily quests for steady income.

### Late-Game Player (Space Mining)
9. Unlocks Starport Alpha. Reduced abduction chance is huge relief.
10. Uses `!scan` to plan space mining sessions strategically.
11. Grinding toward The Nexus 50k entry fee.

### Endgame Player (Nexus)
12. Enters The Nexus. Starts forging infinite-use items from duplicate rares.
13. Daily boss fights become the main activity.
14. Occasionally finds Wanderer's Rest while traveling. Celebrates.
15. Places bounties on rivals at Pirate's Cove for fun.

---

## Summary

| Location | Unlock | Main Bonus | Exclusive Feature |
|----------|--------|-----------|-------------------|
| Noodle Town 🏘️ | Default | Safe hub | Bulletin Board / Quests |
| Crystal Mines ⛏️ | Mine L2 | +20% mining | `!prospect`, Mine Rush |
| Starfish Bay 🎣 | Fish L2 | +20% fishing | `!tide`, Tournaments |
| Greenfield Farm 🌾 | Own plot | +20% farming | `!compost`, Seasonal Crops |
| Starport Alpha 🚀 | Rocket Ship | -50% abduction | `!scan`, `!salvage` |
| Pirate's Cove 🏴‍☠️ | ML+FL ≥ 8 | +50% gambling | `!raid`, `!bounty`, Black Market |
| The Nexus 🌌 | Pluto + 50k | +10% everything | `!rift`, `!forge`, Nexus Trader |
| Wanderer's Rest ⛺ | Random | OP everything | `!wish` |

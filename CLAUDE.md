# Noodle Star Bot - Project Instructions

## CRITICAL: Git Branch Rules

- **NEVER push to `main` without explicit user approval.** Pushing to main deploys to the live bot and can crash or corrupt the game for all players.
- **Always push to `stage` first.** Stage is the testing branch.
- When the user says "push", assume they mean `stage` unless they specifically say "main".
- Always confirm before pushing to `main`: "Want me to push to main as well?"

## Project Overview

Discord bot ("Noodle Star Bot") built with discord.py using `commands.Cog` pattern. Players earn "noodle stars" through mining, fishing, farming, gambling, and trading.

## Architecture

### Cog Package Layout

Each feature lives in `cogs/<domain>/` with this structure:
- `constants.py` - Static data (mineral tables, level configs, hazard definitions)
- `dto.py` - Data transfer objects (dataclasses for results/state)
- `handlers.py` - Discord command handlers (thin layer, calls use_cases)
- `use_case/<domain>.py` - Business logic (the meat of each feature)

### Core Domains

| Cog | Purpose |
|-----|---------|
| `mining/` | Mine minerals for stars, 5 levels + 5 space planets |
| `fishing/` | Cast/pull minigame, bait tiers, 5 levels |
| `farming/` | Plant/harvest crops, passive income |
| `space/` | Space mining (extends mining to planets after level 5) |
| `gambling/` | Coinflip, blackjack, duels, roulette |
| `economy/` | Stars, banking, leaderboards, profiles |
| `shop/` | Store, inventory, item purchases |
| `trading/` | Player-to-player trades |
| `treasure/` | Lock-picking chest minigame |
| `events/` | Random events (alien abduction, farming weather) |
| `moderator/` | Admin commands |
| `dev/` | Developer tools |

### Key Files

- `bot.py` / `main.py` - Bot startup and cog loading
- `config/models.py` - Shared dataclasses (Mineral, MineHazard, ShopItem, BaitTier, Catch, Crop)
- `database/repository.py` - Main database interface
- `database/repositories/` - Domain-specific repository modules (inventory, economy, achievements, gambling)
- `database/migrations/versions/` - Sequential migrations (v001-v023+)
- `utils/help.py` - Interactive button-based help menu with category embeds

### Protection System

- **Helmet** - Blocks helmet-type hazards (collapse, flood, meteor, solar flare)
- **Sword** - Blocks sword-type hazards (goblin, troll, pirate, black hole, void entity)
- **Golden Axe** - Multi-use sword protection (never fails)
- **Mithril Shield** - Multi-use helmet protection (never fails)
- Basic helmet/sword have `protection_fail_chance` that scales with level difficulty
- Each level/planet has unique `helmet_fail_msg` and `sword_fail_msg` in constants
- Siren and Leviathan hazards (`requires_special`) ignore basic helmet/sword

### Rare Effect Items

Dropped from mining/fishing, survive disasters (`clear_user_inventory` preserves them):
- Rune Fragment (30 uses) - Halves mining cooldowns
- Fossilized Noodle (30 uses) - 1 min mining cooldown
- Bucktail Jig - 20% legendary fishing chance on next cast
- Ray-Gun (3 uses, also in shop for 5,000 stars) - Alien abduction item protection
- Star Magnet (20 uses) - +15% stars on mining/fishing
- Lucky Charm (50 uses) - 50% disaster chance reduction (multiplicative)
- Heart of Leviathan (1 use) - Full bank protection from one disaster

### Difficulty Progression

Mine L1-5 -> Fish L1-5 -> Space P1-5 (15 levels total)

Protection fail chances scale: 0% (L1) up to 50% (Space P5)

### Database

SQLite with manual migration system. New columns require:
1. Migration file in `database/migrations/versions/`
2. Column added to `_INVENTORY_COLUMNS` in `database/repositories/inventory.py`
3. Column in `_ensure_inventory_row` INSERT and `get_user_inventory` SELECT

### Conventions

- Shop items defined in `cogs/shop/constants.py` as `ShopItem` dataclasses with aliases
- Consumable items stack; permanent items (gold_pickaxe, telescope, rocket_ship) don't
- `clear_user_inventory` wipes basic items on disaster; `clear_all_items` wipes everything (alien abduction)
- Alien abductions are exempt from `deposit` and `withdraw` commands
- Help menu in `utils/help.py` uses discord.ui.View buttons with embed pages

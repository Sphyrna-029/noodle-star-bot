# Noodle Star Bot - Project Instructions

## CRITICAL: Git Branch Rules — READ THIS FIRST

**DEFAULT BEHAVIOR: Every `git push` goes to `stage` ONLY. Never touch `main` unless the user says "main" in that specific message.**

Pushing to main deploys to the live bot and can crash or corrupt the game for all players.

Rules:
1. **Always push to `stage` only.** This is the default for every commit. Do `git push origin stage` and STOP.
2. **NEVER push to `main` unless the user explicitly says "main" or "push to main" in the CURRENT message.** Not a previous message — the current one.
3. **After pushing to stage, ask:** "Want me to push to main as well?" — then WAIT for the user to respond. Do NOT push to main in the same command.
4. **"Push to main" approval is single-use.** It authorizes ONE push. The next commit goes to stage only, and you must ask again.
5. When the user says "push" with no branch specified, that means `stage`.
6. When the user says "push to main", push stage to main with: `git push origin stage:main` — but ONLY after stage is up to date.

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

### Combat & Ambush System

- Disasters replaced with interactive **combat ambush encounters** in mining, fishing, and space mining
- Ambush chance per level, halved by Lucky Charm
- Turn-based combat with Attack/Defend/Flee buttons via `discord.ui.View`
- Combat gear: 26 items across 5 tiers (4 store-bought, 20 crafted, 2 drop-only)
- **Golden Axe** (Tier 3 weapon) and **Mithril Shield** (Tier 3 shield) are permanent drop-only combat items from fishing/treasure
- Legacy helmet/sword items removed — existing users converted to iron_shield/iron_sword via migration v034

### Rare Effect Items

Dropped from mining/fishing, survive combat defeats (`clear_user_inventory` preserves them):
- Rune Fragment (30 uses) - Halves mining cooldowns
- Fossilized Noodle (30 uses) - 1 min mining cooldown
- Bucktail Jig - 20% legendary fishing chance on next cast
- Ray-Gun (3 uses, also in shop for 5,000 stars) - Lets you fight the alien during abduction (+75 ATK both sides)
- Star Magnet (20 uses) - +15% stars on mining/fishing/space mining
- Lucky Charm (50 uses) - 50% ambush chance reduction (multiplicative)
- Heart of Leviathan (1 use) - Full bank protection from one combat defeat

### Difficulty Progression

Mine L1-5 -> Fish L1-5 -> Space P1-5 (15 levels total)

Ambush chance scales by level/planet (halved by Lucky Charm).

### Database

SQLite with manual migration system. Migrations in `database/migrations/versions/` (v001-v034+).
Inventory uses 3-table split: `user_equipment`, `user_inventory_items`, `user_progression`.
Routing managed by `_EQUIPMENT_KEYS`, `_OWNERSHIP_MAP`, `_PROGRESSION_KEYS`, `_CONSUMABLE_KEYS` in `database/repositories/inventory.py`.

### Help Menu

- **Always update the help menu** (`utils/help.py`) when adding or changing player-facing features.
- Use an existing category embed if the change fits (Mining, Fishing, Items, Shop, etc.).
- Add a new button/category only when the feature doesn't belong in any existing section.
- Both `HelpView` (main menu) and `SubHelpView` (sub-pages) need the button added.

### Conventions

- Shop items defined in `cogs/shop/constants.py` as `ShopItem` dataclasses with aliases
- Consumable items stack; permanent items (gold_pickaxe, telescope, rocket_ship, combat gear) don't
- `clear_user_inventory` wipes inventory items (resources); `clear_all_items` wipes equipment AND inventory (alien abduction)
- Alien abductions are exempt from `deposit` and `withdraw` commands
- Help menu in `utils/help.py` uses discord.ui.View buttons with embed pages

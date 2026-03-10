# Inventory Overhaul — Complete Implementation Plan

## Overview

Convert all resource gathering (mining, fishing, farming, space mining) from instant star payouts to inventory items that players must sell. Split the single `user_inventory` table into three normalized tables: Equipment, Inventory, and Progression.

---

## 1. New Database Schema

### Table: `user_equipment` — Permanent items, survive disasters

```sql
CREATE TABLE IF NOT EXISTS user_equipment (
    user_id     INTEGER NOT NULL,
    item_key    TEXT    NOT NULL,
    uses        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, item_key)
);
CREATE INDEX IF NOT EXISTS idx_user_equipment_user ON user_equipment(user_id);
```

**Equipment items (17 total):**

| Item Key | Type | Uses Meaning |
|----------|------|-------------|
| `gold_pickaxe` | Boolean | 1=owned, 0=not |
| `telescope` | Boolean | 1=owned |
| `rocket_ship` | Boolean | 1=owned |
| `helmet` | Stackable | Count of helmets |
| `sword` | Stackable | Count of swords |
| `golden_axe` | Durability | Remaining uses (50) |
| `mithril_shield` | Durability | Remaining uses (10) |
| `bank_insurance` | Stackable | Count of insurances |
| `rune_fragment` | Durability | Remaining uses (30) |
| `fossilized_noodle` | Durability | Remaining uses (30) |
| `bucktail_jig` | Stackable | Count of jigs |
| `ray_gun` | Durability | Remaining uses (3) |
| `star_magnet` | Durability | Remaining uses (20) |
| `lucky_charm` | Durability | Remaining uses (50) |
| `heart_of_leviathan` | Durability | Remaining uses (1) |
| `preserver` | Boolean | 1=owned |
| `growbot` | Boolean | 1=owned |

### Table: `user_inventory_items` — Slotted items, wiped by disasters

```sql
CREATE TABLE IF NOT EXISTS user_inventory_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    item_key    TEXT    NOT NULL,
    category    TEXT    NOT NULL,       -- "mineral", "fish", "ore", "crop", "consumable"
    base_sell_value INTEGER NOT NULL DEFAULT 0,
    quality     TEXT,                   -- For crops: "bad", "normal", "great"
    acquired_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_inventory_items_user ON user_inventory_items(user_id);
CREATE INDEX IF NOT EXISTS idx_inventory_items_user_item ON user_inventory_items(user_id, item_key);
```

**No stacking** — each item is one row, one slot. Starting capacity: 50 slots, upgradeable to 70 via bag purchases.

**What goes here:**
- Mined minerals (25 types across 5 mine levels)
- Caught fish (75 types across 5 fishing levels)
- Space ores (25 types across 5 planets)
- Harvested crops (5 crop types × 3 quality levels, with baked-in sell value)
- Consumables: `raw_potato`, `golden_mushroom`, `bait_worm`, `bait_herring`, `bait_sturgeon`, `fertilizer`, `water`

### Table: `user_progression` — Levels, machine state, capacity

```sql
CREATE TABLE IF NOT EXISTS user_progression (
    user_id                 INTEGER PRIMARY KEY,
    mine_level              INTEGER NOT NULL DEFAULT 1,
    active_mine_level       INTEGER NOT NULL DEFAULT 1,
    active_fish_level       INTEGER NOT NULL DEFAULT 1,
    space_planet_level      INTEGER NOT NULL DEFAULT 0,
    active_space_planet     INTEGER NOT NULL DEFAULT 0,
    farm_level              INTEGER NOT NULL DEFAULT 1,
    farm_plots              INTEGER NOT NULL DEFAULT 0,
    first_weather_bonus     INTEGER NOT NULL DEFAULT 0,
    inventory_capacity      INTEGER NOT NULL DEFAULT 50,
    equipped_bait           TEXT,
    jig_active              INTEGER NOT NULL DEFAULT 0,
    preserver_level          INTEGER NOT NULL DEFAULT 0,
    preserver_pending_stars  INTEGER NOT NULL DEFAULT 0,
    preserver_ready_ts       INTEGER NOT NULL DEFAULT 0,
    growbot_level            INTEGER NOT NULL DEFAULT 0
);
```

---

## 2. Resource Item Catalog — 130 Total

### Minerals (25) — Category: `mineral`, Home: `crystal_cave`

| Level | Items (5 per level) |
|-------|-------------------|
| L1 Surface | Stone(5), Coal(10), Iron(20), Gold(40), Diamond(100) |
| L2 Caverns | Sandstone(8), Copper(15), Silver(30), Emerald(60), Ruby(150) |
| L3 Deep Tunnels | Slate(12), Tin(25), Platinum(50), Sapphire(90), Amethyst(225) |
| L4 Molten Core | Obsidian(20), Titanium(40), Mithril(80), Opal(140), Star Fragment(350) |
| L5 The Abyss | Darkite(30), Adamantium(60), Dragonstone(120), Void Crystal(200), Noodle Gem(500) |

### Fish (75) — Category: `fish`, Home: `starfish_bay`

15 per level (including ~2 zero-value junk items per level). 8 total junk items (Old Boot, Seaweed, Tin Can, Driftwood, River Stone, Sea Sponge, Barnacle Cluster, Void Coral) with 0 sell value — still go to inventory, take up slots, must be trashed.

### Space Ores (25) — Category: `ore`, Home: `starport_ziti`

| Planet | Items (5 per planet) |
|--------|---------------------|
| P1 Moon | Moon Dust(45), Helium-3(90), Lunar Quartz(180), Selenite(300), Cosmic Pearl(750) |
| P2 Mars | Red Sand(65), Martian Iron(130), Phobos Shard(260), Olympus Ruby(430), Stardust Crystal(1075) |
| P3 Saturn | Ring Fragment(90), Titan Ore(180), Ammonia Ice(360), Saturn Sapphire(600), Nova Core(1500) |
| P4 Uranus | Ice Rock(125), Methane Crystal(250), Miranda Stone(500), Uranian Diamond(830), Nebula Shard(2075) |
| P5 Pluto | Frozen Nitrogen(175), Charon Basalt(350), Dark Matter(700), Plutonium Core(1150), Eternity Gem(2875) |

### Crops (5) — Category: `crop`, Home: `fusilli_farms`

Wheat(40 base), Carrot(90), Corn(200), Tomato(440), Melon(960). Mushroom excluded (yields golden_mushroom consumable instead).

**Crop quality**: Quality is rolled at harvest time. The final sell value is **baked into the item** at harvest (base × quality_mult × weather_mult × soil_mult). No re-computation at sell time. Harvest message still shows quality feedback.

---

## 3. Core Flow Changes

### Mining / Fishing / Space Mining — Before vs After

**BEFORE:**
1. Player mines → mineral selected → stars added to wallet immediately
2. Disaster rolls → wallet/bank % lost

**AFTER:**
1. Player mines → mineral selected → **item added to inventory** (no stars)
2. Disaster rolls → wallet/bank % lost (based on existing wallet, not the new item)
3. Player uses `!sell` later to convert items to stars

### Farming — Before vs After

**BEFORE:**
1. Player harvests → quality rolled → stars added immediately

**AFTER:**
1. Player harvests → quality rolled → **crop item added to inventory** with baked-in sell value
2. Player uses `!sell` to get stars

### Inventory Full Behavior

When inventory is full (all slots occupied):
- **Mining/Space Mining**: Action is **BLOCKED**. Cooldown NOT consumed. Message: "Your inventory is full! Use `!sell` to clear space."
- **Fishing**: Check at **pull time**. If full, catch is lost. "Your inventory is full — the fish got away!"
- **Farming**: Harvest as many crops as fit. Warn about remaining: "Inventory full! X crops left unharvested."

### Star Magnet — Move to Sell Time

Currently applies at mine/fish time (+15%). After overhaul, Star Magnet applies at **sell time** instead:
- Simpler: items have fixed base values, no per-instance boosted prices
- Consume 1 use per `!sell` command (not per item)
- Retroactive benefit: get Star Magnet after mining, still applies to items already in inventory

---

## 4. The `!sell` Command

### Location & Placement

Add to `cogs/shop/` alongside buy logic. New files:
- `cogs/shop/resources.py` — Resource catalog with all sellable items, aliases, categories
- `cogs/shop/use_case/sell.py` — Sell business logic

### Commands

| Command | Description |
|---------|------------|
| `!sell <item_name>` | Sell all of a specific item |
| `!sell <item_name> <count>` | Sell N of a specific item |
| `!sell all` | Sell everything in inventory |
| `!sell <category>` | Sell all items in a category (minerals, fish, crops, ores) |
| `!trash <item_name>` | Discard junk items (0-value fish) without stars |

### Location-Based Sell Bonuses

Sell can be done from **any location**. Bonuses:

| Location | Bonus | Example |
|----------|-------|---------|
| **Noodle Town** | +25% | Selling anything at town |
| **Non-home activity location** | +10% | Selling fish at Crystal Cave |
| **Home location** | +0% | Selling fish at Starfish Bay |

Home locations per category:
- Minerals → Crystal Cave
- Fish → Starfish Bay
- Crops → Fusilli Farms
- Space Ores → Starport Ziti

### Sell Flow

1. Resolve item name via alias lookup
2. Check player has the item in inventory
3. Get current location → calculate bonus %
4. Check Star Magnet → add +15% if available, consume 1 use
5. Calculate: `final = base_value × (1 + location_bonus + magnet_bonus)`
6. Remove items from inventory, add stars to wallet
7. Show receipt with breakdown

### Sell Result Message Format

```
💰 Sold Iron x5

Base value: 100 stars (20 each)
📍 Location: Noodle Town (+25%)
🧲 Star Magnet: +15% (19 uses left)
Bonus: +40 stars

Total: 140 stars
New balance: 1,234 stars
```

---

## 5. Preserver Rework

**Current**: Preserver scans planted_crops for ready melons, rolls quality, computes value + bonus, stores as pending_stars.

**New flow**:
1. Player harvests melons normally → melon items go to inventory with baked-in sell_value
2. `!farm preserver start` → scans inventory for melon items, consumes them
3. Sums their sell_values, applies `PRESERVER_BONUS_BY_LEVEL` %
4. Stores total as `preserver_pending_stars`, starts timer
5. `!farm preserver collect` → pays out pending_stars as direct stars (unchanged)

**Output is stars, not items.** The preserver's value-add is the time-gated bonus percentage.

---

## 6. Disaster & Equipment Changes

### `clear_user_inventory()` — Disaster Wipe

**New behavior**: Wipe ALL inventory items (resources + consumables). Equipment is safe.
```sql
DELETE FROM user_inventory_items WHERE user_id = ?
```

### `clear_all_items()` — Alien Abduction

**New behavior**: Wipe BOTH equipment AND inventory items. Progression untouched.
```sql
DELETE FROM user_equipment WHERE user_id = ?
DELETE FROM user_inventory_items WHERE user_id = ?
```

Protected items (gold_pickaxe, telescope, rocket_ship, preserver, growbot) are snapshot'd before wipe and restored after, same as current alien abduction logic.

### Protection Item Checks

Protection items (helmet, sword, golden_axe, mithril_shield) are read from `user_equipment` table instead of inventory columns. Use-count decrementing: `UPDATE user_equipment SET uses = uses - 1 WHERE user_id = ? AND item_key = ?`

### Message Changes

- "Lost your items" → "Lost your resources"
- Disaster messages updated to reference inventory items being wiped, not specific item names

---

## 7. Inventory UI Redesign

### `!inventory` Display — Two Sections

```
🎒 PlayerName's Inventory

── EQUIPMENT ──
⛏️ Gold Pickaxe · 📷 Telescope · 🚀 Rocket Ship
🤖 Grow-Bot (Lv.2) · 🏭 Preserver (Lv.1)
🪖 Helmet x3 · ⚔️ Sword x2 · 💸 Insurance x1
🪓 Golden Axe (12 uses) · 🛡️ Mithril Shield (8 uses)
🧲 Star Magnet (18/20) · 🍀 Lucky Charm (42/50)

── INVENTORY (45/50) ──

⛏️ Minerals
🪨 Stone x2 · ⚫ Coal x3 · 💎 Diamond x1

🎣 Fish
🐟 Small Fish x4 · 🦀 Crab x2

🌾 Crops
🌾 Wheat (Normal) x2 · 🌾 Wheat (Great) x1

🧪 Supplies
🥔 Potato x5 · 🪱 Worm Bait x10

Bag: 45/50 slots | Upgrade at !store
```

### Color Coding

- Blue: < 90% full
- Orange: 90-99% full
- Red: 100% full

### Bag Upgrades

| Upgrade # | Capacity | Price |
|-----------|----------|-------|
| Base | 50 | — |
| 1 | 55 | 1,000 |
| 2 | 60 | 1,500 |
| 3 | 65 | 2,000 |
| 4 | 70 | 3,000 |
| **Total** | 70 max | **7,500** |

Store as `inventory_capacity` on `user_progression` table. Bag upgrades are permanent (survive disasters + alien abductions).

---

## 8. Migration Strategy

### Migration: `v031_inventory_redesign.py`

Single atomic migration:

1. **Create** `user_equipment`, `user_inventory_items`, `user_progression` tables
2. **Migrate progression** data from `user_inventory` → `user_progression`
3. **Migrate equipment** items from `user_inventory` columns → `user_equipment` rows (only where value > 0)
4. **Migrate consumables** from count columns → individual `user_inventory_items` rows (recursive CTE to expand counts)
5. **Rename** old table to `user_inventory_legacy_v031` (keep as backup)

### Backward-Compatible Shim

To avoid rewriting all 35+ call sites at once, provide legacy shim methods:

```python
def get_user_inventory(self, user_id) -> dict:
    """LEGACY SHIM: Returns same dict shape as before, reading from new tables."""

def update_user_inventory(self, user_id, item, amount) -> None:
    """LEGACY SHIM: Routes writes to correct table."""
```

This allows incremental migration of callers.

---

## 9. Implementation Phases

### Phase 1 — Database Foundation (Non-Breaking)
- Create v031 migration + 3 new tables
- Add new repository classes (`EquipmentRepository`, `InventoryItemsRepository`, `ProgressionRepository`)
- Add legacy shims so all existing code keeps working
- **Tests**: Verify migration preserves all existing data

### Phase 2 — Resource Gathering Conversion
- Mining: item → inventory instead of stars
- Fishing: catch → inventory instead of stars
- Space Mining: ore → inventory instead of stars
- Farming: crop → inventory instead of stars (with baked-in quality/value)
- Preserver rework (consume melon items from inventory)
- Move Star Magnet to sell time
- **Tests**: Verify all gathering gives items, not stars

### Phase 3 — Sell System
- Resource catalog (`cogs/shop/resources.py`)
- Sell use case + handlers (`!sell`, `!sell all`, `!sell <category>`, `!trash`)
- Location-based bonuses
- Star Magnet at sell time
- **Tests**: Verify sell prices, bonuses, edge cases

### Phase 4 — Inventory UI + Bag Upgrades
- Redesign `!inventory` display (equipment + inventory sections)
- Add bag upgrade shop item with escalating prices
- Capacity checks on all buy/gather actions
- Color-coded fullness warnings
- **Tests**: Display formatting, capacity limits

### Phase 5 — Disaster & Equipment Updates
- Update `clear_user_inventory` (resources only)
- Update `clear_all_items` (equipment + resources)
- Protection checks from equipment table
- Update disaster messages
- **Tests**: Disaster wipe scope, protection logic

### Phase 6 — Polish & Cleanup
- Remove legacy shims (migrate remaining callers to typed APIs)
- Drop `user_inventory_legacy_v031` backup table
- Update help menu for all new commands
- Update trading system for resource trades (optional)

---

## 10. Complete File Change List

### New Files (8)
| File | Purpose |
|------|---------|
| `database/migrations/versions/v031_inventory_redesign.py` | Migration creating 3 new tables + data migration |
| `database/repositories/equipment.py` | Equipment CRUD |
| `database/repositories/inventory_items.py` | Inventory items CRUD |
| `database/repositories/progression.py` | Progression state CRUD |
| `cogs/shop/resources.py` | Resource catalog (130 items with aliases, categories, prices) |
| `cogs/shop/use_case/sell.py` | Sell business logic |
| `cogs/shop/dto.py` (or add to existing) | SellResult, SellLineItem DTOs |
| `docs/inventory-overhaul-plan.md` | This plan document |

### Modified Files (~25)
| File | Changes |
|------|---------|
| `database/repository.py` | Compose new repos into UserRepository |
| `database/repositories/__init__.py` | Export new repo classes |
| `database/repositories/inventory.py` | Rewrite internals + add legacy shims |
| `database/repositories/mining.py` | `user_inventory` → `user_progression` queries |
| `database/repositories/fishing.py` | `user_inventory` → `user_progression` queries |
| `database/repositories/farming.py` | `user_inventory` → `user_progression` queries |
| `database/repositories/user_core.py` | Update JOINs for new tables |
| `database/models.py` | Update User class |
| `config/models.py` | Add ResourceItem dataclass, update ShopItem |
| `cogs/mining/use_case/mining.py` | Add item to inventory instead of stars |
| `cogs/mining/dto.py` | Add item_sell_value, inventory_full fields |
| `cogs/mining/handlers.py` | "Added to inventory" instead of "earned stars" |
| `cogs/fishing/use_case/fishing.py` | Add catch to inventory instead of stars |
| `cogs/fishing/dto.py` | Add item_sell_value, inventory_full fields |
| `cogs/fishing/handlers.py` | Update catch display messages |
| `cogs/space/use_case/space.py` | Add ore to inventory instead of stars |
| `cogs/space/dto.py` | Add item_sell_value, inventory_full fields |
| `cogs/space/handlers.py` | Update space mine display |
| `cogs/farming/use_case/crop_flow.py` | Harvest → inventory items with baked values |
| `cogs/farming/use_case/preserver.py` | Consume melon items from inventory |
| `cogs/farming/dto.py` | Update HarvestResult, StartPreserverResult |
| `cogs/farming/handlers.py` | Update harvest/preserver messages |
| `cogs/shop/handlers.py` | Add `!sell` command, redesign `!inventory` |
| `cogs/shop/use_case/shop.py` | Bag upgrade buy logic, inventory display |
| `cogs/shop/constants.py` | Add bag_upgrade ShopItem, update growbot/preserver db_columns |
| `cogs/events/alien_abduction.py` | Update wipe logic for new tables |
| `cogs/trading/use_case/trading.py` | Support resource trading (Phase 6) |
| `utils/help.py` | Add sell commands, update all gathering descriptions |

---

## 11. Key Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Crop quality | Bake sell value at harvest | Preserves quality excitement at harvest; simple sell logic |
| Star Magnet timing | Apply at sell time | Prevents per-instance value differences; simpler inventory |
| Inventory full (mining) | Block action | Less punishing than losing items |
| Inventory full (fishing) | Catch lost at pull | Bait already consumed at cast |
| Zero-value fish | Go to inventory | Adds inventory management depth |
| Preserver output | Stars (not items) | Avoids extra sell step; bonus is the time-gated % |
| Bag upgrades | Permanent, survive disasters | QoL progression, not items |
| Stacking | No stacking (1 item = 1 slot) | Per design spec |
| Star Magnet uses | 1 per sell command | Matches current "1 per action" pattern |
| Disaster scope | Wipe resources + consumables only | Equipment is permanent |
| Location bonuses | Additive with Star Magnet | 25% town + 15% magnet = 40% total |

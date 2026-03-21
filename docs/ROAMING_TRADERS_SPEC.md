# Roaming Traders — Feature Spec

## Overview

Two roaming NPC traders appear periodically in **Noodle Town**. Players must be at that location and click a **Trade** button on the announcement embed to open an ephemeral (private) buy menu. Stock is global — all players buy from the same pool and items can sell out.

---

## 1. Wandering Wok (Regular Trader)

**Theme:** A travelling noodle merchant with a cart full of scavenged goods. Friendly, haggling personality. Charges a premium because "you try pushing a cart through the Hollow."

### Timing
- **Frequency:** ~2 appearances per day (pure random)
- **Implementation:** Background task checks every 30 minutes with ~4.2% chance per check (~2/day average). Can be 0-4 on any given day.
- **Duration:** 10 minutes active window
- **Grace period:** Players who already opened a session get 3 extra minutes after the global timer expires

### Stock Rules
- **Global stock** — one roll per appearance, shared across all players
- **Per-player purchase cap:** 10 units per item per visit
- **Consumable qty cap:** 20 units per item (global)
- **Equipment qty cap:** 1 unit per item (global)
- **Pricing:** ~2x shop/craft cost markup on all items

### Item Pool

**High-availability items (75% chance to appear, 20 qty each):**
- Seaweed
- Bioluminescent Jelly
- Coral Golem

**Standard items (25% chance each to appear, 20 qty each):**
| Item | Category |
|------|----------|
| Noodle Gem | Mineral |
| Star Fragment | Mineral |
| Adamantium | Mineral |
| Titanium | Mineral |
| Dragonstone | Mineral |
| Emerald | Mineral |
| Mithril | Mineral |
| Coal | Mineral |
| Void Coral | Mineral |
| Golden Fish | Fish |
| River Dragon | Fish |
| Mermaid's Pearl | Fish |
| Generic fish (salmon, trout, etc.) | Fish |
| Generic farm items (wheat, corn, etc.) | Farm |

*(Fill remaining slots to reach ~20 items total from existing resource definitions)*

**T5 Equipment (5% chance per item to appear, 1 qty each, ~5x craft cost = 50-75k stars):**
- Noodle Gem Katana (weapon)
- Void Reaper (weapon)
- Eternity Bulwark (shield)
- Darkite Warplate (armor)

### Embed & UI
- **Color:** Warm orange/gold
- **Announcement:** Themed embed with flavor text, item preview, and a `🛒 Trade` button
- **Footer:** Shows countdown "Leaving in X minutes"
- **Ephemeral menu:** Player clicks Trade → gets a private dropdown or button menu to browse and buy
- **Sold out:** Players discover items are sold out when they attempt to buy (no live-updating embed)

---

## 2. Zyx the Collector (Alien Trader)

**Theme:** An alien from the same species as the abduction aliens, but this one is a rogue collector interested in commerce rather than kidnapping. Speaks in broken, ominous fragments. Extremely rare visitor.

### Timing
- **Frequency:** ~1 appearance per week (pure random)
- **Implementation:** Background task checks every hour with ~0.6% chance per check. Averages to ~1/week but could vary (twice in 3 days or once in 12 days).
- **Duration:** 2 minutes active window
- **Grace period:** Players who already opened a session get 3 extra minutes after the global timer expires
- **5-minute warning:** A mysterious/cryptic message posts 5 minutes before arrival: *"Strange signals detected... the air crackles with static... something approaches Noodle Town..."*

### Stock Rules
- **Global stock** — one roll per appearance, shared across all players
- **Per-player purchase cap:** 10 units per consumable, 1 per equipment
- **Equipment qty cap:** 1 unit per item (global)
- **Consumable qty cap:** 5 units per item (global, since window is so short)
- **Pricing:** ~5x craft cost markup on equipment. Extreme markup on rare effect items.

### Item Pool

**T6 Equipment (each has independent chance to appear, 1 qty, 5x craft cost):**
- Spiker (weapon)
- Plasma Pistol (weapon)
- Lunar Barrier (shield)
- Lunar Exosuit (armor)

**T7 Equipment (each has independent chance to appear, 1 qty, 5x craft cost):**
- Plasma Rifle (weapon)
- Plasma Repeater (weapon)
- Thermal Deflector (shield)
- Crimson Exoplate (armor)

**Rare Effect Items (each has independent chance to appear, 1 qty, extreme markup ~10x+ base):**
- Heart of Leviathan
- Lucky Charm
- Star Magnet
- Rune Fragment
- Fossilized Noodle
- Bucktail Jig

**Rare Consumables (chance to appear, 5 qty each, high markup):**
- Void Energy Flask
- Bank Insurance

### Embed & UI
- **Color:** Deep purple / alien green
- **Warning message:** Posted 5 minutes before. Cryptic, mysterious. No explicit mention of a trader.
- **Announcement:** Alien-themed embed with ominous flavor text and a `👽 Trade` button
- **Footer:** Shows countdown "Departing in X minutes"
- **Ephemeral menu:** Same pattern as regular trader — private dropdown/button menu on click
- **Urgency:** 2-minute window means players need to act fast

---

## 3. Architecture

### Location: `cogs/events/`
Both traders live in the events cog alongside alien abduction and farming weather.

**New files:**
- `cogs/events/roaming_trader.py` — Wandering Wok logic, constants, background task, views
- `cogs/events/alien_trader.py` — Zyx logic, constants, background task, views, warning system

### State: In-Memory Only
- Last appearance timestamps: module-level `datetime` vars
- Current stock: module-level dict (item_key → remaining qty)
- Per-player purchase tracking: module-level dict (user_id → {item_key: qty_bought})
- All state resets on bot restart (acceptable — traders are transient events)

### Channel Configuration
- **Admin command:** `!settrader #channel` — stores channel ID in DB
- **Stored in:** A simple key-value table or the existing bot config
- **Both traders use the same configured channel**

### Notification
- No @everyone / @here / role pings for either trader
- Just the announcement embed in the configured channel

### Access
- **Button only** — no `!trade` command. Players must see and click the announcement embed's Trade button.
- **Location gated** — player must be at Noodle Town to click Trade. Check `require_location` on interaction.

---

## 4. Trade Session Flow

```
1. Background task triggers → stock rolled → announcement embed posted
2. Player clicks [Trade] button on embed
3. Bot checks player is at Noodle Town
4. Bot sends ephemeral message with item list + Buy buttons/dropdown
5. Player selects item → bot checks: in stock? under per-player cap? enough stars?
6. Purchase processed → stars deducted, item added to inventory, global stock decremented
7. Ephemeral menu can be used repeatedly until dismissed or timer expires
8. When global timer expires: announcement embed updated ("The trader has left...")
9. Players with open sessions get 3-minute grace period before their menus disable
```

---

## 5. Constants Summary

| Parameter | Wandering Wok | Zyx the Collector |
|-----------|--------------|-------------------|
| Check interval | 30 min | 60 min |
| Trigger chance | ~4.2% per check | ~0.6% per check |
| Avg frequency | ~2/day | ~1/week |
| Active duration | 10 min | 2 min |
| Grace period | 3 min | 3 min |
| Warning | None | 5 min cryptic message |
| Consumable qty | 20 global | 5 global |
| Equipment qty | 1 global | 1 global |
| Per-player cap | 10 per item | 10 consumable, 1 equip |
| Markup (consumables) | ~2x | ~5-10x |
| Markup (equipment) | ~5x craft cost | ~5x craft cost |
| Location | Noodle Town | Noodle Town |
| Channel | Configured via !settrader | Same channel |

---

## 6. Names & Flavor

### Wandering Wok
- **Emoji:** 🍳
- **Greeting:** *"Psst... you look like someone who appreciates quality goods. Step closer, friend."*
- **Departure:** *"The Wandering Wok rolls onward... until next time!"*
- **Personality:** Warm, slightly shady, always has a deal

### Zyx the Collector
- **Emoji:** 👽
- **Warning message:** *"Strange signals detected... the air crackles with static... something approaches Noodle Town..."*
- **Greeting:** *"ZYX... HAS ARRIVED. TRADE... OR ZYX LEAVES. QUICKLY."*
- **Departure:** *"ZYX... DEPARTS. DO NOT... FOLLOW."*
- **Personality:** Terse, alien, intimidating, speaks in fragments. Same species as abduction aliens but a rogue merchant.

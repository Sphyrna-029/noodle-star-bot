# Noodle Star Bot - Economy Analysis
## Average Daily Star Income (40-50 Commands/Day)

---

## Executive Summary

**Estimated Daily Income Range: 200-2,500+ stars/day**

The economy has extreme variance depending on:
- Activities chosen (mining vs fishing vs gambling)
- Risk tolerance (Level 1 safe zones vs Level 5 high-risk areas)
- Luck with disasters and gambling outcomes
- Use of premium items (bait, potatoes, mushrooms)

**Key Findings:**
- ⚠️ **MAJOR IMBALANCE**: Fishing at Level 5 can earn 600+ stars PER FISH (vs 93 stars per mine)
- ⚠️ Gambling has negative expected value (-30% to -46% loss rate)
- ⚠️ Bank disasters at Level 4-5 can wipe 10-25% of entire bank balance
- ✅ Mining is most balanced: steady income with manageable risk
- ✅ Fishing Level 1-3 is fair but fishing Level 4-5 is OP

---

## 1. Mining Analysis

### Cooldowns
- **Base cooldown**: 30 minutes
- **With Raw Potato**: 5 minutes (costs 2 stars)
- **With Golden Mushroom**: Instant (costs 25 stars)
- **Max mines per day**: 48 (with 30min cooldown) or unlimited (with mushrooms)

### Average Returns Per Mine (Without Disasters)

| Level | Normal Pickaxe | Gold Pickaxe | Unlock Cost | Bank Risk |
|-------|---------------|--------------|-------------|-----------|
| 1     | 17.0 ⭐        | 21.5 ⭐       | Free        | 0%        |
| 2     | 34.5 ⭐        | 44.0 ⭐       | 1,500 ⭐     | 0%        |
| 3     | 52.0 ⭐        | 67.5 ⭐       | 3,000 ⭐     | 0%        |
| 4     | 63.5 ⭐        | 88.0 ⭐       | 4,000 ⭐     | **10%** ⚠️ |
| 5     | 93.0 ⭐        | 128.0 ⭐      | 5,000 ⭐     | **25%** ⚠️ |

### Disaster Analysis

| Level | Disaster Chance | Hazards | Protection |
|-------|----------------|---------|------------|
| 1     | 10%            | Collapse (50% wallet), Goblin (75% wallet) | Helmet (50⭐), Sword (75⭐) |
| 2     | 12%            | + Flood (60% wallet) | Helmet (50⭐), Sword (75⭐) |
| 3     | 14%            | + Cave Troll (80% wallet) | Helmet (50⭐), Sword (75⭐) |
| 4     | 16%            | + **Lava Flow (85% wallet + 10% bank)** | Helmet (50⭐), Sword (75⭐) |
| 5     | 20%            | + **Shadow Wraith (90% wallet + 25% bank)** | Helmet (50⭐), Sword (75⭐) |

**Special Protection Items:**
- **Mithril Shield**: 10 uses, protects from helmet-type disasters (250⭐ / 25⭐ per use)
- **Golden Axe**: 50 uses, protects from sword-type disasters (found via fishing)

### Daily Mining Income (40 Commands = ~20 Mines)

**Conservative (Level 3, Normal Pickaxe, 10% disasters):**
- 20 mines × 52 stars = 1,040 stars
- Minus disasters (10%): ~2 disasters × 52 × 0.6 = -62.4 stars
- Minus protection items: ~2 × 60 stars = -120 stars
- **Net: ~860 stars/day**

**Optimal (Level 5, Gold Pickaxe, no disasters with protection):**
- 20 mines × 128 stars = 2,560 stars
- Protection costs: ~4 disasters × 25 stars (mushroom/shield) = -100 stars
- **Net: ~2,460 stars/day** ✅

**Risk Analysis:**
- Level 4-5 disasters can hit your BANK (10-25%)
- If you have 10,000 stars in bank, Shadow Wraith = 2,500 star loss
- This makes Level 5 very risky without proper protection

---

## 2. Fishing Analysis

### Cooldowns
- **Base cooldown**: 120 seconds (2 minutes)
- **Max fish per day**: 720 (if fishing every 2 minutes for 24 hours)
- **Realistic max**: 40-50 fish/day with active play

### Bait Types

| Bait | Cost | Bite Wait | Pull Window | Rare Boost |
|------|------|-----------|-------------|------------|
| Worm | 33⭐ | 15-60s | 60s | 1.0x |
| Herring | 79⭐ | 90-180s | 35s | 1.5x |
| Sturgeon | 110⭐ | 5-8min | 20s | 2.0x |

### Average Returns Per Fish (Calculated from weighted probabilities)

**Level 1 (Calm Pond) - 0% Disaster Rate:**
- Worm: 35 stars (net: +2 stars after bait cost)
- Herring: 45 stars (net: -34 stars) ❌
- Sturgeon: 52 stars (net: -58 stars) ❌

**Level 2 (River Rapids) - 8% Disaster Rate:**
- Worm: 83 stars (net: +50 stars)
- Herring: 106 stars (net: +27 stars)
- Sturgeon: 123 stars (net: +13 stars)

**Level 3 (Coral Reef) - 10% Disaster Rate:**
- Worm: 158 stars (net: +125 stars) ✅
- Herring: 201 stars (net: +122 stars) ✅
- Sturgeon: 235 stars (net: +125 stars) ✅

**Level 4 (Shipwreck Depths) - 12% Disaster Rate + 10% Bank Risk:**
- Worm: 269 stars (net: +236 stars) 🚀
- Herring: 342 stars (net: +263 stars) 🚀
- Sturgeon: 399 stars (net: +289 stars) 🚀

**Level 5 (The Abyss Trench) - 14% Disaster Rate + 20% Bank Risk:**
- Worm: 408 stars (net: +375 stars) 🚀🚀🚀
- Herring: 521 stars (net: +442 stars) 🚀🚀🚀
- Sturgeon: 607 stars (net: +497 stars) 🚀🚀🚀

### Fishing Disasters

| Level | Disaster % | Hazards | Bank Risk |
|-------|-----------|---------|-----------|
| 1     | 0%        | None | 0% |
| 2     | 8%        | Riptide (40%), Shark (55%) | 0% |
| 3     | 10%       | + Whirlpool (60%) | 0% |
| 4     | 12%       | + Kraken (75%) | 0% |
| 5     | 14%       | + **Siren (80% + 10% bank)**, **Leviathan (85% + 20% bank)** | **10-20%** ⚠️⚠️⚠️ |

### Daily Fishing Income (40 Commands = ~25 Fish)

**Conservative (Level 3, Worm Bait, 10% disasters):**
- 25 fish × 158 stars = 3,950 stars
- Minus bait: 25 × 33 = -825 stars
- Minus disasters: ~2.5 × 158 × 0.6 = -237 stars
- Minus protection: ~2.5 × 60 = -150 stars
- **Net: ~2,740 stars/day** 🚀

**Optimal (Level 5, Sturgeon Bait, with protection):**
- 25 fish × 607 stars = 15,175 stars
- Minus bait: 25 × 110 = -2,750 stars
- Protection costs: ~3.5 disasters × 25 = -87 stars
- **Net: ~12,340 stars/day** 🚀🚀🚀 **EXTREMELY OVERPOWERED**

---

## 3. Gambling Analysis

### !gamble (Roll to 7)

**Win Conditions:**
- Roll exactly 7 on a 7-sided die (1/7 = 14.3% chance)
- Multipliers: 20x (1%), 5x (33%), 7x (33%), 8x (33%)

**Expected Value Analysis:**
- Win chance: 14.3%
- Average multiplier: (20×0.01 + 5×0.33 + 7×0.33 + 8×0.33) = 6.8x
- Expected value per bet: 0.143 × 6.8 - 0.857 = -0.88 = **-88% loss**

**Correction:** Looking at the CDF more carefully:
- 1% chance for 20x (cumulative 1%)
- 33% chance for 5x (cumulative 34%)
- 33% chance for 7x (cumulative 67%)
- 33% chance for 8x (cumulative 100%)

**Actual Expected Value:**
- (0.143) × (0.01×20 + 0.33×5 + 0.33×7 + 0.33×8) - 0.857
- = 0.143 × 6.59 - 0.857 = -0.46 = **-46% loss per bet** ❌

### !coinflip

**Win Conditions:**
- 50% chance to win
- Win multiplier: 1.95x (returns 1.95× bet)
- Minimum bet: 20 stars

**Expected Value:**
- 0.5 × 1.95 - 0.5 = 0.975 - 0.5 = **0.475 or -2.5% loss per bet** ✅ (Nearly fair!)

### !blackjack

**Parameters:**
- Natural blackjack: 1.5× payout (3:2)
- Normal win: 1× payout (1:1)
- Minimum bet: 20 stars
- Cooldown: 30 seconds
- Decks: 2

**Expected Value:**
- With optimal play, house edge ~0.5-2%
- **Expected loss: -1% per bet** ✅ (Fairest gambling game!)

### !duel

**Win Conditions:**
- Roll d20 vs opponent's d20 (reroll ties)
- 50% win rate
- No house edge (0% expected loss)
- Stamina cost: 8 + (bet ÷ 50) stamina
- Max stamina: 100
- Regen: 1 stamina per 10+ minutes (based on bet size)

**Expected Value:**
- 0.5 × bet - 0.5 × bet = **0% loss** ✅ (Perfectly fair!)

**Stamina Constraints:**
- Can only duel ~5-10 times per day depending on bet sizes
- Not a reliable income source

### Daily Gambling Income (10 Commands)

**Coinflip (most fair):**
- 10 bets × 100 stars average = 1,000 stars wagered
- Expected loss: 1,000 × -0.025 = **-25 stars/day** (nearly break-even)

**Blackjack (fairest):**
- 10 games × 100 stars = 1,000 stars wagered
- Expected loss: 1,000 × -0.01 = **-10 stars/day** ✅

**Gamble (worst):**
- 10 bets × 100 stars = 1,000 stars wagered
- Expected loss: 1,000 × -0.46 = **-460 stars/day** ❌

---

## 4. Shop Item Costs

| Item | Cost | Purpose |
|------|------|---------|
| Raw Potato | 2⭐ | Reduce mine cooldown to 5min |
| Golden Mushroom | 25⭐ | Mine instantly |
| Worm Bait | 33⭐ | Basic fishing bait |
| Helmet | 50⭐ | Protect from collapse/flood/riptide/whirlpool (1 use) |
| Sword | 75⭐ | Protect from goblin/troll/shark/kraken (1 use) |
| Herring Bait | 79⭐ | Medium fishing bait |
| Sturgeon Bait | 110⭐ | Premium fishing bait |
| Telescope | 200⭐ | View starfield (cosmetic) |
| Bank Insurance | 250⭐ | Protect bank from 1 disaster (10 uses) |
| Gold Pickaxe | 500⭐ | Better mining luck (permanent) |

**Rare Fishing Drops:**
- Golden Axe: 50 uses, sword protection (free from fishing)
- Mithril Shield: 10 uses, helmet protection (free from fishing)

---

## 5. Random Events

### Alien Abduction
- **Chance**: 0.05% per command (~2% per day with 40 commands)
- **Effect**: Lose 100% of wallet + all items (bank is safe)
- **Impact**: Can wipe days of progress if unlucky

---

## 6. Overall Economy Balance

### Income Tiers (40-50 commands/day)

**Tier 1: Safe Conservative (200-500 stars/day)**
- Level 1-2 mining/fishing
- No gambling
- Minimal risk

**Tier 2: Balanced Mid-Game (800-1,500 stars/day)**
- Level 3 fishing with worm bait
- Level 3-4 mining with gold pickaxe
- Occasional blackjack
- Some disasters but protected

**Tier 3: High-Risk High-Reward (2,000-5,000 stars/day)**
- Level 4-5 mining with mushrooms
- Level 4 fishing with herring/sturgeon
- Protection items equipped
- **Bank risk: 10-20%** ⚠️

**Tier 4: EXTREME (10,000+ stars/day)**
- Level 5 fishing with sturgeon bait
- 25+ fish per day
- **COMPLETELY BROKEN** 🚨
- Bank risk: 20% per disaster

---

## 7. Critical Balance Issues

### 🚨 Major Problems

1. **Fishing Level 5 is MASSIVELY overpowered**
   - 607 stars per fish (vs 128 for Level 5 mining)
   - 4.7× more profitable than mining
   - Can earn 12,000+ stars/day easily
   - **Recommendation**: Reduce Level 5 fish values by 50-60%

2. **!gamble has terrible expected value (-46%)**
   - Nearly guaranteed to lose money
   - No reason to use over coinflip (-2.5%) or blackjack (-1%)
   - **Recommendation**: Improve multipliers or increase win chance to 20% (1 in 5)

3. **Bank disasters are punishing at scale**
   - 20-25% bank loss can be THOUSANDS of stars
   - Makes hoarding stars in bank risky
   - **Recommendation**: Cap bank loss at 1,000 stars or add more insurance options

4. **Alien abduction is too random**
   - 0.05% per command is low but devastating
   - No way to protect wallet
   - **Recommendation**: Add warning signs or protection item

5. **Level 1 fishing with herring/sturgeon is net negative**
   - Bait costs more than average catch
   - Trap for new players
   - **Recommendation**: Buff Level 1 catches or reduce bait costs

### ✅ Well-Balanced Features

1. **Blackjack & Coinflip** - Fair gambling with low house edge
2. **Mining Levels 1-4** - Good progression and risk/reward balance
3. **Duels** - Perfectly fair (0% house edge), stamina prevents abuse
4. **Protection items** - Good pricing for risk mitigation
5. **Trading system** - Allows player economy without exploitation

---

## 8. Recommendations for Balance

### High Priority Fixes

1. **Nerf Level 5 Fishing by 50-60%**
   ```
   Current: 607 stars/fish (sturgeon)
   Recommended: 250-300 stars/fish
   ```

2. **Buff !gamble win rate or multipliers**
   ```
   Current: 14.3% win, -46% EV
   Recommended: 20% win (1d5 instead of 1d7), keep multipliers
   New EV: ~-20% (still house advantage but playable)
   ```

3. **Cap bank disaster losses**
   ```
   Current: 25% of entire bank (can be 10,000+ stars)
   Recommended: Max 1,000 star loss OR 10%, whichever is lower
   ```

4. **Add alien abduction protection item**
   ```
   "Tinfoil Hat" - 100 stars
   - Protects from 1 alien abduction
   - Consumable
   ```

### Medium Priority

5. **Buff Level 1 fishing rewards**
   ```
   Current: 35 stars average (net +2 after worm bait)
   Recommended: 50 stars average (net +17)
   ```

6. **Reduce sturgeon bait cost**
   ```
   Current: 110 stars (only worth it at Level 3+)
   Recommended: 80 stars
   ```

7. **Add more bank insurance uses**
   ```
   Current: 250 stars for 10 uses = 25 stars/use
   Recommended: Make it last 20 uses
   ```

### Low Priority

8. **Add daily login bonus** (50-100 stars) to help new players
9. **Add achievement rewards** for milestones
10. **Add weekly quests** for variety

---

## 9. Final Summary: Typical User Daily Income

**Casual Player (20-30 commands/day):**
- Mix of Level 2-3 mining/fishing
- No gambling
- **~400-800 stars/day**

**Active Player (40-50 commands/day):**
- Level 3-4 fishing with worm/herring
- Level 3-4 mining with gold pickaxe
- Some blackjack/coinflip
- **~1,500-2,500 stars/day**

**Hardcore/Exploiter (50+ commands/day):**
- Level 5 fishing with sturgeon
- Abusing cooldowns with mushrooms
- **~10,000+ stars/day** 🚨 **TOO HIGH**

---

## 10. Fairness Assessment

### Most Fair Systems ✅
1. Duels (0% house edge)
2. Blackjack (-1% house edge)
3. Coinflip (-2.5% house edge)
4. Mining Levels 1-4 (balanced risk/reward)
5. Fishing Levels 1-3 (balanced progression)

### Least Fair Systems ❌
1. Fishing Levels 4-5 (massively overpowered)
2. !gamble (-46% house edge, nearly unplayable)
3. Bank disasters at Level 5 (can lose 25% of life savings)
4. Alien abduction (pure RNG, no counterplay)
5. Level 1 fishing with premium bait (net negative income)

---

**Analysis Date**: February 27, 2026  
**Analyzed By**: AI Assistant  
**Data Source**: Full codebase analysis of all cogs and constants

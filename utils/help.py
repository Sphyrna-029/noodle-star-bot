"""Interactive button-based help command for Noodle Star Bot.

Main !help shows a welcome screen with clickable category buttons.
Each category opens a detailed, beginner-friendly sub-page.
!help <command> and !help <category> still work as text lookups.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import discord
from discord.ext import commands

# ---------------------------------------------------------------------------
# Embed builders — one per category, written for non-tech-savvy users
# ---------------------------------------------------------------------------

def _main_embed() -> discord.Embed:
    embed = discord.Embed(
        title="✨ Noodle Star Bot — Help Menu",
        description=(
            "Welcome to the **Noodle House**!\n\n"
            "**Not sure where to start?** Here's the basics:\n"
            "1. Type `!mine` to earn your first stars\n"
            "2. Type `!stars` to check how many you have\n"
            "3. Type `!store` to see what you can buy\n"
            "4. Type `!deposit all` to keep your stars safe in the bank\n\n"
            "**Click a button below** to learn about each feature, "
            "or type `!help <command>` for info on a specific command."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="⛏️ Mining",
        value="Dig for minerals to earn stars",
        inline=True,
    )
    embed.add_field(
        name="🎣 Fishing",
        value="Cast your line, catch fish & treasure",
        inline=True,
    )
    embed.add_field(
        name="🌾 Farming",
        value="Plant crops, wait, harvest for profit",
        inline=True,
    )
    embed.add_field(
        name="🐾 Pets",
        value="Adopt and care for companions",
        inline=True,
    )
    embed.add_field(
        name="💰 Economy",
        value="Check stars, bank, leaderboards",
        inline=True,
    )
    embed.add_field(
        name="🎲 Gambling",
        value="Coinflip, blackjack, duels & more",
        inline=True,
    )
    embed.add_field(
        name="🛒 Shop & Trading",
        value="Buy items, trade with other players",
        inline=True,
    )
    embed.add_field(
        name="🚀 Space Mining",
        value="Launch into space, mine 5 planets",
        inline=True,
    )
    embed.add_field(
        name="🧰 Treasure Hunt",
        value="Lock-pick chests for star rewards",
        inline=True,
    )
    embed.add_field(
        name="🎒 Items",
        value="Rare items, effects & how to get them",
        inline=True,
    )
    embed.set_footer(text="Buttons expire after 3 minutes. Type !help anytime to reopen.")
    return embed


def _mining_embed() -> discord.Embed:
    embed = discord.Embed(
        title="⛏️ Mining — How It Works",
        description=(
            "Mining is the easiest way to earn stars. "
            "You dig into a mine and find a random mineral worth stars."
        ),
        color=discord.Color.dark_gold(),
    )
    embed.add_field(
        name="Getting Started (step by step)",
        value=(
            "**Step 1:** Type `!mine` — you'll find a mineral and earn stars\n"
            "**Step 2:** Wait 30 minutes, then `!mine` again\n"
            "**Step 3:** When you have 500+ stars, buy a Gold Pickaxe from `!store`\n"
            "**Step 4:** Unlock deeper mines with `!unlock 2` for better loot"
        ),
        inline=False,
    )
    embed.add_field(
        name="All Mining Commands",
        value=(
            "`!mine` — Dig for minerals (30 min cooldown)\n"
            "`!mine potato` — Mine after only 5 min (costs 1 Raw Potato)\n"
            "`!mine mushroom` — Mine right now, no waiting (uses 1 Golden Mushroom from farming harvests)\n"
            "`!minelevel` — See what mine levels you've unlocked\n"
            "`!minelevel 2` — Switch to a different mine level\n"
            "`!unlock 2` — Pay to unlock the next mine level"
        ),
        inline=False,
    )
    embed.add_field(
        name="The 5 Mine Levels",
        value=(
            "⛏️ **Lv1 Surface Mine** — Free! 10% disaster chance\n"
            "🕳️ **Lv2 Caverns** — Costs 1,500 stars to unlock, 12% disaster\n"
            "🪨 **Lv3 Deep Tunnels** — Costs 3,000 stars, 14% disaster\n"
            "🌋 **Lv4 Molten Core** — Costs 4,000 stars, 16% disaster, **can lose bank stars!**\n"
            "🌑 **Lv5 The Abyss** — Costs 5,000 stars, 20% disaster, **can lose bank stars!**\n\n"
            "You must unlock levels in order (1 → 2 → 3 → 4 → 5)."
        ),
        inline=False,
    )
    embed.add_field(
        name="What Are Disasters?",
        value=(
            "After you mine, there's a chance something bad happens:\n"
            "💥 **Collapse** / 🌊 **Flood** — Blocked by a Helmet (50 stars)\n"
            "👹 **Goblin** / 🧌 **Troll** — Blocked by a Sword (75 stars)\n\n"
            "**If you DON'T have protection:** You lose a chunk of your stars "
            "AND all your items get destroyed.\n"
            "**If you DO have protection:** The item breaks but you keep everything else.\n\n"
            "**Always buy a Helmet AND Sword before mining Level 2+!**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Pro Tips",
        value=(
            "• The Gold Pickaxe (500 stars, one-time buy) makes rare minerals appear more often\n"
            "• Raw Potatoes are only 2 stars — great for mining more often on a budget\n"
            "• At Lv4-5, buy Bank Insurance (250 stars) to protect your bank\n"
            "• `!deposit all` your stars before risky mines!"
        ),
        inline=False,
    )
    return embed


def _fishing_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎣 Fishing — How It Works",
        description=(
            "Fishing is a two-step minigame: you cast your line, wait for a tug, "
            "then pull it in before time runs out."
        ),
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="Getting Started (step by step)",
        value=(
            "**Step 1:** Buy worm bait from `!store` (33 stars each)\n"
            "**Step 2:** Type `!fish` to cast your line\n"
            "**Step 3:** **Wait!** The bot will tell you when a fish bites\n"
            "**Step 4:** When you see **\"You feel a tug!\"**, quickly type `!pull`\n"
            "**Step 5:** You catch a fish and earn stars! (2 min cooldown after)"
        ),
        inline=False,
    )
    embed.add_field(
        name="All Fishing Commands",
        value=(
            "`!fish` — Cast your line (uses your equipped bait)\n"
            "`!fish herring` — Switch bait and cast in one command\n"
            "`!pull` — Reel in when you see \"You feel a tug!\"\n"
            "`!fishing` — Check if you're currently fishing / on cooldown\n"
            "`!use bait worm` — Equip a bait type without casting\n"
            "`!baitshop` — Compare all bait types\n"
            "`!fishlevel` — See your fishing levels\n"
            "`!fishlevel 2` — Switch to a different fishing area"
        ),
        inline=False,
    )
    embed.add_field(
        name="Bait Comparison",
        value=(
            "🪱 **Worm** (33 stars) — Bites in 15-60 sec, 60 sec to pull — **Best for beginners**\n"
            "🐟 **Herring** (79 stars) — Bites in 90-180 sec, 35 sec to pull — 2x better catches\n"
            "🐋 **Sturgeon** (110 stars) — Bites in 5-8 min, only 20 sec to pull — 10x better catches\n\n"
            "**Higher tier bait** = longer wait but WAY better fish.\n"
            "**Be careful with Sturgeon** — you only get 20 seconds to type `!pull`!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Fishing Levels",
        value=(
            "🎣 **Lv1 Calm Pond** — Safe, no dangers\n"
            "🏞️ **Lv2 River Rapids** — 8% disaster, better catches\n"
            "🪸 **Lv3 Coral Reef** — 10% disaster, even better catches\n"
            "🚢 **Lv4 Shipwreck Depths** — 12% disaster, **can lose bank stars!**\n"
            "🌊 **Lv5 The Abyss Trench** — 14% disaster, **can lose bank stars!**\n\n"
            "Fishing levels unlock through mining (`!unlock`)."
        ),
        inline=False,
    )
    embed.add_field(
        name="Common Mistakes",
        value=(
            "**Pulling too early** — If you type `!pull` before the fish bites, "
            "you lose your bait and get a cooldown.\n"
            "**Pulling too late** — If you don't `!pull` in time, the fish escapes "
            "and your bait is wasted.\n"
            "**No bait equipped** — You need bait to fish! Buy some from `!store`."
        ),
        inline=False,
    )
    return embed


def _farming_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🌾 Farming — How It Works",
        description=(
            "Farming is the safest way to earn stars. "
            "Plant crops, wait for them to grow, and harvest for profit. "
            "No cooldowns, but soil quality now matters."
        ),
        color=discord.Color.green(),
    )
    embed.add_field(
        name="Getting Started (step by step)",
        value=(
            "**Step 1:** Type `!buyplot` to see plot prices\n"
            "**Step 2:** Type `!buyplot 1` to buy your first plot (300 stars)\n"
            "**Step 3:** Type `!plant wheat 1` to plant wheat in plot 1\n"
            "**Step 4:** Wait 1 hour (check progress with `!farm`)\n"
            "**Step 5:** Type `!harvest` to collect your stars\n"
            "**Step 6:** Use `!tend <plot> <fertilizer|water>` when soil gets low"
        ),
        inline=False,
    )
    embed.add_field(
        name="All Farming Commands",
        value=(
            "`!farm` — See your farm (what's planted, growth timers)\n"
            "`!farmlevel` — Check your farm level and next upgrade cost\n"
            "`!upgradefarm` — Upgrade farm level (improves harvest quality odds)\n"
            "`!buyplot` — See all plots and prices\n"
            "`!buyplot 1` — Buy a specific plot\n"
            "`!plant wheat 1` — Plant a crop in a plot\n"
            "`!harvest` — Harvest ALL ready crops at once\n"
            "`!harvest 1` — Harvest just one plot\n"
            "`!tend 1 fertilizer` — Restore soil on a plot using a tending item\n"
            "`!crops` — See all available crops and stats"
        ),
        inline=False,
    )
    embed.add_field(
        name="Crops — What to Plant",
        value=(
            "🌾 **Wheat** — Pay 15, get 40 back (1 hour) — *Check every hour*\n"
            "🥕 **Carrot** — Pay 30, get 90 back (2 hours) — *Check every few hours*\n"
            "🌽 **Corn** — Pay 60, get 200 back (4 hours) — *Check 2-3x a day*\n"
            "🍅 **Tomato** — Pay 120, get 440 back (8 hours) — *Plant before bed/work*\n"
            "🍉 **Melon** — Pay 240, get 960 back (16 hours) — *Check once a day*\n"
            "🍄 **Mushroom** — Pay 300, harvest in 24 hours for 5 Golden Mushrooms\n\n"
            "**Longer crops = more profit per hour.** "
            "Pick based on how often you check Discord!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Plot Prices (one-time purchase)",
        value=(
            "Plot 1: 300 • Plot 2: 400 • Plot 3: 500\n"
            "Plot 4: 600 • Plot 5: 700 • Plot 6: 800\n"
            "Must buy in order. Max 6 plots total."
        ),
        inline=False,
    )
    embed.add_field(
        name="Soil & Plot Fatigue",
        value=(
            "• Each plot has soil condition shown in `!farm`\n"
            "• Repeatedly planting the same crop in one plot increases soil drain\n"
            "• Lower soil condition reduces harvest value and worsens quality odds\n"
            "• Use `!tend <plot> fertilizer` (+25 soil) or `!tend <plot> water` (+10 soil)\n"
            "• Buy tending items in `!store` (Farming category)"
        ),
        inline=False,
    )
    embed.add_field(
        name="Good to Know",
        value=(
            "• Farm level now goes up to 10, and bad quality is always possible\n"
            "• Harvest value swings with quality, weather events, and soil condition\n"
            "• Replanting the same crop repeatedly on one plot drains soil faster\n"
            "• Buy 🧪 Fertilizer and 💧 Water from `!store` to tend plots\n"
            "• No cooldowns — plant and harvest as often as your crops are ready\n"
            "• 🍄 Mushroom crops are the source of Golden Mushrooms for instant mining\n"
            "• Hidden daily weather events can buff or nerf harvest value\n"
            "• A plot must be empty to plant in it (harvest first)"
        ),
        inline=False,
    )
    return embed


def _pets_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🐾 Pets — How It Works",
        description=(
            "Pets are Tamagotchi-style companions with no neglect penalties. "
            "Care actions improve mood and expression."
        ),
        color=discord.Color.orange(),
    )
    embed.add_field(
        name="Getting Started (step by step)",
        value=(
            "**Step 1:** Open `!store` and go to the **Pets** category\n"
            "**Step 2:** Buy a pet with `!buy <pet>` (example: `!buy cat`)\n"
            "**Step 3:** Check your active pet with `!pet`\n"
            "**Step 4:** Keep mood up with `!pet feed`, `!pet clean`, `!pet play`"
        ),
        inline=False,
    )
    embed.add_field(
        name="All Pet Commands",
        value=(
            "`!pet` — View your active pet\n"
            "`!pet @user` — View someone else's active pet\n"
            "`!pet all` — View all owned pets with full stats\n"
            "`!pet select <pet>` — Set active pet\n"
            "`!pet name <pet> <nickname>` — Name one owned pet\n"
            "`!pet rename <nickname>` — Rename active pet\n"
            "`!pet feed` — Increase hunger stat\n"
            "`!pet clean` — Increase cleanliness stat\n"
            "`!pet play` — Increase happiness stat"
        ),
        inline=False,
    )
    embed.add_field(
        name="Mood & Sprites",
        value=(
            "Mood is based on hunger, cleanliness, and happiness:\n"
            "• **Happy** — high average care\n"
            "• **Idle** — medium average care\n"
            "• **Sad** — low average care\n\n"
            "Your pet expression image updates based on this mood state."
        ),
        inline=False,
    )
    embed.add_field(
        name="Important Rules",
        value=(
            "• No punishments for inactivity (no death, no hard penalties)\n"
            "• You can own multiple pets and switch the active one\n"
            "• Pets are bought through `!store`/`!buy`, not a separate pet shop"
        ),
        inline=False,
    )
    return embed


def _economy_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💰 Economy — How It Works",
        description=(
            "Everything in Noodle House runs on **noodle stars**. "
            "Earn them, save them, spend them!"
        ),
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="Checking Your Balance",
        value=(
            "`!stars` — See your wallet + bank balance\n"
            "`!stars @someone` — Check another player's balance\n"
            "`!profile` / `!achievements` — View your user profile + achievements\n"
            "`!topstars` — See the top 10 richest players\n"
            "`!bottomstars` — See the bottom 5 players\n"
            "`!starstats` — See monthly economy statistics"
        ),
        inline=False,
    )
    embed.add_field(
        name="Banking (Keep Your Stars Safe!)",
        value=(
            "`!deposit 100` — Move 100 stars to your bank\n"
            "`!deposit all` — Move everything to your bank\n"
            "`!withdraw 50` — Take 50 stars from your bank\n"
            "`!withdraw all` — Take everything out\n\n"
            "**Deposit cooldown:** 60 minutes\n"
            "**Withdraw cooldown:** 15 minutes"
        ),
        inline=False,
    )
    embed.add_field(
        name="Wallet vs Bank — What's the Difference?",
        value=(
            "💰 **Wallet** — This is your \"cash on hand\". Used for buying, "
            "gambling, and earning. **Can be lost** from mining disasters, "
            "fishing hazards, and alien abductions!\n\n"
            "🏦 **Bank** — This is your safe storage. Protected from almost everything. "
            "Only Lv4-5 mining/fishing disasters can touch it, "
            "and you can buy Bank Insurance to prevent even that.\n\n"
            "**Rule of thumb:** Always `!deposit all` after earning stars!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Watch Out!",
        value=(
            "👽 **Alien Abductions** — 0.5% chance on any command to lose ALL "
            "your wallet stars and items. Your bank is always safe though!\n"
            "**This is why you should deposit often.**"
        ),
        inline=False,
    )
    return embed


def _gambling_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎲 Gambling — How It Works",
        description=(
            "Risk your stars for a chance at big payouts. "
            "Each game has different odds — some are fair, some are not!"
        ),
        color=discord.Color.red(),
    )
    embed.add_field(
        name="The Games",
        value=(
            "**🪙 Coinflip** — `!coinflip 50 heads`\n"
            "50/50 chance, pays 1.95x. Min bet: 20 stars.\n\n"
            "**🃏 Blackjack** — `!blackjack 50` (or `!bj 50`)\n"
            "Play cards vs the dealer. Use the Hit/Stand buttons. "
            "Natural 21 pays 1.5x. Min bet: 20 stars. 30 sec cooldown.\n\n"
            "**⚔️ Duel** — `!duel @player 50`\n"
            "Both roll a d20, higher roll wins. Completely fair (50/50). "
            "Costs stamina.\n\n"
            "**🔫 Russian Roulette** — `!russian @player 100` (or `!rr`)\n"
            "PvP only: challenge another player, they accept, then each turn pick a chamber with "
            "`!russian fire <1-6>`. You have **1 hour** per turn or you forfeit.\n\n"
            "**🎲 Gamble** — `!gamble 50`\n"
            "Roll a d7, win only on 7 (14% chance). Can pay up to 20x. "
            "**Very risky!**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Which Game Should I Play?",
        value=(
            "⚔️ **Duel** — Fairest game (0% house edge), but costs stamina\n"
            "🃏 **Blackjack** — Almost fair (~1% house edge), fun card game\n"
            "🪙 **Coinflip** — Simple and quick (2.5% house edge)\n"
            "🎲 **Gamble** — You'll probably lose (46% house edge) but jackpots are huge\n\n"
            "**If you want to make money:** Duel or Blackjack\n"
            "**If you want excitement:** Gamble (but expect to lose!)"
        ),
        inline=False,
    )
    embed.add_field(
        name="Duel Stamina Explained",
        value=(
            "Duels cost stamina so you can't spam them.\n"
            "• You have **100 stamina**, resets daily\n"
            "• Small bets cost ~10 stamina, big bets cost more\n"
            "• Stamina regenerates slowly over time\n"
            "• Check your stamina when you `!duel`"
        ),
        inline=False,
    )
    return embed


def _shop_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🛒 Shop & Trading — How It Works",
        description=(
            "Buy items to help with mining and fishing, "
            "or trade with other players."
        ),
        color=discord.Color.purple(),
    )
    embed.add_field(
        name="Shop Commands",
        value=(
            "`!store` — See all items and prices\n"
            "`!buy helmet` — Buy an item\n"
            "`!buy cat` — Buy a pet from the Pets category\n"
            "`!buy worm 5` — Buy 5 of something\n"
            "`!inventory` — See what you own\n"
            "`!inventory @someone` — See what someone else owns"
        ),
        inline=False,
    )
    embed.add_field(
        name="What Should I Buy First?",
        value=(
            "1. 🪖 **Helmet** (50 stars) + ⚔️ **Sword** (75 stars) — "
            "Buy these BEFORE mining Lv2+. They save you from disasters.\n"
            "2. 🪱 **Worm Bait** (33 stars) — Needed to fish at all.\n"
            "3. ⛏️ **Gold Pickaxe** (500 stars) — One-time buy, "
            "permanently boosts mining luck.\n"
            "4. 🥔 **Raw Potato** (2 stars) — Cheapest way to mine more often.\n"
            "5. 💸 **Bank Insurance** (250 stars) — Must-have for Lv4-5 "
            "mining/fishing."
        ),
        inline=False,
    )
    embed.add_field(
        name="Quick Item Reference",
        value=(
            "🪖 Helmet (50) — Blocks 1 collapse/flood disaster\n"
            "⚔️ Sword (75) — Blocks 1 goblin/troll disaster\n"
            "🥔 Raw Potato (2) — Mine after 5 min instead of 30\n"
            "🍄 Golden Mushroom (farm harvest) — Mine instantly, skip cooldown\n"
            "💸 Bank Insurance (250) — Protects your bank from 1 disaster\n"
            "📷 Telescope (200) — View a starfield (permanent, fun item)\n"
            "🪱 Worm (33) / 🐟 Herring (79) / 🐋 Sturgeon (110) — Fishing bait\n"
            "🐾 Pets — Companion category in `!store` (buy with `!buy <pet>`)"
        ),
        inline=False,
    )
    embed.add_field(
        name="Trading With Other Players",
        value=(
            "`!trade @Bob 100 stars for 2 helmet` — Propose a 2-way trade\n"
            "`!trade @Bob 50 stars` — Send a gift (they still have to accept)\n"
            "`!trade accept` — Accept a trade someone sent you\n"
            "`!trade cancel` — Cancel a trade\n\n"
            "**How it works:**\n"
            "1. You propose → they get 60 seconds to accept\n"
            "2. After accepting → 10 second safety countdown\n"
            "3. Either side can cancel before it goes through"
        ),
        inline=False,
    )
    return embed


def _treasure_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🧰 Treasure Hunt — How It Works",
        description=(
            "Treasure Hunt is a lock-picking event. "
            "A chest appears, one player claims the lock, and tries to crack the combo."
        ),
        color=discord.Color.teal(),
    )
    embed.add_field(
        name="Core Commands",
        value=(
            "`!chest status` — Check if a chest is active\n"
            "`!pick start` — Claim the lock and begin\n"
            "`!pick 1 3 2` / `!pick 1 3 2 4` — Submit a guess\n"
            "`!pick status` — Check chest lock status"
        ),
        inline=False,
    )
    embed.add_field(
        name="How Lock-Picking Works",
        value=(
            "• Standard chests use **3 pins** (1-4 each)\n"
            "• Item-capable chests use **4 pins** and can drop extra loot\n"
            "• You get **5 attempts** per lock session\n"
            "• Feedback shows exact matches and misplaced matches\n"
            "• If you solve it, you win a random star reward"
        ),
        inline=False,
    )
    embed.add_field(
        name="Important Rules",
        value=(
            "• While you hold the lock, others must wait\n"
            "• You have about **60 seconds** before lock ownership resets\n"
            "• If no one opens the chest within **1 hour**, it expires"
        ),
        inline=False,
    )

    return embed


def _space_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🚀 Space Mining — How It Works",
        description=(
            "Space mining is the endgame! After reaching mine level 5, "
            "buy a Rocket Ship and blast off to mine on 5 planets with "
            "bigger rewards and deadlier hazards."
        ),
        color=discord.Color.dark_blue(),
    )
    embed.add_field(
        name="Getting Started (step by step)",
        value=(
            "**Step 1:** Reach mine level 5 (`!unlock 5`)\n"
            "**Step 2:** Buy a Rocket Ship from `!store` (10,000 stars)\n"
            "**Step 3:** Type `!launch` to blast off into space\n"
            "**Step 4:** Type `!spacemine` to mine on the Moon\n"
            "**Step 5:** Earn stars and unlock more planets with `!unlockplanet`"
        ),
        inline=False,
    )
    embed.add_field(
        name="All Space Commands",
        value=(
            "`!launch` — Blast off into space (one-time, requires Rocket Ship + mine Lv5)\n"
            "`!spacemine` — Mine on your active planet (shares mining cooldown)\n"
            "`!spacemine potato` — Mine with reduced cooldown (uses 1 Raw Potato)\n"
            "`!spacemine mushroom` — Mine instantly (uses 1 Golden Mushroom)\n"
            "`!planets` — View all planets and your active planet\n"
            "`!planets 3` — Switch to a different planet\n"
            "`!unlockplanet 2` — Pay to unlock the next planet"
        ),
        inline=False,
    )
    embed.add_field(
        name="The 5 Planets",
        value=(
            "🌕 **Planet 1 — The Moon** — Free! 12% disaster chance\n"
            "🔴 **Planet 2 — Mars** — 5,000 stars, 14% disaster\n"
            "🪐 **Planet 3 — Saturn** — 10,000 stars, 16% disaster, **bank risk!**\n"
            "💠 **Planet 4 — Uranus** — 15,000 stars, 18% disaster, **bank risk!**\n"
            "🥶 **Planet 5 — Pluto** — 20,000 stars, 22% disaster, **bank risk!**\n\n"
            "Planets must be unlocked in order (1 → 2 → 3 → 4 → 5)."
        ),
        inline=False,
    )
    embed.add_field(
        name="Space Hazards",
        value=(
            "☄️ **Meteor Strike** — Blocked by Helmet (50% wallet loss)\n"
            "🏴‍☠️ **Space Pirate** — Blocked by Sword (75% wallet loss)\n"
            "☀️ **Solar Flare** (P3+) — Blocked by Helmet (85% wallet + 10% bank)\n"
            "🕳️ **Black Hole Rift** (P3+) — Blocked by Sword (85% wallet + 15% bank)\n"
            "👁️ **Void Entity** (P5 only) — Blocked by Sword (90% wallet + 30% bank)\n\n"
            "**Helmets and swords have a HIGH failure chance in space!**\n"
            "Golden Axe and Mithril Shield never fail — they're essential here."
        ),
        inline=False,
    )
    embed.add_field(
        name="Pro Tips",
        value=(
            "• `!deposit all` before space mining — the hazards are brutal\n"
            "• Buy Bank Insurance for planets 3+ to protect your bank\n"
            "• Space mining shares the same cooldown as regular mining\n"
            "• Higher planets = better ores but much more dangerous\n"
            "• Protection failure chance goes up to 50% on Pluto!"
        ),
        inline=False,
    )
    return embed


def _space_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🚀 Space Mining — How It Works",
        description=(
            "Space mining is the endgame! After reaching mine level 5, "
            "buy a Rocket Ship and blast off to mine on 5 planets with "
            "bigger rewards and deadlier hazards."
        ),
        color=discord.Color.dark_blue(),
    )
    embed.add_field(
        name="Getting Started (step by step)",
        value=(
            "**Step 1:** Reach mine level 5 (`!unlock 5`)\n"
            "**Step 2:** Buy a Rocket Ship from `!store` (10,000 stars)\n"
            "**Step 3:** Type `!launch` to blast off into space\n"
            "**Step 4:** Type `!spacemine` to mine on the Moon\n"
            "**Step 5:** Earn stars and unlock more planets with `!unlockplanet`"
        ),
        inline=False,
    )
    embed.add_field(
        name="All Space Commands",
        value=(
            "`!launch` — Blast off into space (one-time, requires Rocket Ship + mine Lv5)\n"
            "`!spacemine` — Mine on your active planet (shares mining cooldown)\n"
            "`!spacemine potato` — Mine with reduced cooldown (uses 1 Raw Potato)\n"
            "`!spacemine mushroom` — Mine instantly (uses 1 Golden Mushroom)\n"
            "`!planets` — View all planets and your active planet\n"
            "`!planets 3` — Switch to a different planet\n"
            "`!unlockplanet 2` — Pay to unlock the next planet"
        ),
        inline=False,
    )
    embed.add_field(
        name="The 5 Planets",
        value=(
            "🌕 **Planet 1 — The Moon** — Free! 12% disaster chance\n"
            "🔴 **Planet 2 — Mars** — 5,000 stars, 14% disaster\n"
            "🪐 **Planet 3 — Saturn** — 10,000 stars, 16% disaster, **bank risk!**\n"
            "💠 **Planet 4 — Uranus** — 15,000 stars, 18% disaster, **bank risk!**\n"
            "🥶 **Planet 5 — Pluto** — 20,000 stars, 22% disaster, **bank risk!**\n\n"
            "Planets must be unlocked in order (1 → 2 → 3 → 4 → 5)."
        ),
        inline=False,
    )
    embed.add_field(
        name="Space Hazards",
        value=(
            "☄️ **Meteor Strike** — Blocked by Helmet (50% wallet loss)\n"
            "🏴‍☠️ **Space Pirate** — Blocked by Sword (75% wallet loss)\n"
            "☀️ **Solar Flare** (P3+) — Blocked by Helmet (85% wallet + 10% bank)\n"
            "🕳️ **Black Hole Rift** (P3+) — Blocked by Sword (85% wallet + 15% bank)\n"
            "👁️ **Void Entity** (P5 only) — Blocked by Sword (90% wallet + 30% bank)\n\n"
            "**Helmets and swords have a HIGH failure chance in space!**\n"
            "Golden Axe and Mithril Shield never fail — they're essential here."
        ),
        inline=False,
    )
    embed.add_field(
        name="Pro Tips",
        value=(
            "• `!deposit all` before space mining — the hazards are brutal\n"
            "• Buy Bank Insurance for planets 3+ to protect your bank\n"
            "• Space mining shares the same cooldown as regular mining\n"
            "• Higher planets = better ores but much more dangerous\n"
            "• Protection failure chance goes up to 50% on Pluto!"
        ),
        inline=False,
    )
    return embed


def _items_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎒 Items — Rare Effects & How to Get Them",
        description=(
            "Beyond the basic shop gear, rare items can drop from mining and fishing. "
            "These powerful effects can turn the tide in your favor!"
        ),
        color=discord.Color.dark_purple(),
    )
    embed.add_field(
        name="🛡️ Protection Items (from Shop)",
        value=(
            "🪖 **Helmet** (50 stars) — Blocks 1 collapse/flood/meteor disaster. "
            "Consumed on use. Can fail at higher levels!\n"
            "⚔️ **Sword** (75 stars) — Blocks 1 goblin/troll/pirate disaster. "
            "Consumed on use. Can fail at higher levels!\n"
            "💸 **Bank Insurance** (250 stars, 10 uses) — Protects your bank from "
            "Lv4-5 disasters that drain banked stars"
        ),
        inline=False,
    )
    embed.add_field(
        name="🪓 Multi-Use Protection (Rare Drops)",
        value=(
            "🪓 **Golden Axe** (50 uses) — Works like a sword but lasts 50 hits. "
            "Never fails at any level. *3% drop on rare/legendary fishing catches*\n"
            "🛡️ **Mithril Shield** (10 uses) — Works like a helmet but lasts 10 hits. "
            "Never fails at any level. *0.4% drop on any fishing catch*"
        ),
        inline=False,
    )
    embed.add_field(
        name="✨ Rare Effect Items (Drops)",
        value=(
            "🔮 **Rune Fragment** (30 uses, from mining) — Reduces mining cooldown to 15 min "
            "(or 2m30s with a potato). *0.5% drop per mine*\n"
            "🦴 **Fossilized Noodle** (30 uses, from mining) — Reduces mining cooldown to just 1 min "
            "(or 30s with a rune). *0.1% drop per mine*\n"
            "🎣 **Bucktail Jig** (from fishing) — Use `!use jig` to get 20% legendary "
            "catch chance on your next cast. *0.3% drop per catch*\n"
            "🔫 **Ray-Gun** (3 uses, 5,000 stars or fishing drop) — Protects your items from alien "
            "abductions. *Also 0.35% drop per catch*"
        ),
        inline=False,
    )
    embed.add_field(
        name="⭐ Passive Boosts (Drops)",
        value=(
            "🧲 **Star Magnet** (20 uses, from fishing) — +15% stars on every mine "
            "and fishing catch. *1% drop on rare/legendary catches*\n"
            "🍀 **Lucky Charm** (50 uses, from fishing) — Cuts disaster chance in half. "
            "*0.05% drop on any catch*\n"
            "💜 **Heart of Leviathan** (1 use, from fishing) — Fully protects your bank "
            "from one disaster. *25% drop when catching Leviathan Scale*"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Quick Reference",
        value=(
            "• Rare items **survive disasters** — they aren't destroyed when you lose items\n"
            "• Check your items with `!inventory`\n"
            "• Passive items (Star Magnet, Lucky Charm) activate automatically\n"
            "• Helmets & swords have a **higher failure chance** on harder levels\n"
            "• Golden Axe & Mithril Shield **never fail**, making them extremely valuable"
        ),
        inline=False,
    )
    return embed


_CATEGORY_HELP_BUILDERS = {
    "mining": _mining_embed,
    "fishing": _fishing_embed,
    "farming": _farming_embed,
    "pets": _pets_embed,
    "pet": _pets_embed,
    "economy": _economy_embed,
    "gambling": _gambling_embed,
    "shop": _shop_embed,
    "trading": _shop_embed,  # "Shop & Trade" interactive section
    "space": _space_embed,
    "treasure": _treasure_embed,
    "treasure hunt": _treasure_embed,
    "items": _items_embed,
}


# ---------------------------------------------------------------------------
# Interactive help views with navigation buttons
# ---------------------------------------------------------------------------

class HelpView(discord.ui.View):
    """Main help menu with category buttons."""

    def __init__(self, author_id: int):
        super().__init__(timeout=180)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your help menu! Type `!help` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True  # type: ignore[union-attr]

    @discord.ui.button(label="Mining", style=discord.ButtonStyle.secondary, emoji="⛏️", row=0)
    async def mining_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_mining_embed(), view=view)

    @discord.ui.button(label="Fishing", style=discord.ButtonStyle.secondary, emoji="🎣", row=0)
    async def fishing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_fishing_embed(), view=view)

    @discord.ui.button(label="Farming", style=discord.ButtonStyle.secondary, emoji="🌾", row=0)
    async def farming_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_farming_embed(), view=view)

    @discord.ui.button(label="Pets", style=discord.ButtonStyle.secondary, emoji="🐾", row=1)
    async def pets_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_pets_embed(), view=view)

    @discord.ui.button(label="Economy", style=discord.ButtonStyle.secondary, emoji="💰", row=1)
    async def economy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_economy_embed(), view=view)

    @discord.ui.button(label="Gambling", style=discord.ButtonStyle.secondary, emoji="🎲", row=1)
    async def gambling_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_gambling_embed(), view=view)

    @discord.ui.button(label="Shop & Trade", style=discord.ButtonStyle.secondary, emoji="🛒", row=1)
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_shop_embed(), view=view)

    @discord.ui.button(label="Space", style=discord.ButtonStyle.secondary, emoji="🚀", row=2)
    async def space_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_space_embed(), view=view)

    @discord.ui.button(label="Treasure Hunt", style=discord.ButtonStyle.secondary, emoji="🧰", row=2)
    async def treasure_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_treasure_embed(), view=view)

    @discord.ui.button(label="Items", style=discord.ButtonStyle.secondary, emoji="🎒", row=2)
    async def items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_items_embed(), view=view)


class SubHelpView(discord.ui.View):
    """Sub-page view with Back button and category shortcuts."""

    def __init__(self, author_id: int):
        super().__init__(timeout=180)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your help menu! Type `!help` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True  # type: ignore[union-attr]

    @discord.ui.button(label="Back to Menu", style=discord.ButtonStyle.danger, emoji="◀️", row=0)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = HelpView(self.author_id)
        await interaction.response.edit_message(embed=_main_embed(), view=view)

    @discord.ui.button(label="Mining", style=discord.ButtonStyle.secondary, emoji="⛏️", row=1)
    async def mining_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_mining_embed(), view=view)

    @discord.ui.button(label="Fishing", style=discord.ButtonStyle.secondary, emoji="🎣", row=1)
    async def fishing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_fishing_embed(), view=view)

    @discord.ui.button(label="Farming", style=discord.ButtonStyle.secondary, emoji="🌾", row=1)
    async def farming_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_farming_embed(), view=view)

    @discord.ui.button(label="Pets", style=discord.ButtonStyle.secondary, emoji="🐾", row=1)
    async def pets_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_pets_embed(), view=view)

    @discord.ui.button(label="Economy", style=discord.ButtonStyle.secondary, emoji="💰", row=2)
    async def economy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_economy_embed(), view=view)

    @discord.ui.button(label="Gambling", style=discord.ButtonStyle.secondary, emoji="🎲", row=2)
    async def gambling_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_gambling_embed(), view=view)

    @discord.ui.button(label="Shop & Trade", style=discord.ButtonStyle.secondary, emoji="🛒", row=2)
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_shop_embed(), view=view)

    @discord.ui.button(label="Space", style=discord.ButtonStyle.secondary, emoji="🚀", row=3)
    async def space_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_space_embed(), view=view)

    @discord.ui.button(label="Treasure Hunt", style=discord.ButtonStyle.secondary, emoji="🧰", row=3)
    async def treasure_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_treasure_embed(), view=view)

    @discord.ui.button(label="Items", style=discord.ButtonStyle.secondary, emoji="🎒", row=3)
    async def items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_items_embed(), view=view)


# ---------------------------------------------------------------------------
# Custom HelpCommand — interactive menu + text fallbacks
# ---------------------------------------------------------------------------

class NoodleHelpCommand(commands.HelpCommand):
    """Help command with interactive button menu and text fallback lookups.

    - ``!help``              -> interactive button menu
    - ``!help mining``       -> text page for the Mining cog
    - ``!help mine``         -> detailed info for the ``!mine`` command
    """

    CATEGORY_ORDER = [
        "Economy",
        "Gambling",
        "Mining",
        "Fishing",
        "Farming",
        "Pets",
        "Treasure",
        "Shop",
        "Trading",
        "Moderator",
        "Dev",
        "Other",
    ]

    def __init__(self):
        self.no_category: str = "Other"
        super().__init__(
            command_attrs={
                "help": "Show the interactive help menu.",
            },
        )

    # --- Helpers (kept from upstream #39) ------------------------------------

    def _clean_cog_name(self, cog: Optional[commands.Cog]) -> str:
        if cog is None:
            return self.no_category or "Other"
        name = getattr(cog, "qualified_name", None) or cog.__class__.__name__
        if name.endswith("Cog"):
            name = name[:-3]
        return name or (self.no_category or "Other")

    def _format_command_line(self, command: commands.Command) -> str:
        signature = self.get_command_signature(command)
        summary = command.help or command.short_doc or "No description"
        line = f"`{signature}` — {summary}"
        return line[:1000] + "…" if len(line) > 1000 else line

    def _sort_categories(self, categories: Iterable[str]) -> List[str]:
        order_index = {name: i for i, name in enumerate(self.CATEGORY_ORDER)}
        return sorted(categories, key=lambda n: (order_index.get(n, 999), n.lower()))

    def _sort_commands(self, cmds: Iterable[commands.Command]) -> List[commands.Command]:
        return sorted(cmds, key=lambda c: c.name)

    def _find_cog_by_help_name(self, name: str) -> Optional[commands.Cog]:
        """Resolve user-typed category names like 'farming' to a Cog."""
        if self.context is None:
            return None
        target = name.strip().lower()
        for cog in self.context.bot.cogs.values():
            cleaned = self._clean_cog_name(cog).lower()
            qualified = getattr(cog, "qualified_name", "").lower()
            if target in {cleaned, qualified}:
                return cog
        return None

    def _build_chunks(self, lines: List[str], *, max_len: int = 1024) -> List[str]:
        if not lines:
            return []
        chunks: List[str] = []
        current = ""
        for raw_line in lines:
            segments = (
                [raw_line[i : i + max_len] for i in range(0, len(raw_line), max_len)]
                if len(raw_line) > max_len
                else [raw_line]
            )
            for segment in segments:
                candidate = f"{current}\n{segment}" if current else segment
                if len(candidate) > max_len:
                    if current:
                        chunks.append(current)
                    current = segment
                else:
                    current = candidate
        if current:
            chunks.append(current)
        return chunks

    async def _safe_send_embed(self, embed: discord.Embed, *, fallback_text: str) -> None:
        ctx = self.context
        if ctx is None:
            return
        try:
            await ctx.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send(fallback_text[:1900])

    # --- Main !help -> interactive menu --------------------------------------

    async def send_bot_help(self, mapping):
        ctx = self.context
        if ctx is None:
            return
        view = HelpView(ctx.author.id)
        await ctx.send(embed=_main_embed(), view=view)

    # --- !help <category_name> -> resolve cog names --------------------------

    async def command_callback(self, ctx, /, *, command=None):
        """Resolve cleaned cog names like 'farming' before default lookup."""
        if command is not None:
            normalized = command.strip()
            if " " not in normalized and ctx.bot.get_command(normalized) is None:
                category_builder = _CATEGORY_HELP_BUILDERS.get(normalized.lower())
                if category_builder is not None:
                    self.context = ctx
                    await self._safe_send_embed(
                        category_builder(),
                        fallback_text=(
                            "This help page is best viewed as an embed. "
                            "Type `!help` to open the interactive menu."
                        ),
                    )
                    return
                cog = self._find_cog_by_help_name(normalized)
                if cog is not None:
                    self.context = ctx
                    return await self.send_cog_help(cog)
        return await super().command_callback(ctx, command=command)

    # --- !help <command> -> single command info ------------------------------

    async def send_command_help(self, command: commands.Command):
        ctx = self.context
        if ctx is None:
            return

        embed = discord.Embed(
            title=f"📘 Command: {command.qualified_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Usage",
            value=f"`{self.get_command_signature(command)}`",
            inline=False,
        )
        embed.add_field(
            name="Description",
            value=command.help or command.short_doc or "No description",
            inline=False,
        )
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False,
            )

        fallback = (
            f"Command: {command.qualified_name}\n"
            f"Usage: {self.get_command_signature(command)}\n"
            f"Description: {command.help or command.short_doc or 'No description'}"
        )
        await self._safe_send_embed(embed, fallback_text=fallback)

    # --- !help <cog> -> list commands in that cog ----------------------------

    async def send_cog_help(self, cog: commands.Cog):
        cleaned = self._clean_cog_name(cog).lower()
        category_builder = _CATEGORY_HELP_BUILDERS.get(cleaned)
        if category_builder is not None:
            await self._safe_send_embed(
                category_builder(),
                fallback_text=(
                    "This help page is best viewed as an embed. "
                    "Type `!help` to open the interactive menu."
                ),
            )
            return

        commands_list = await self.filter_commands(cog.get_commands(), sort=True)

        embed = discord.Embed(
            title=f"📚 {self._clean_cog_name(cog)} Commands",
            color=discord.Color.blurple(),
        )
        lines = [self._format_command_line(cmd) for cmd in commands_list]
        chunks = self._build_chunks(lines)
        if not chunks:
            chunks = ["No commands."]

        for index, chunk in enumerate(chunks):
            embed.add_field(
                name="Commands" if index == 0 else "Commands (cont.)",
                value=chunk,
                inline=False,
            )

        fallback = "\n".join([
            f"{self._clean_cog_name(cog)} Commands",
            *[line.replace("`", "") for line in lines],
        ])
        await self._safe_send_embed(embed, fallback_text=fallback)

    # --- !help <group> -> subcommands ----------------------------------------

    async def send_group_help(self, group: commands.Group):
        ctx = self.context
        if ctx is None:
            return

        embed = discord.Embed(
            title=f"📦 Command Group: {group.qualified_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Usage",
            value=f"`{self.get_command_signature(group)}`",
            inline=False,
        )
        embed.add_field(
            name="Description",
            value=group.help or group.short_doc or "No description",
            inline=False,
        )

        subcommands = await self.filter_commands(group.commands, sort=True)
        if subcommands:
            lines = [self._format_command_line(cmd) for cmd in subcommands]
            chunks = self._build_chunks(lines)
            for index, chunk in enumerate(chunks):
                embed.add_field(
                    name="Subcommands" if index == 0 else "Subcommands (cont.)",
                    value=chunk,
                    inline=False,
                )

        fallback = (
            f"Command Group: {group.qualified_name}\n"
            f"Usage: {self.get_command_signature(group)}\n"
            f"Description: {group.help or group.short_doc or 'No description'}"
        )
        await self._safe_send_embed(embed, fallback_text=fallback)

    # --- Error handler -------------------------------------------------------

    async def send_error_message(self, error: str):
        ctx = self.context
        if ctx is None:
            return
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=(
                f"{error}\n\n"
                "Type `!help` to see the full help menu with buttons."
            ),
            color=discord.Color.red(),
        )
        await self._safe_send_embed(embed, fallback_text=error)

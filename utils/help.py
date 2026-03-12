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
            "1. Type `!mine` to find minerals (they go to your inventory)\n"
            "2. Type `!sell all` to sell your items for stars\n"
            "3. Type `!store` to see what you can buy\n"
            "4. Type `!deposit all` to keep your stars safe in the bank\n"
            "5. Use `!travel` to move between locations\n\n"
            "**Click a button below** to learn about each feature, "
            "or type `!help <command>` for info on a specific command.\n\n"
            "**Tip:** Use `!action` (or `!a`) for a quick dashboard with your stats and actions!"
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="🗺️ Travel",
        value="Locations, where to go, what works where",
        inline=True,
    )
    embed.add_field(
        name="⛏️ Mining",
        value="Dig for minerals, sell for stars",
        inline=True,
    )
    embed.add_field(
        name="🎣 Fishing",
        value="Cast your line, catch fish to sell",
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
        name="⚔️ Combat",
        value="Fight mobs, gear up, dungeon levels",
        inline=True,
    )
    embed.add_field(
        name="🔨 Crafting",
        value="Forge weapons, brew potions",
        inline=True,
    )
    embed.add_field(
        name="🎒 Items",
        value="Rare items, effects & how to get them",
        inline=True,
    )
    embed.set_footer(text="Buttons expire after 3 minutes. Type !help anytime to reopen.")
    return embed


def _travel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🗺️ Travel & Locations — How It Works",
        description=(
            "The world has **5 locations**. Most commands only work "
            "at specific locations, so you need to travel first!"
        ),
        color=discord.Color.teal(),
    )
    embed.add_field(
        name="Travel Commands",
        value=(
            "`!travel` (or `!t`) — Open the travel menu with buttons\n"
            "`!where` — Check your current location\n"
            "`!where @someone` — Check where another player is\n"
            "`!action` (or `!a`) — Dashboard with stats, timers, and quick actions"
        ),
        inline=False,
    )
    embed.add_field(
        name="The 5 Locations",
        value=(
            "🏘️ **Noodle Town** — Banking, store, trading, gambling\n"
            "⛏️ **Crystal Cave** — Mine for minerals and stars\n"
            "🎣 **Starfish Bay** — Cast your line and catch fish\n"
            "🌾 **Fusilli Farms** — Plant, tend, and harvest crops\n"
            "🚀 **Starport Ziti** — Launch into space and mine planets\n"
            "🏟️ **Noodle Colosseum** — Fight mobs in 5 dungeon levels"
        ),
        inline=False,
    )
    embed.add_field(
        name="What Works Where?",
        value=(
            "**🏘️ Noodle Town**\n"
            "`!deposit` `!withdraw` `!store` `!buy` `!trade`\n"
            "`!gamble` `!coinflip` `!blackjack` `!pickpocket` `!duel` `!russian`\n\n"
            "**⛏️ Crystal Cave** — `!mine` `!minelevel`\n"
            "**🎣 Starfish Bay** — `!fish` `!pull` `!fishing`\n"
            "**🌾 Fusilli Farms** — `!plant` `!harvest` `!tend`\n"
            "**🚀 Starport Ziti** — `!launch` `!spacemine`\n"
            "**🏟️ Noodle Colosseum** — `!fight` `!dungeon`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Works From Multiple Locations",
        value=(
            "`!unlock` — Crystal Cave or Noodle Town\n"
            "`!unlockplanet` — Starport Ziti or Noodle Town\n"
            "`!buyplot` `!upgradefarm` — Fusilli Farms or Noodle Town"
        ),
        inline=False,
    )
    embed.add_field(
        name="Works Everywhere",
        value=(
            "`!stars` `!profile` `!inventory` `!farm` `!crops`\n"
            "`!farm growbot ...` `!farm preserver ...`\n"
            "`!pet` `!fishlevel` `!baitshop` `!planets` `!where`\n"
            "`!hp` `!stamina` `!gear` `!consume` `!equip`\n"
            "`!craft` `!recipes` `!recipe` `!action`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Travel Rules",
        value=(
            "• Everyone starts at **Noodle Town**\n"
            "• Travel is instant with a **1 minute cooldown**\n"
            "• Returning to Noodle Town is always **free** (no cooldown)\n"
            "• Use `!travel` to open the button menu and pick a destination"
        ),
        inline=False,
    )
    return embed


def _mining_embed() -> discord.Embed:
    embed = discord.Embed(
        title="⛏️ Mining — How It Works",
        description=(
            "Mining is the easiest way to earn stars. "
            "You dig into a mine and find a random mineral that goes to your inventory. "
            "Use `!sell` to convert items into stars."
        ),
        color=discord.Color.dark_gold(),
    )
    embed.add_field(
        name="Getting Started (step by step)",
        value=(
            "**Step 1:** Type `!mine` — you'll find a mineral (added to your inventory)\n"
            "**Step 2:** Type `!sell all` to sell your minerals for stars\n"
            "**Step 3:** Use `!consume` to restore stamina, then mine again\n"
            "**Step 4:** When you have 500+ stars, buy a Gold Pickaxe from `!store`\n"
            "**Step 5:** Unlock deeper mines with `!unlock 2` for better loot"
        ),
        inline=False,
    )
    embed.add_field(
        name="All Mining Commands",
        value=(
            "`!mine` — Dig for minerals (costs stamina)\n"
            "`!minelevel` — See what mine levels you've unlocked\n"
            "`!minelevel 2` — Switch to a different mine level\n"
            "`!unlock 2` — Pay to unlock the next mine level"
        ),
        inline=False,
    )
    embed.add_field(
        name="Stamina Cost per Level",
        value=(
            "⛏️ **Lv1 Surface Mine** — 10 stamina, 10% ambush\n"
            "🕳️ **Lv2 Caverns** — 16 stamina, 12% ambush\n"
            "🪨 **Lv3 Deep Tunnels** — 24 stamina, 14% ambush\n"
            "🌋 **Lv4 Molten Core** — 30 stamina, 16% ambush, **bank risk on defeat**\n"
            "🌑 **Lv5 The Abyss** — 36 stamina, 20% ambush, **bank risk on defeat**\n\n"
            "Use `!consume` to restore stamina with potatoes (+6) or mushrooms (+40)."
        ),
        inline=False,
    )
    embed.add_field(
        name="Ambush Encounters",
        value=(
            "After you mine, there's a chance a **monster ambushes you**!\n"
            "You'll enter interactive combat — use Attack, Defend, or Flee.\n\n"
            "**Win:** Keep your loot, no penalties!\n"
            "**Lose:** Lose wallet stars, items, and possibly bank stars at Lv4-5.\n"
            "**Flee:** Not available for the first few turns "
            "(L1=1 turn, L2=2, L3=5, L4=7, L5=10). Flee chance depends on "
            "your stamina and defense.\n\n"
            "Equip combat gear before mining deeper levels!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Pro Tips",
        value=(
            "• The Gold Pickaxe (500 stars, one-time buy) makes rare minerals appear more often\n"
            "• Raw Potatoes (+6 stamina, 2 stars) and Golden Mushrooms (+40 stamina) keep you mining\n"
            "• At Lv4-5, buy Bank Insurance to protect your bank if you lose a fight\n"
            "• Lucky Charm halves your ambush chance!\n"
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
            "**Step 5:** Your catch goes to inventory! Use `!sell` to get stars"
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
            "🐟 **Herring** (79 stars) — Bites in 90-180 sec, 36 sec to pull — 2x better catches\n"
            "🐋 **Sturgeon** (110 stars) — Bites in 5-8 min, only 20 sec to pull — 10x better catches\n\n"
            "**Higher tier bait** = longer wait but WAY better fish.\n"
            "**Be careful with Sturgeon** — you only get 20 seconds to type `!pull`!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Fishing Levels",
        value=(
            "🎣 **Lv1 Calm Pond** — Safe, no ambushes\n"
            "🏞️ **Lv2 River Rapids** — 8% ambush chance, better catches\n"
            "🪸 **Lv3 Coral Reef** — 10% ambush, even better catches\n"
            "🚢 **Lv4 Shipwreck Depths** — 12% ambush, **bank risk on defeat**\n"
            "🌊 **Lv5 The Abyss Trench** — 14% ambush, **bank risk on defeat**\n\n"
            "You get your catch first, then the ambush triggers — win to keep it!\n"
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
        title="🌾 Farming — Basics",
        description=(
            "Farming is the safest way to earn stars. "
            "Plant crops, wait for them to grow, and harvest to add them to your inventory. "
            "Use `!sell` to convert crops to stars. No cooldowns, but soil quality matters."
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
            "**Step 5:** Type `!harvest 1` (or `!farm growbot harvest`) to collect stars\n"
            "**Step 6:** Use `!tend <plot> <fertilizer|water>` when soil gets low"
        ),
        inline=False,
    )
    embed.add_field(
        name="Core Farming Commands",
        value=(
            "`!farm` — See your farm (what's planted, growth timers)\n"
            "`!farmlevel` — Check your farm level and next upgrade cost\n"
            "`!upgradefarm` — Upgrade farm level (improves harvest quality odds)\n"
            "`!buyplot` — See all plots and prices\n"
            "`!buyplot 1` — Buy a specific plot\n"
            "`!plant wheat 1` — Plant a crop in a plot\n"
            "`!harvest 1` — Harvest one specific plot\n"
            "`!tend 1 fertilizer` — Restore soil on a plot using a tending item\n"
            "`!crops` — See all available crops and stats"
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
        name="📍 Location Rules",
        value=(
            "`!plant` `!harvest` `!tend` — Require **Fusilli Farms** 🌾\n"
            "`!buyplot` `!upgradefarm` — Work at Fusilli Farms or Noodle Town\n"
            "`!farm growbot ...` `!farm preserver ...` — Work **anywhere**\n"
            "`!farm` `!crops` — View from anywhere"
        ),
        inline=False,
    )
    embed.set_footer(text="Use the buttons below to switch between Basics, Crops & Soil, and Machinery.")
    return embed


def _farming_crops_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🌾 Farming — Crops & Soil",
        description="Crop choice, soil quality, and rotations have a big effect on farming profit.",
        color=discord.Color.green(),
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
            "**Longer crops = more profit per hour.** Pick based on how often you check Discord."
        ),
        inline=False,
    )
    embed.add_field(
        name="Soil & Plot Fatigue",
        value=(
            "• Each plot has soil condition shown in `!farm`\n"
            "• Repeatedly planting the same crop in one plot increases soil drain\n"
            "• Lower soil condition reduces harvest value and worsens quality odds\n"
            "• Use `!tend <plot> fertilizer` (+30 soil) or `!tend <plot> water` (+10 soil)\n"
            "• Buy tending items in `!store` under the Farming category"
        ),
        inline=False,
    )
    embed.add_field(
        name="Good to Know",
        value=(
            "• Farm level caps at 5, and bad quality is always possible\n"
            "• Harvest value swings with quality, weather events, and soil condition\n"
            "• Replanting the same crop repeatedly on one plot drains soil faster\n"
            "• No cooldowns: plant and harvest as often as crops are ready\n"
            "• Mushroom crops give Golden Mushrooms — use `!consume` for +40 stamina\n"
            "• Crops can be eaten for HP: Wheat +5, Carrot +10, Corn +15, Tomato +20, Melon +30\n"
            "• A plot must be empty before you plant into it"
        ),
        inline=False,
    )
    embed.set_footer(text="Machinery covers Preserver and GrowBot automation.")
    return embed


def _farming_machinery_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🌾 Farming — Machinery",
        description="Preserver and GrowBot are the farming automation and late-game progression systems.",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="GrowBot",
        value=(
            "`!farm growbot` — View GrowBot status and commands\n"
            "`!farm growbot harvest` — Harvest all ready crops\n"
            "`!farm growbot tend water` — Tend many plots in one command\n"
            "`!farm growbot plant wheat` — Plant all eligible empty plots\n"
            "`!farm growbot plant melon 3` — Plant first 3 eligible empty plots\n"
            "`!farm growbot plant carrot 1,3,6` — Plant specific plots\n\n"
            "Buy GrowBot from `!store` to unlock farm automation."
        ),
        inline=False,
    )
    embed.add_field(
        name="Preserver",
        value=(
            "`!farm preserver` — View Preserver status\n"
            "`!farm preserver upgrade` — Upgrade Preserver\n"
            "`!farm preserver collect` — Collect processed stars\n\n"
            "Preserver is bought once from `!store`, then upgraded separately. "
            "It is the late-game farming progression and focuses on melon processing bonuses."
        ),
        inline=False,
    )
    embed.add_field(
        name="Machinery Notes",
        value=(
            "• GrowBot is for bulk harvest, tending, and planting\n"
            "• Preserver adds delayed bonus stars from melon harvests\n"
            "• Both systems still depend on your farm layout, soil, and crop timing\n"
            "• Use `!farm` regularly to see pending Preserver rewards and automation status"
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
            "`!withdraw all` — Take everything out"
        ),
        inline=False,
    )
    embed.add_field(
        name="📦 Safe Storage (Keep Your Items Safe!)",
        value=(
            "`!storage` / `!vault` — View stored items (grouped by category)\n"
            "`!stash` — Open stash menu (category dropdown)\n"
            "`!stash minerals` — Stash all minerals at once\n"
            "`!stash all` — Stash everything in your inventory\n"
            "`!stash <item> [amount]` — Stash specific items\n"
            "`!unstash` — Open withdraw menu (category dropdown)\n"
            "`!unstash fish` — Withdraw all fish at once\n"
            "`!unstash <item> [amount]` — Withdraw specific items\n\n"
            "Must be in **Noodle Town** to stash/unstash.\n"
            "Items in storage are **100% immune** to disasters, "
            "death, and alien abductions — but **can't be used** until withdrawn."
        ),
        inline=False,
    )
    embed.add_field(
        name="Wallet vs Bank — What's the Difference?",
        value=(
            "💰 **Wallet** — This is your \"cash on hand\". Used for buying, "
            "gambling, and earning. **Can be lost** from ambush defeats, "
            "dungeon deaths, and alien abductions!\n\n"
            "🏦 **Bank** — This is your safe storage. Protected from almost everything. "
            "Only high-level ambush defeats and dungeon deaths can touch it. "
            "Buy Bank Insurance or find Heart of Leviathan to prevent even that.\n\n"
            "**Rule of thumb:** Always `!deposit all` after earning stars!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Watch Out!",
        value=(
            "👽 **Alien Abductions** — 1% chance when traveling away from Noodle Town! "
            "Without a Ray-Gun you auto-lose (100% wallet gone). "
            "With a Ray-Gun you fight the alien (+75 ATK both sides)!\n"
            "**This is why you should deposit before traveling!**\n\n"
            "📦 **Pro tip:** Use `!stash` to protect valuable items "
            "like rare equipment and crafting materials!"
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
            "**🦹 Pickpocket** — `!pickpocket @player 50` (or `!pp`)\n"
            "Both roll a D20 — highest roll wins! Uses its own stamina system. "
            "Quick and simple PvP.\n\n"
            "**⚔️ PvP Duel** — `!duel @player 50`\n"
            "Turn-based PvP combat at the **Noodle Colosseum**! "
            "Uses your real gear, HP, and stamina. Attack, defend, or consume items each turn. "
            "Winner takes the star wager. Damage persists after the fight.\n\n"
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
            "⚔️ **Duel** — Fairest game (0% house edge), uses your real combat stats\n"
            "🦹 **Pickpocket** — Fair dice roll (0% house edge), quick and simple\n"
            "🃏 **Blackjack** — Almost fair (~1% house edge), fun card game\n"
            "🪙 **Coinflip** — Simple and quick (2.5% house edge)\n"
            "🎲 **Gamble** — You'll probably lose (46% house edge) but jackpots are huge\n\n"
            "**If you want to make money:** Duel, Pickpocket, or Blackjack\n"
            "**If you want excitement:** Gamble (but expect to lose!)"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚔️ PvP Duel Details",
        value=(
            "• Must be at the **Noodle Colosseum** (`!travel`)\n"
            "• Uses your equipped gear, real HP, and real stamina\n"
            "• Take turns: Attack, Defend, or Consume an item (costs a turn)\n"
            "• Winner takes the star wager from both players' wallets\n"
            "• Damage persists — both players keep post-fight HP/stamina\n"
            "• 5 minute turn timer — idle player forfeits"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎲 Lucky Dice",
        value=(
            "Normally you must be in **Noodle Town** to gamble.\n"
            "Buy **Lucky Dice** from `!store` (500 stars) to gamble from anywhere!\n"
            "*(Note: PvP Duels always require the Colosseum)*"
        ),
        inline=False,
    )
    return embed


def _shop_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🛒 Shop, Selling & Trading — How It Works",
        description=(
            "Buy items to help with mining and fishing, "
            "sell gathered resources for stars, or trade with other players."
        ),
        color=discord.Color.purple(),
    )
    embed.add_field(
        name="Shop Commands",
        value=(
            "`!store` — See all items and prices\n"
            "`!buy potato` — Buy an item\n"
            "`!buy cat` — Buy a pet from the Pets category\n"
            "`!buy worm 5` — Buy 5 of something\n"
            "`!buy bag` — Upgrade your inventory capacity (+5 slots)\n"
            "`!inventory` — See your equipment and items\n"
            "`!inventory @someone` — See what someone else owns"
        ),
        inline=False,
    )
    embed.add_field(
        name="Selling Items",
        value=(
            "`!sell <item>` — Sell all of a specific item\n"
            "`!sell <item> 5` — Sell 5 of an item\n"
            "`!sell minerals` / `fish` / `crops` / `ores` — Sell a whole category\n"
            "`!sell all` — Sell everything in your inventory\n"
            "`!trash <item>` — Discard junk items (0-value fish like Old Boot)\n\n"
            "**Location Bonuses:**\n"
            "📍 Noodle Town: +25% sell bonus\n"
            "📍 Non-home location: +10% bonus\n"
            "📍 Home location: +0% (Crystal Cave for minerals, etc.)\n"
            "🧲 Star Magnet adds +15% per sell command"
        ),
        inline=False,
    )
    embed.add_field(
        name="What Should I Buy First?",
        value=(
            "1. 🪱 **Worm Bait** (33 stars) — Needed to fish at all.\n"
            "2. ⛏️ **Gold Pickaxe** (500 stars) — One-time buy, "
            "permanently boosts mining luck.\n"
            "3. 🥔 **Raw Potato** (2 stars) — Restores 6 stamina.\n"
            "4. ⚔️ **Combat Gear** — Equip weapons and armor to survive ambush encounters.\n"
            "5. 💸 **Bank Insurance** — Must-have for Lv4-5 "
            "mining/fishing/space."
        ),
        inline=False,
    )
    embed.add_field(
        name="Quick Item Reference",
        value=(
            "🥔 Raw Potato (2) — `!consume` restores 6 stamina\n"
            "⚗️ Stamina Elixir (50) — `!consume` restores 18 stamina\n"
            "🍄 Golden Mushroom (farm harvest) — `!consume` restores 40 stamina\n"
            "❤️‍🩹 Health Potion (50) — `!consume` restores 20 HP\n"
            "💸 Bank Insurance (2000) — Protects your bank from 1 defeat\n"
            "📷 Telescope (200) — View a starfield (permanent, fun item)\n"
            "🪱 Worm (33) / 🐟 Herring (79) / 🐋 Sturgeon (110) — Fishing bait\n"
            "🔫 Ray-Gun (5000, 3 uses) — Fight aliens instead of auto-losing\n"
            "🐾 Pets — Companion category in `!store` (buy with `!buy <pet>`)"
        ),
        inline=False,
    )
    embed.add_field(
        name="Trading With Other Players",
        value=(
            "`!trade @Bob 100 stars for 2 potato` — Propose a 2-way trade\n"
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
            "bigger rewards and tougher ambush encounters. Ores go to your inventory — "
            "use `!sell` to cash out."
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
            "`!spacemine` — Mine on your active planet (costs stamina)\n"
            "`!planets` — View all planets and your active planet\n"
            "`!planets 3` — Switch to a different planet\n"
            "`!unlockplanet 2` — Pay to unlock the next planet"
        ),
        inline=False,
    )
    embed.add_field(
        name="The 5 Planets",
        value=(
            "🌕 **Planet 1 — The Moon** — 44 stamina, 12% ambush\n"
            "🔴 **Planet 2 — Mars** — 50 stamina, 14% ambush\n"
            "🪐 **Planet 3 — Saturn** — 56 stamina, 16% ambush, **bank risk on defeat!**\n"
            "💠 **Planet 4 — Uranus** — 64 stamina, 18% ambush, **bank risk on defeat!**\n"
            "🥶 **Planet 5 — Pluto** — 70 stamina, 22% ambush, **bank risk on defeat!**\n\n"
            "Planets must be unlocked in order (1 → 2 → 3 → 4 → 5)."
        ),
        inline=False,
    )
    embed.add_field(
        name="Space Ambush Encounters",
        value=(
            "Space mobs are **much tougher** than surface mobs!\n"
            "You mine your ore first, then the ambush triggers.\n\n"
            "**Win:** Keep your loot!\n"
            "**Lose:** Heavy wallet/bank losses and all items destroyed.\n"
            "**Flee lockout:** Same as mining levels (P1=1 turn through P5=10 turns).\n\n"
            "Equip the best combat gear you can before space mining!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Pro Tips",
        value=(
            "• `!deposit all` before space mining — defeat penalties are brutal\n"
            "• Buy Bank Insurance for planets 3+ to protect your bank\n"
            "• Space mining costs more stamina than regular mining — stock up on mushrooms!\n"
            "• Higher planets = better ores but much tougher enemies\n"
            "• Lucky Charm halves your ambush chance!"
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
        name="🛡️ Bank & Loss Protection (from Shop)",
        value=(
            "💸 **Bank Insurance** (2000 stars, 1 use) — Protects your bank from "
            "ambush defeats or dungeon deaths that drain banked stars\n"
            "💜 **Heart of Leviathan** (1 use, fishing drop) — Fully protects "
            "your bank from one defeat"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚔️ Rare Combat Gear (Drops)",
        value=(
            "🪓 **Golden Axe** (permanent, from fishing) — Tier 3 weapon. "
            "*3% drop on rare/legendary catches*\n"
            "🛡️ **Mithril Shield** (permanent, from fishing) — Tier 3 shield. "
            "*0.4% drop on any catch*\n"
            "Equip with `!equip golden axe` or `!equip mithril shield`"
        ),
        inline=False,
    )
    embed.add_field(
        name="✨ Rare Effect Items (Drops)",
        value=(
            "🔮 **Rune Fragment** (30 uses, from mining) — A mysterious glowing fragment. "
            "*0.5% drop per mine*\n"
            "🦴 **Fossilized Noodle** (30 uses, from mining) — A rare ancient noodle. "
            "*0.5% drop per mine*\n"
            "🎣 **Bucktail Jig** (from fishing) — Use `!use jig` to get 20% legendary "
            "catch chance on your next cast. *0.3% drop per catch*\n"
            "🔫 **Ray-Gun** (3 uses, 5,000 stars or fishing drop) — Lets you fight "
            "the alien instead of auto-losing during abductions (+75 ATK both sides). "
            "*Also 0.35% drop per catch*"
        ),
        inline=False,
    )
    embed.add_field(
        name="⭐ Passive Boosts (Drops)",
        value=(
            "🧲 **Star Magnet** (20 uses, from fishing) — +15% stars on every mine, "
            "fishing catch, and space mine. *1% drop on rare/legendary catches*\n"
            "🍀 **Lucky Charm** (50 uses, from fishing) — Cuts ambush chance in half. "
            "*0.05% drop on any catch*"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Quick Reference",
        value=(
            "• Rare items **survive ambush defeats** — they aren't destroyed when you lose items\n"
            "• Check your items with `!inventory`\n"
            "• Passive items (Star Magnet, Lucky Charm) activate automatically\n"
            "• Lucky Charm halves ambush chance on mining, fishing, and space mining\n"
            "• Bank Insurance and Heart of Leviathan protect your bank from defeat penalties"
        ),
        inline=False,
    )
    return embed


def _combat_embed() -> discord.Embed:
    embed = discord.Embed(
        title="⚔️ Combat — How It Works",
        description=(
            "Travel to the **Noodle Colosseum** 🏟️ and fight mobs across 5 dungeon levels. "
            "Win stars, gain combat levels, and unlock deeper dungeons."
        ),
        color=discord.Color.red(),
    )
    embed.add_field(
        name="Getting Started",
        value=(
            "**Step 1:** Buy starter gear from `!store` (Combat section)\n"
            "**Step 2:** Equip it with `!equip wooden sword`, `!equip leather vest`, etc.\n"
            "**Step 3:** Travel to Noodle Colosseum with `!t colosseum`\n"
            "**Step 4:** Type `!fight` to battle a random mob\n"
            "**Step 5:** Use Attack ⚔️, Defend 🛡️, or Flee 🏃 buttons"
        ),
        inline=False,
    )
    embed.add_field(
        name="Combat Commands",
        value=(
            "`!fight` (or `!f`) — Start a fight at your active dungeon level\n"
            "`!dungeon` — View all dungeon levels and your progress\n"
            "`!dungeon 2` — Switch to a different dungeon level\n"
            "`!hp` — Check your HP and stamina\n"
            "`!gear` — View your equipped combat gear\n"
            "`!equip <item>` — Equip a combat item\n"
            "`!unequip <slot>` — Unequip weapon/shield/armor\n"
            "`!consume` (or `!c`, `!eat`, `!drink`) — Open consume menu to restore HP or stamina\n"
            "**In battle:** Use the dropdowns to consume items mid-fight (costs a turn!)"
        ),
        inline=False,
    )
    embed.add_field(
        name="Dungeon Levels",
        value=(
            "🏋️ **Lv1 Training Grounds** — Easy mobs, low reward. Death: lose 50% wallet\n"
            "🕯️ **Lv2 Dark Corridors** — Medium mobs. Death: 100% wallet + 50% items\n"
            "🏚️ **Lv3 Cursed Halls** — Hard mobs. Death: wallet + all items\n"
            "🔥 **Lv4 Infernal Depths** — Very hard. Death: + 2 random equipment\n"
            "🌌 **Lv5 The Void** — Endgame. Death: EVERYTHING + 10% bank"
        ),
        inline=False,
    )
    embed.add_field(
        name="Stamina System",
        value=(
            "• Every attack costs **8 stamina**, defending costs **3**\n"
            "• Lower stamina = lower damage (min 20% damage at 0 stamina)\n"
            "• Mobs also have stamina — defend to outlast them!\n"
            "• Recover with `!consume` or mid-battle dropdowns (costs a turn)\n"
            "• HP and stamina regen passively over time (1/min each)"
        ),
        inline=False,
    )
    embed.add_field(
        name="Flee System",
        value=(
            "• Flee isn't always available — ambush fights lock it for several turns\n"
            "• Flee chance depends on your **stamina** and **defense vs enemy attack**\n"
            "• Full stamina = ~90% flee chance\n"
            "• 0 stamina = 50-75% (higher defense = higher floor)\n"
            "• Failed flee = enemy gets a free attack on you!"
        ),
        inline=False,
    )
    embed.add_field(
        name="Ambush Encounters",
        value=(
            "Mining, fishing, and space mining can trigger **ambush fights**!\n"
            "You keep your loot first, then fight the monster.\n"
            "**Win:** Keep everything! **Lose:** Penalties depend on the activity level.\n"
            "Combat gear helps in ambushes too — always stay equipped!"
        ),
        inline=False,
    )
    embed.add_field(
        name="🆘 Coop Fighting",
        value=(
            "Click **Request Help** during any fight to let others join!\n"
            "• Up to **4 players** can team up against a mob\n"
            "• **Round-based:** everyone picks their action, then all resolve at once\n"
            "• Mob attacks all players (diminishing damage per target: 100%/50%/25%/12.5%)\n"
            "• Star rewards are reduced per player (2p=70%, 3p=50%, 4p=40% each)\n"
            "• Dead players get normal defeat penalties; others continue\n"
            "• Joiners must be at the **Noodle Colosseum** with HP and stamina"
        ),
        inline=False,
    )
    embed.add_field(
        name="Pro Tips",
        value=(
            "• Defense builds can outlast mobs by waiting for their stamina to drop\n"
            "• Stock up on healing fish before entering L3+ dungeons\n"
            "• Each dungeon has a **boss** with extra HP and rewards\n"
            "• Win 5 fights at your combat level to level up\n"
            "• Better gear = more attack, defense, and max HP\n"
            "• Coop helps with survival but solo gives more stars per kill"
        ),
        inline=False,
    )
    return embed


def _crafting_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🔨 Crafting — How It Works",
        description=(
            "Craft combat gear and potions from mined minerals and rare fish. "
            "Higher tier items need rarer materials."
        ),
        color=discord.Color.dark_gold(),
    )
    embed.add_field(
        name="Crafting Commands",
        value=(
            "`!recipes` — View all recipes and which you can craft\n"
            "`!recipe <name>` — View details for a specific recipe\n"
            "`!craft <name>` — Craft an item (consumes materials)"
        ),
        inline=False,
    )
    embed.add_field(
        name="Material Sources",
        value=(
            "**⛏️ Mining** — Ores and gems from all 10 mine/space levels\n"
            "**🎣 Fishing** — Rare/legendary fish are crafting ingredients\n"
            "**🧪 Junk Fish** — Seaweed, Starfish, etc. for stamina potions"
        ),
        inline=False,
    )
    embed.add_field(
        name="Gear Tiers",
        value=(
            "🗡️ **Tier 1** — Buy from `!store` (200-250 stars)\n"
            "⚔️ **Tier 2** — Craft from Iron, Copper, Silver, Gold\n"
            "✨ **Tier 3** — Craft from Platinum, Emerald, Mithril + rare fish\n"
            "🌟 **Tier 4** — Craft from Star Fragment, Adamantium + legendary fish\n"
            "🍜 **Tier 5** — Craft from Noodle Gem, Eternity Gem + endgame fish"
        ),
        inline=False,
    )
    embed.add_field(
        name="Stamina Potions",
        value=(
            "🧪 **Minor Stamina Brew** — 3 Seaweed + 1 Coal → +30 stamina\n"
            "🧴 **Stamina Tonic** — 2 Bio Jelly + 1 Tin + Golden Seahorse → +50 stamina\n"
            "⚗️ **Void Energy Flask** — 3 Void Coral + Dark Matter + Coral Golem → +80 stamina"
        ),
        inline=False,
    )
    return embed


_CATEGORY_HELP_BUILDERS = {
    "travel": _travel_embed,
    "locations": _travel_embed,
    "mining": _mining_embed,
    "fishing": _fishing_embed,
    "farming": _farming_embed,
    "pets": _pets_embed,
    "pet": _pets_embed,
    "economy": _economy_embed,
    "gambling": _gambling_embed,
    "shop": _shop_embed,
    "trading": _shop_embed,
    "space": _space_embed,
    "treasure": _treasure_embed,
    "treasure hunt": _treasure_embed,
    "items": _items_embed,
    "combat": _combat_embed,
    "crafting": _crafting_embed,
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

    @discord.ui.button(label="Travel", style=discord.ButtonStyle.primary, emoji="🗺️", row=0)
    async def travel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_travel_embed(), view=view)

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
        view = FarmingHelpView(self.author_id)
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

    @discord.ui.button(label="Combat", style=discord.ButtonStyle.danger, emoji="⚔️", row=2)
    async def combat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_combat_embed(), view=view)

    @discord.ui.button(label="Crafting", style=discord.ButtonStyle.secondary, emoji="🔨", row=2)
    async def crafting_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_crafting_embed(), view=view)

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

    @discord.ui.button(label="Travel", style=discord.ButtonStyle.primary, emoji="🗺️", row=1)
    async def travel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_travel_embed(), view=view)

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
        view = FarmingHelpView(self.author_id)
        await interaction.response.edit_message(embed=_farming_embed(), view=view)

    @discord.ui.button(label="Pets", style=discord.ButtonStyle.secondary, emoji="🐾", row=2)
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

    @discord.ui.button(label="Combat", style=discord.ButtonStyle.danger, emoji="⚔️", row=3)
    async def combat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_combat_embed(), view=view)

    @discord.ui.button(label="Crafting", style=discord.ButtonStyle.secondary, emoji="🔨", row=3)
    async def crafting_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_crafting_embed(), view=view)

    @discord.ui.button(label="Items", style=discord.ButtonStyle.secondary, emoji="🎒", row=3)
    async def items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_items_embed(), view=view)


class FarmingHelpView(discord.ui.View):
    """Dedicated farming help navigation."""

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

    @discord.ui.button(label="Basics", style=discord.ButtonStyle.success, emoji="🌾", row=1)
    async def basics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FarmingHelpView(self.author_id)
        await interaction.response.edit_message(embed=_farming_embed(), view=view)

    @discord.ui.button(label="Crops & Soil", style=discord.ButtonStyle.secondary, emoji="🥕", row=1)
    async def crops_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FarmingHelpView(self.author_id)
        await interaction.response.edit_message(embed=_farming_crops_embed(), view=view)

    @discord.ui.button(label="Machinery", style=discord.ButtonStyle.secondary, emoji="⚙️", row=1)
    async def machinery_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FarmingHelpView(self.author_id)
        await interaction.response.edit_message(embed=_farming_machinery_embed(), view=view)

    @discord.ui.button(label="Other Categories", style=discord.ButtonStyle.secondary, emoji="📚", row=2)
    async def categories_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SubHelpView(self.author_id)
        await interaction.response.edit_message(embed=_farming_embed(), view=view)


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
        "Locations",
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

    async def _safe_send_embed(
        self,
        embed: discord.Embed,
        *,
        fallback_text: str,
        view: Optional[discord.ui.View] = None,
    ) -> None:
        ctx = self.context
        if ctx is None:
            return
        try:
            await ctx.send(embed=embed, view=view)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send(fallback_text[:1900])

    # --- Main !help -> interactive menu --------------------------------------

    async def send_bot_help(self, mapping):
        ctx = self.context
        if ctx is None:
            return
        view = HelpView(ctx.author.id)
        await self._safe_send_embed(
            _main_embed(),
            fallback_text="Type `!help <category>` or `!help <command>` for help.",
            view=view,
        )

    # --- !help <category_name> -> resolve cog names --------------------------

    async def command_callback(self, ctx, /, *, command=None):
        """Resolve cleaned cog names like 'farming' before default lookup."""
        if command is not None:
            normalized = command.strip()
            if " " not in normalized and ctx.bot.get_command(normalized) is None:
                category_builder = _CATEGORY_HELP_BUILDERS.get(normalized.lower())
                if category_builder is not None:
                    self.context = ctx
                    view = FarmingHelpView(ctx.author.id) if normalized.lower() == "farming" else None
                    await self._safe_send_embed(
                        category_builder(),
                        fallback_text=(
                            "This help page is best viewed as an embed. "
                            "Type `!help` to open the interactive menu."
                        ),
                        view=view,
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
            view = FarmingHelpView(self.context.author.id) if cleaned == "farming" and self.context is not None else None
            await self._safe_send_embed(
                category_builder(),
                fallback_text=(
                    "This help page is best viewed as an embed. "
                    "Type `!help` to open the interactive menu."
                ),
                view=view,
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

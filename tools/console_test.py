"""Console testing app for Noodle Star Bot.

Run this to test bot commands without connecting to Discord.
Usage: python console_test.py
"""

import os
import re
import shlex
import sys
import asyncio
from dataclasses import dataclass, field
from typing import Optional

# Set up paths - add parent directory so we can import bot modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)  # So database file is created in project root

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # Ignore if reconfigure not available

from config import COMMAND_PREFIX, FISHING_BAIT_TIERS, SHOP_ITEMS
from database.migrations import MigrationManager
from services.economy import EconomyService
from services.fishing import FishingService, FishingState, get_fishing_conditions
from services.gambling import GamblingService
from services.mining import MiningService
from services.shop import ShopService
from services.trading import TradeService, TradeState, TRADE_COUNTDOWN_SECONDS


# =============================================================================
# Mock Discord Objects
# =============================================================================


@dataclass
class MockMember:
    """Simulates a Discord Member."""

    id: int
    name: str
    display_name: str = ""
    bot: bool = False

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name

    @property
    def mention(self) -> str:
        return f"@{self.name}"

    def __str__(self) -> str:
        return self.name


@dataclass
class MockEmbed:
    """Simulates a Discord Embed for display."""

    title: str = ""
    description: str = ""
    color: int = 0
    fields: list = field(default_factory=list)

    def add_field(self, name: str, value: str, inline: bool = False):
        self.fields.append({"name": name, "value": value, "inline": inline})

    def render(self) -> str:
        """Render embed as console-friendly text."""
        lines = []
        if self.title:
            lines.append(f"\n{'=' * 50}")
            lines.append(f"  {self.title}")
            lines.append(f"{'=' * 50}")
        if self.description:
            lines.append(self.description)
        for f in self.fields:
            lines.append(f"\n  {f['name']}")
            lines.append(f"    {f['value']}")
        if self.title:
            lines.append(f"{'=' * 50}\n")
        return "\n".join(lines)


class MockContext:
    """Simulates a Discord Context."""

    def __init__(self, author: MockMember):
        self.author = author
        self.messages: list[str] = []

    async def send(self, content: str = None, embed: MockEmbed = None):
        """Capture sent messages for display."""
        if content:
            self.messages.append(content)
        if embed:
            self.messages.append(embed.render())


# =============================================================================
# Console Bot
# =============================================================================


class ConsoleBot:
    """Console-based testing interface for the Noodle Star Bot."""

    def __init__(self):
        # Services
        self.economy = EconomyService()
        self.fishing = FishingService()
        self.gambling = GamblingService()
        self.mining = MiningService()
        self.shop = ShopService()
        self.trading = TradeService()

        # Set up fishing bite callback
        self.fishing.set_bite_callback(self._on_fishing_bite)

        # Set up trading callback
        self.trading.set_trade_callback(self._on_trade_event)

        # Simulated users - can add more with !adduser
        self.users: dict[str, MockMember] = {
            "user1": MockMember(id=1001, name="TestUser1"),
            "user2": MockMember(id=1002, name="TestUser2"),
            "mod": MockMember(id=9999, name="Moderator"),
        }
        self.current_user = self.users["user1"]

    async def _on_fishing_bite(self, user_id: int, channel_id: int, pull_window: int):
        """Callback for fishing bite notifications."""
        # Find user by ID
        user_name = "Unknown"
        for user in self.users.values():
            if user.id == user_id:
                user_name = user.name
                break

        if pull_window == -1:
            print(f"\n*** FISHING: @{user_name}, the fish got away! You didn't pull in time. ***\n")
        else:
            print(f"\n*** FISHING: @{user_name}, you feel a tug! Type !pull within {pull_window} seconds! ***\n")

    async def _on_trade_event(self, event, proposer_id, channel_id, session, extra=""):
        """Callback for trade notifications."""
        if event == "timeout":
            print(
                f"\n*** TRADE: Trade between {session.proposer_name} and "
                f"{session.opponent_name} expired (no response). ***\n"
            )
        elif event == "completed":
            proposer_gives = self.trading.format_offer(session.proposer_offer)
            opponent_gives = self.trading.format_offer(session.opponent_offer)
            print(
                f"\n*** TRADE COMPLETE! ***\n"
                f"  {session.proposer_name} gave: {proposer_gives}\n"
                f"  {session.opponent_name} gave: {opponent_gives}\n"
            )
        elif event == "failed":
            print(f"\n*** TRADE FAILED: {extra} ***\n")

    def print_help(self):
        """Print help message."""
        print(
            """
================================================================================
                        NOODLE STAR BOT - CONSOLE TESTER
================================================================================

CONSOLE COMMANDS (no prefix):
  help              - Show this help message
  switch <user>     - Switch to a different user (user1, user2, mod, or custom)
  adduser <name>    - Add a new simulated user
  users             - List all simulated users
  whoami            - Show current user
  exit / quit       - Exit the console tester

BOT COMMANDS (use ! prefix):
  Economy:
    !stars [@user]        - Check noodle stars balance
    !deposit <amt|all>    - Deposit stars to bank
    !withdraw <amt|all>   - Withdraw stars from bank
    !topstars             - Show top 10 leaderboard
    !bottomstars          - Show bottom 10 leaderboard

  Gambling:
    !gamble <amount>              - Roll dice (need 7 to win)
    !coinflip <amount> <h|t>      - Flip a coin
    !duel @user <amount>          - Challenge another user

  Mining:
    !mine [potato|mushroom]       - Mine for minerals

  Fishing:
    !fish [bait]                  - Cast your line (auto-selects if one bait type)
    !pull                         - Reel in when you feel a bite
    !fishing                      - Check fishing status
    !baitshop                     - View bait stats

  Shop:
    !store                        - View shop items
    !buy <item>                   - Buy an item
    !inventory [@user]            - Check inventory

  Trading:
    !trade help                        - Show trade help menu
    !trade @user [offer] for [request] - Propose a trade
    !trade accept                      - Accept a pending trade
    !trade cancel                      - Cancel your current trade

  Moderator:
    !addstar @user <amount>       - Add stars to user
    !removestar @user <amount>    - Remove stars from user

================================================================================
"""
        )

    def find_user_by_mention(self, mention: str) -> Optional[MockMember]:
        """Find a user by @mention or name."""
        # Remove @ symbol if present
        name = mention.lstrip("@")
        for user in self.users.values():
            if user.name.lower() == name.lower():
                return user
        return None

    def parse_command(self, text: str) -> tuple[str, list[str]]:
        """Parse command and arguments from input."""
        text = text.strip()
        if not text:
            return "", []

        # Use shlex for proper quote handling
        try:
            parts = shlex.split(text)
        except ValueError:
            parts = text.split()

        if not parts:
            return "", []

        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args

    async def handle_console_command(self, cmd: str, args: list[str]) -> bool:
        """Handle console-specific commands. Returns True if handled."""
        if cmd == "help":
            self.print_help()
            return True

        elif cmd == "switch":
            if not args:
                print("Usage: switch <username>")
                return True
            name = args[0].lower()
            if name in self.users:
                self.current_user = self.users[name]
                print(f"Switched to {self.current_user.name}")
            else:
                print(f"User '{name}' not found. Use 'users' to list or 'adduser' to create.")
            return True

        elif cmd == "adduser":
            if not args:
                print("Usage: adduser <username>")
                return True
            name = args[0]
            key = name.lower()
            if key in self.users:
                print(f"User '{name}' already exists.")
            else:
                new_id = max(u.id for u in self.users.values()) + 1
                self.users[key] = MockMember(id=new_id, name=name)
                print(f"Added user '{name}' with ID {new_id}")
            return True

        elif cmd == "users":
            print("\nSimulated Users:")
            for key, user in self.users.items():
                marker = " <-- current" if user == self.current_user else ""
                print(f"  {key}: {user.name} (ID: {user.id}){marker}")
            print()
            return True

        elif cmd == "whoami":
            print(f"Current user: {self.current_user.name} (ID: {self.current_user.id})")
            return True

        elif cmd in ("exit", "quit"):
            print("Goodbye!")
            return "exit"

        return False

    async def handle_bot_command(self, cmd: str, args: list[str]):
        """Handle bot commands."""
        ctx = MockContext(self.current_user)

        # Remove command prefix
        cmd = cmd.lstrip(COMMAND_PREFIX)

        # Economy commands
        if cmd == "stars":
            member = self.current_user
            if args:
                member = self.find_user_by_mention(args[0])
                if not member:
                    print(f"User '{args[0]}' not found.")
                    return

            result = self.economy.get_balance(member.id, str(member))
            await ctx.send(
                f"* {member.mention}'s Noodle Stars:\n"
                f"  Wallet: **{result.wallet}** stars\n"
                f"  Bank: **{result.bank}** stars\n"
                f"  Total: **{result.total}** stars"
            )

        elif cmd == "deposit":
            if not args:
                await ctx.send("Usage: !deposit <amount|all>")
            else:
                result = self.economy.deposit(
                    self.current_user.id, str(self.current_user), args[0]
                )
                if not result.success:
                    await ctx.send(f"Error: {result.message}")
                else:
                    await ctx.send(
                        f"Deposited stars!\n"
                        f"  Wallet: **{result.wallet}** | Bank: **{result.bank}** | Total: **{result.total}**"
                    )

        elif cmd == "withdraw":
            if not args:
                await ctx.send("Usage: !withdraw <amount|all>")
            else:
                result = self.economy.withdraw(
                    self.current_user.id, str(self.current_user), args[0]
                )
                if not result.success:
                    await ctx.send(f"Error: {result.message}")
                else:
                    await ctx.send(
                        f"Withdrew stars!\n"
                        f"  Wallet: **{result.wallet}** | Bank: **{result.bank}** | Total: **{result.total}**"
                    )

        elif cmd == "topstars":
            results = self.economy.get_leaderboard(limit=10, ascending=False)
            if not results:
                await ctx.send("No noodle stars have been awarded yet!")
            else:
                embed = MockEmbed(title="Top 10 Good Noodles")
                for i, (username, stars) in enumerate(results, 1):
                    medal = ["", "1.", "2.", "3."][min(i, 3)] if i <= 3 else f"{i}."
                    embed.add_field(name=f"{medal} {username}", value=f"{stars} stars")
                await ctx.send(embed=embed)

        elif cmd == "bottomstars":
            results = self.economy.get_leaderboard(limit=10, ascending=True)
            if not results:
                await ctx.send("No noodle stars have been awarded yet!")
            else:
                embed = MockEmbed(title="Bottom 10 Noodles")
                for i, (username, stars) in enumerate(results, 1):
                    embed.add_field(name=f"{i}. {username}", value=f"{stars} stars")
                await ctx.send(embed=embed)

        # Gambling commands
        elif cmd == "gamble":
            if not args:
                await ctx.send("Usage: !gamble <amount>")
            else:
                try:
                    amount = int(args[0])
                    result = self.gambling.gamble(
                        self.current_user.id, str(self.current_user), amount
                    )
                    if not result.success:
                        await ctx.send(f"Error: {result.message}")
                    elif result.won:
                        await ctx.send(
                            f"GAMBLE: Rolled **{result.roll}**!\n"
                            f"  WIN! Multiplier: {result.multiplier}x\n"
                            f"  Won **{result.amount_changed}** stars!\n"
                            f"  New balance: **{result.new_balance}** stars"
                        )
                    else:
                        await ctx.send(
                            f"GAMBLE: Rolled **{result.roll}**...\n"
                            f"  LOSE! Needed a 7!\n"
                            f"  Lost **{result.amount_changed}** stars!\n"
                            f"  New balance: **{result.new_balance}** stars"
                        )
                except ValueError:
                    await ctx.send("Please enter a valid number.")

        elif cmd == "coinflip":
            if len(args) < 2:
                await ctx.send("Usage: !coinflip <amount> <heads|tails|h|t>")
            else:
                try:
                    amount = int(args[0])
                    choice = args[1]
                    result = self.gambling.coinflip(
                        self.current_user.id, str(self.current_user), amount, choice
                    )
                    if not result.success:
                        await ctx.send(f"Error: {result.message}")
                    elif result.won:
                        await ctx.send(
                            f"COINFLIP: Landed on **{result.result.upper()}**!\n"
                            f"  WIN! You won **{result.amount_changed}** stars!\n"
                            f"  New balance: **{result.new_balance}** stars"
                        )
                    else:
                        await ctx.send(
                            f"COINFLIP: Landed on **{result.result.upper()}**!\n"
                            f"  LOSE! You lost **{result.amount_changed}** stars!\n"
                            f"  New balance: **{result.new_balance}** stars"
                        )
                except ValueError:
                    await ctx.send("Please enter a valid number.")

        elif cmd == "duel":
            if len(args) < 2:
                await ctx.send("Usage: !duel @user <amount>")
            else:
                opponent = self.find_user_by_mention(args[0])
                if not opponent:
                    await ctx.send(f"User '{args[0]}' not found.")
                    return
                if opponent.bot:
                    await ctx.send("You can't duel a bot!")
                    return
                try:
                    amount = int(args[1])
                    result = self.gambling.duel(
                        self.current_user.id,
                        str(self.current_user),
                        opponent.id,
                        str(opponent),
                        amount,
                    )
                    if not result.success:
                        await ctx.send(f"Error: {result.message}")
                    else:
                        winner = (
                            self.current_user
                            if result.winner_id == self.current_user.id
                            else opponent
                        )
                        loser = opponent if winner == self.current_user else self.current_user
                        await ctx.send(
                            f"DICE DUEL!\n"
                            f"  {self.current_user.mention} rolled **{result.challenger_roll}**\n"
                            f"  {opponent.mention} rolled **{result.opponent_roll}**\n"
                            f"\n  WINNER: {winner.mention}!\n"
                            f"  {winner.mention} won **{amount}** stars from {loser.mention}!\n"
                            f"\n  {self.current_user.mention}: **{result.challenger_new_balance}** stars\n"
                            f"  {opponent.mention}: **{result.opponent_new_balance}** stars"
                        )
                except ValueError:
                    await ctx.send("Please enter a valid number.")

        # Mining commands
        elif cmd == "mine":
            use_item = args[0] if args else None
            result = self.mining.mine(
                self.current_user.id, str(self.current_user), use_item
            )
            if not result.success:
                await ctx.send(f"Error: {result.message}")
            else:
                msg = (
                    f"MINING: Found {result.mineral_emoji} **{result.mineral_name}**!\n"
                    f"  Earned **{result.stars_earned}** stars!"
                )
                if result.disaster == "collapse":
                    if result.disaster_protected:
                        msg += "\n  COLLAPSE! Your helmet protected you!"
                    else:
                        msg += f"\n  COLLAPSE! Lost **{result.stars_lost}** stars!"
                elif result.disaster == "goblin":
                    if result.disaster_protected:
                        msg += "\n  GOBLIN! Your sword protected you!"
                    else:
                        msg += f"\n  GOBLIN! Lost **{result.stars_lost}** stars!"
                msg += f"\n  New balance: **{result.new_balance}** stars"
                await ctx.send(msg)

        # Shop commands
        elif cmd == "store":
            embed = MockEmbed(title="Noodle Star Store")
            embed.description = "Use !buy <item> to purchase items!"
            items = self.shop.get_items()
            for item in items:
                embed.add_field(
                    name=f"{item.emoji} {item.display_name} - {item.price} stars",
                    value=item.description,
                )
            await ctx.send(embed=embed)

        elif cmd == "buy":
            if not args:
                await ctx.send("Usage: !buy <item>")
            else:
                item_name = " ".join(args)
                result = self.shop.buy(
                    self.current_user.id, str(self.current_user), item_name
                )
                if not result.success:
                    await ctx.send(f"Error: {result.message}")
                else:
                    await ctx.send(
                        f"Purchased {result.item_emoji} **{result.item_name}** "
                        f"for **{result.price}** stars!\n"
                        f"  New balance: **{result.new_balance}** stars"
                    )

        elif cmd == "inventory":
            member = self.current_user
            if args:
                member = self.find_user_by_mention(args[0])
                if not member:
                    print(f"User '{args[0]}' not found.")
                    return

            items_list = self.shop.get_inventory_display(member.id)
            embed = MockEmbed(title=f"{member.name}'s Inventory")
            if items_list:
                embed.description = "\n".join(items_list)
            else:
                embed.description = "*Empty - Visit the !store to buy items!*"
            await ctx.send(embed=embed)

        # Fishing commands
        elif cmd == "fish":
            # Pass bait type directly to cast_line (auto-selects if only one type)
            bait_type = args[0] if args else None
            result = await self.fishing.cast_line(
                self.current_user.id,
                str(self.current_user),
                0,  # channel_id not needed for console
                bait_type=bait_type,
            )
            if not result.success:
                await ctx.send(f"FISHING: {result.message}")
            else:
                await ctx.send(f"FISHING: {result.message}")

        elif cmd == "pull":
            result = self.fishing.pull_line(self.current_user.id, str(self.current_user))
            if not result.success:
                await ctx.send(f"FISHING: {result.message}")
            else:
                if result.stars_earned > 0:
                    rarity_prefix = ""
                    if result.catch_rarity == "legendary":
                        rarity_prefix = "LEGENDARY! "
                    elif result.catch_rarity == "rare":
                        rarity_prefix = "RARE! "
                    await ctx.send(
                        f"FISHING: {rarity_prefix}Caught {result.catch_emoji} **{result.catch_name}**!\n"
                        f"  Earned **{result.stars_earned}** stars!\n"
                        f"  New balance: **{result.new_balance}** stars"
                    )
                else:
                    await ctx.send(
                        f"FISHING: Caught {result.catch_emoji} **{result.catch_name}**!\n"
                        f"  *It's worthless junk...*\n"
                        f"  Balance: **{result.new_balance}** stars"
                    )

        elif cmd == "fishing":
            status = self.fishing.get_status(self.current_user.id, str(self.current_user))
            lines = [f"FISHING STATUS for {self.current_user.name}:"]
            lines.append(f"  * {get_fishing_conditions()} *")

            # Show available bait
            available_baits = self.fishing.get_available_baits(self.current_user.id)
            if available_baits:
                bait_strs = []
                for bt, count in available_baits:
                    info = FISHING_BAIT_TIERS[bt]
                    bait_strs.append(f"{info['emoji']} {bt} x{count}")
                lines.append(f"  Your bait: {', '.join(bait_strs)}")
            else:
                lines.append("  Your bait: None - buy from !store")

            if status.is_fishing:
                if status.state == FishingState.WAITING:
                    lines.append("  Status: Waiting for a bite...")
                    if status.time_until_bite is not None:
                        if status.time_until_bite > 60:
                            lines.append("  Hint: Be patient...")
                        elif status.time_until_bite > 10:
                            lines.append("  Hint: Should be soon...")
                        else:
                            lines.append("  Hint: Any moment now!")
                elif status.state == FishingState.BITING:
                    lines.append("  Status: ** A FISH IS BITING! **")
                    if status.time_until_expires is not None:
                        lines.append(f"  Time left: **{status.time_until_expires}s** to !pull!")
            else:
                lines.append("  Status: Not fishing")
                if status.cooldown_remaining and status.cooldown_remaining > 0:
                    mins = status.cooldown_remaining // 60
                    secs = status.cooldown_remaining % 60
                    if mins > 0:
                        lines.append(f"  Cooldown: {mins}m {secs}s")
                    else:
                        lines.append(f"  Cooldown: {secs}s")
                else:
                    lines.append("  Ready to fish! Use !fish")

            await ctx.send("\n".join(lines))

        elif cmd == "baitshop":
            lines = ["BAIT SHOP:", "  Buy bait from !store, then use !fish <bait> to cast"]
            lines.append(f"  * {get_fishing_conditions()} *")
            lines.append("")
            bait_descriptions = {
                "worm": {"bite": "Quick", "window": "Generous", "rarity": "Standard"},
                "herring": {"bite": "Moderate", "window": "Tight", "rarity": "Improved"},
                "sturgeon": {"bite": "Very slow", "window": "Very tight", "rarity": "Excellent"},
            }
            for bait_key, bait_info in FISHING_BAIT_TIERS.items():
                desc = bait_descriptions.get(bait_key, {})
                lines.append(f"  {bait_info['emoji']} {bait_info['display_name']} ({bait_key}):")
                lines.append(f"    Bite speed: {desc.get('bite', '?')}")
                lines.append(f"    Reaction window: {desc.get('window', '?')}")
                lines.append(f"    Rare catch odds: {desc.get('rarity', '?')}")
                lines.append("")
            await ctx.send("\n".join(lines))

        # Trading commands
        elif cmd == "trade":
            if not args or args[0].lower() == "help":
                await ctx.send(
                    "TRADE HELP:\n"
                    "  Propose:  !trade @user <your offer> for <their offer>\n"
                    "            Example: !trade @Bob 50 stars 1 sword for 2 helmet\n"
                    "  Gift:     !trade @user <offer>  (no 'for', opponent still accepts)\n"
                    "            Example: !trade @Bob 100 stars\n"
                    "  Accept:   !trade accept\n"
                    "  Cancel:   !trade cancel\n"
                    "\n"
                    "  How it works:\n"
                    "    1. Propose a trade to another player.\n"
                    "    2. They have 60 seconds to accept or it expires.\n"
                    "    3. After accepting, 10-second countdown (either side can cancel).\n"
                    "    4. Trade executes automatically after the countdown.\n"
                    "\n"
                    "  Tradeable: stars, helmets, swords, potatoes, golden mushrooms,\n"
                    "             gold pickaxes, and all bait types."
                )
            elif args[0].lower() == "accept":
                result = self.trading.accept_trade(
                    self.current_user.id, str(self.current_user)
                )
                if not result.success:
                    await ctx.send(f"TRADE: {result.message}")
                else:
                    session = result.session
                    proposer_gives = self.trading.format_offer(session.proposer_offer)
                    opponent_gives = self.trading.format_offer(session.opponent_offer)
                    await ctx.send(
                        f"TRADE ACCEPTED! Countdown started ({TRADE_COUNTDOWN_SECONDS}s).\n"
                        f"  {session.proposer_name} gives: {proposer_gives}\n"
                        f"  {session.opponent_name} gives: {opponent_gives}\n"
                        f"  Either party can !trade cancel to abort."
                    )
            elif args[0].lower() == "cancel":
                result = self.trading.cancel_trade(self.current_user.id)
                if not result.success:
                    await ctx.send(f"TRADE: {result.message}")
                else:
                    session = result.session
                    await ctx.send(
                        f"TRADE CANCELLED by {self.current_user.name}.\n"
                        f"  (was between {session.proposer_name} and {session.opponent_name})"
                    )
            else:
                # Propose trade: !trade @user [offer args...]
                opponent = self.find_user_by_mention(args[0])
                if not opponent:
                    await ctx.send(f"User '{args[0]}' not found.")
                elif opponent.bot:
                    await ctx.send("You can't trade with a bot.")
                else:
                    offer_args = args[1:]  # everything after the @mention
                    result = self.trading.propose_trade(
                        proposer_id=self.current_user.id,
                        proposer_name=str(self.current_user),
                        opponent_id=opponent.id,
                        opponent_name=str(opponent),
                        channel_id=0,
                        args=offer_args,
                    )
                    if not result.success:
                        await ctx.send(f"TRADE: {result.message}")
                    else:
                        session = result.session
                        proposer_gives = self.trading.format_offer(session.proposer_offer)
                        opponent_gets = self.trading.format_offer(session.opponent_offer)
                        await ctx.send(
                            f"TRADE PROPOSAL to {opponent.name}:\n"
                            f"  {session.proposer_name} gives: {proposer_gives}\n"
                            f"  {session.opponent_name} gives: {opponent_gets}\n"
                            f"  {opponent.name}, type !trade accept or !trade cancel (60s timeout)"
                        )

        # Moderator commands
        elif cmd == "addstar":
            if len(args) < 2:
                await ctx.send("Usage: !addstar @user <amount>")
            else:
                member = self.find_user_by_mention(args[0])
                if not member:
                    await ctx.send(f"User '{args[0]}' not found.")
                    return
                try:
                    amount = int(args[1])
                    result = self.economy.add_stars(member.id, str(member), amount)
                    await ctx.send(
                        f"[MOD] Added **{amount}** star(s) to {member.mention}!\n"
                        f"  They now have **{result.wallet}** stars!"
                    )
                except ValueError:
                    await ctx.send("Please enter a valid number.")

        elif cmd == "removestar":
            if len(args) < 2:
                await ctx.send("Usage: !removestar @user <amount>")
            else:
                member = self.find_user_by_mention(args[0])
                if not member:
                    await ctx.send(f"User '{args[0]}' not found.")
                    return
                try:
                    amount = int(args[1])
                    result = self.economy.remove_stars(member.id, str(member), amount)
                    await ctx.send(
                        f"[MOD] Removed **{amount}** star(s) from {member.mention}!\n"
                        f"  They now have **{result.wallet}** stars!"
                    )
                except ValueError:
                    await ctx.send("Please enter a valid number.")

        else:
            await ctx.send(f"Unknown command: {cmd}")

        # Print all messages
        for msg in ctx.messages:
            print(msg)

    async def run(self):
        """Run the console testing loop."""
        # Run migrations
        print("Running database migrations...")
        migration_manager = MigrationManager()
        applied = migration_manager.run_migrations()
        if applied:
            print(f"Applied {len(applied)} migration(s)")
        else:
            print("Database is up to date.")

        self.print_help()
        print(f"Current user: {self.current_user.name}\n")

        loop = asyncio.get_running_loop()
        while True:
            try:
                user_input = await loop.run_in_executor(
                    None, input, f"[{self.current_user.name}] > "
                )
                user_input = user_input.strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            cmd, args = self.parse_command(user_input)

            # Check if it's a console command
            result = await self.handle_console_command(cmd, args)
            if result == "exit":
                break
            elif result:
                continue

            # Otherwise, treat as bot command
            if user_input.startswith(COMMAND_PREFIX):
                await self.handle_bot_command(cmd, args)
            else:
                print(f"Unknown command. Type 'help' for available commands.")


# =============================================================================
# Entry Point
# =============================================================================


def main():
    """Main entry point."""
    import asyncio

    try:
        bot = ConsoleBot()
        asyncio.run(bot.run())
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        # Removed blocking prompt to keep automated tester usable


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        # Removed blocking prompt to keep automated tester usable

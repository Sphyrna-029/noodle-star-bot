"""Economy commands cog."""

from datetime import datetime

import discord
from discord.ext import commands

from cogs.locations.check import require_location
from cogs.economy.use_case import EconomyUseCases
from database.repository import UserRepository


class EconomyCog(commands.Cog):
    """Commands for checking and managing star balances."""

    def __init__(self, bot):
        self.bot = bot
        self.repo = UserRepository()
        self.economy = EconomyUseCases(self.repo)

    @commands.command(name="stars")
    async def check_stars(self, ctx, member: discord.Member = None):
        """Check noodle stars for a user"""
        if member is None:
            member = ctx.author

        result = self.economy.get_balance(member.id, str(member))

        await ctx.send(
            f"⭐ {member.mention}'s Noodle Stars:\n"
            f"💰 Wallet: **{result.wallet}** stars\n"
            f"🏦 Bank: **{result.bank}** stars\n"
            f"📊 Total: **{result.total}** stars"
        )

    @commands.command(name="profile", aliases=["achievements", "ach"])
    async def profile(self, ctx, member: discord.Member = None):
        """View your profile with simple achievement progress."""
        if member is None:
            member = ctx.author

        result = self.economy.get_profile(member.id, str(member))
        unlocked = [achievement for achievement in result.achievements if achievement.unlocked]

        if result.newly_unlocked:
            names = ", ".join(
                f"{achievement.emoji} **{achievement.name}**"
                for achievement in result.newly_unlocked
            )
            plural = "achievement" if len(result.newly_unlocked) == 1 else "achievements"
            await ctx.send(f"🎉 {member.mention} unlocked {plural}: {names}")

        embed = discord.Embed(
            title=f"👤 {member.display_name}'s Profile",
            color=discord.Color.teal(),
        )
        embed.add_field(
            name="💰 Balance",
            value=(
                f"Wallet: **{result.wallet}**\n"
                f"Bank: **{result.bank}**\n"
                f"Total: **{result.total}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🏆 Achievements",
            value=f"Unlocked: **{result.unlocked_achievements}/{result.total_achievements}**",
            inline=False,
        )

        if unlocked:
            embed.add_field(
                name="✅ Unlocked",
                value="\n".join(
                    f"{achievement.emoji} {achievement.name} - {achievement.description}"
                    for achievement in unlocked
                ),
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="topstars")
    async def top_stars(self, ctx):
        """Show top 5 users with the most noodle stars."""
        results = self.economy.get_leaderboard(limit=5, ascending=False)

        if not results:
            await ctx.send("No noodle stars have been awarded yet!")
            return

        embed = discord.Embed(title="🌟 Top 5 Good Noodles 🌟", color=discord.Color.gold())

        for i, (username, stars) in enumerate(results, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(name=f"{medal} {username}", value=f"{stars} stars", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="bottomstars")
    async def bottom_stars(self, ctx):
        """Show bottom 5 users with the least noodle stars."""
        results = self.economy.get_leaderboard(limit=5, ascending=True)

        if not results:
            await ctx.send("No noodle stars have been awarded yet!")
            return

        embed = discord.Embed(title="📉 Bottom 5 Noodles 📉", color=discord.Color.red())

        for i, (username, stars) in enumerate(results, 1):
            embed.add_field(name=f"{i}. {username}", value=f"{stars} stars", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="deposit")
    async def deposit(self, ctx, amount: str = ''):
        """Deposit noodle stars into your bank for safekeeping."""
        if not await require_location(ctx, "noodle_town"):
            return
        if amount == '':
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an amount to deposit! "
                f"Usage: `!deposit <amount>` or `!deposit all`"
            )
            return

        result = self.economy.deposit(ctx.author.id, str(ctx.author), amount)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"🏦 {ctx.author.mention} deposited **{result.message.split('**')[1]}** stars into the bank!\n"
            f"💰 Wallet: **{result.wallet}** stars\n"
            f"🏦 Bank: **{result.bank}** stars\n"
            f"📊 Total: **{result.total}** stars"
        )

    @commands.command(name="withdraw")
    async def withdraw(self, ctx, amount: str = ''):
        """Withdraw noodle stars from your bank."""
        if not await require_location(ctx, "noodle_town"):
            return
        if amount == '':
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify an amount to withdraw! "
                f"Usage: `!withdraw <amount>` or `!withdraw all`"
            )
            return

        result = self.economy.withdraw(ctx.author.id, str(ctx.author), amount)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"🏦 {ctx.author.mention} withdrew **{result.message.split('**')[1]}** stars from the bank!\n"
            f"💰 Wallet: **{result.wallet}** stars\n"
            f"🏦 Bank: **{result.bank}** stars\n"
            f"📊 Total: **{result.total}** stars"
        )

    @commands.command(name="starstats")
    async def star_stats(self, ctx, period: str | None = None):
        """Show monthly earned stars and more. Usage: !stats [last|YYYY-MM]"""

        if period is None:
            now = datetime.utcnow()
            year, month = now.year, now.month
            earned = self.economy.get_monthly_stars_earned(year, month)
        else:
            period = period.strip().lower()

            if period == "last":
                earned, year, month = self.economy.get_last_month_stars_earned()
            else:
                try:
                    parsed = datetime.strptime(period, "%Y-%m")
                    year, month = parsed.year, parsed.month
                except ValueError:
                    await ctx.send(
                        f"❌ {ctx.author.mention}, invalid period. Use `last` or `YYYY-MM` (example: `2026-01`)."
                    )
                    return

                earned = self.economy.get_monthly_stars_earned(year, month)

        lost = self.economy.get_monthly_stars_lost(year, month)
        economy_stats = self.economy.get_economy_stats()
        total_in_circulation = economy_stats.total_stars if economy_stats.success else 0

        month_label = f"{year}-{month:02d}"
        embed = discord.Embed(
            title=f"📈 ZGAF star stats for {month_label}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="🌟 Stars earned:",
            value=f"**{earned}**",
            inline=False,
        )
        embed.add_field(
            name="📉 Stars lost:",
            value=f"**{lost}**",
            inline=False,
        )
        embed.add_field(
            name="🔄 Stars in circulation:",
            value=f"**{total_in_circulation}**",
            inline=False,
        )

        await ctx.send(embed=embed)


    # ── Storage (safe vault) ────────────────────────────────

    @commands.command(name="storage", aliases=["vault"])
    async def storage(self, ctx):
        """View your safe storage. Items here are immune to all disasters."""
        items = self.repo.get_storage_summary(ctx.author.id)

        if not items:
            await ctx.send(
                f"📦 {ctx.author.mention}, your storage is empty!\n"
                f"Use `!stash <item>` in **Noodle Town** to store items safely."
            )
            return

        embed = discord.Embed(
            title="📦 Safe Storage",
            description=(
                "Items here are **100% safe** — immune to disasters, "
                "death penalties, and alien abductions.\n"
                "Items in storage **cannot be used** until withdrawn."
            ),
            color=discord.Color.dark_teal(),
        )

        equip_lines = []
        inv_lines = []

        for row in items:
            key = row["item_key"]
            count = row["count"]
            item_type = row["item_type"]

            if item_type == "equipment":
                uses = row["total_uses"]
                if uses > 1:
                    equip_lines.append(f"**{key}** ({uses} uses)")
                else:
                    equip_lines.append(f"**{key}**")
            else:
                if count > 1:
                    inv_lines.append(f"**{key}** x{count}")
                else:
                    inv_lines.append(f"**{key}**")

        if equip_lines:
            embed.add_field(
                name="🔧 Equipment",
                value="\n".join(equip_lines),
                inline=False,
            )
        if inv_lines:
            embed.add_field(
                name="📦 Items",
                value="\n".join(inv_lines),
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="stash")
    async def stash(self, ctx, *, item_name: str = ""):
        """Move an item to safe storage. Usage: !stash <item> [amount]"""
        if not await require_location(ctx, "noodle_town"):
            return

        if not item_name:
            await ctx.send(
                f"❌ {ctx.author.mention}, specify an item to store!\n"
                f"Usage: `!stash <item>` or `!stash <item> <amount>`"
            )
            return

        # Parse optional amount from the end
        parts = item_name.rsplit(" ", 1)
        amount = 1
        name = item_name
        if len(parts) == 2 and parts[1].isdigit():
            name = parts[0]
            amount = int(parts[1])
            if amount < 1:
                amount = 1

        # Try equipment first
        equip = self.repo.get_user_equipment(ctx.author.id)
        equip_key = _resolve_equip_key(name, equip)

        if equip_key:
            uses = equip.get(equip_key, 0)
            if uses <= 0:
                await ctx.send(f"❌ You don't own **{equip_key}**!")
                return

            # Check if item is currently equipped as combat gear
            stats = self.repo.get_combat_stats(ctx.author.id)
            for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
                if stats.get(slot) == equip_key:
                    self.repo.set_equipped_combat_item(ctx.author.id, slot.replace("equipped_", ""), None)

            # Move to storage
            self.repo.set_equipment(ctx.author.id, equip_key, 0)
            self.repo.add_to_storage(ctx.author.id, equip_key, "equipment", uses)

            label = f"({uses} uses)" if uses > 1 else ""
            await ctx.send(
                f"📦 Stashed **{equip_key}** {label} into safe storage!\n"
                f"It's now immune to all disasters but can't be used until withdrawn."
            )
            return

        # Try inventory items
        inv_items = self.repo.get_inventory_items(ctx.author.id)
        matching = [i for i in inv_items if i["item_key"].lower() == name.lower()]

        if not matching:
            # Try fuzzy match
            matching = [i for i in inv_items if name.lower() in i["item_key"].lower()]

        if not matching:
            await ctx.send(f"❌ No item called **{name}** found in your inventory or equipment!")
            return

        actual_key = matching[0]["item_key"]
        to_stash = min(amount, len(matching))
        ids_to_remove = [m["id"] for m in matching[:to_stash]]

        self.repo.remove_items_by_ids(ctx.author.id, ids_to_remove)
        for _ in range(to_stash):
            self.repo.add_to_storage(ctx.author.id, actual_key, "inventory")

        label = f"x{to_stash}" if to_stash > 1 else ""
        await ctx.send(
            f"📦 Stashed **{actual_key}** {label} into safe storage!\n"
            f"Immune to all disasters but can't be used until withdrawn."
        )

    @commands.command(name="unstash")
    async def unstash(self, ctx, *, item_name: str = ""):
        """Take an item out of safe storage. Usage: !unstash <item> [amount]"""
        if not await require_location(ctx, "noodle_town"):
            return

        if not item_name:
            await ctx.send(
                f"❌ {ctx.author.mention}, specify an item to withdraw!\n"
                f"Usage: `!unstash <item>` or `!unstash <item> <amount>`"
            )
            return

        # Parse optional amount
        parts = item_name.rsplit(" ", 1)
        amount = 1
        name = item_name
        if len(parts) == 2 and parts[1].isdigit():
            name = parts[0]
            amount = int(parts[1])
            if amount < 1:
                amount = 1

        # Find matching items in storage
        stored = self.repo.get_storage_items(ctx.author.id)
        matching = [s for s in stored if s["item_key"].lower() == name.lower()]
        if not matching:
            matching = [s for s in stored if name.lower() in s["item_key"].lower()]

        if not matching:
            await ctx.send(f"❌ No item called **{name}** found in your storage!")
            return

        actual_key = matching[0]["item_key"]
        item_type = matching[0]["item_type"]

        if item_type == "equipment":
            # Equipment: restore to user_equipment
            row = self.repo.remove_from_storage(ctx.author.id, actual_key, "equipment")
            if not row:
                await ctx.send(f"❌ Failed to retrieve **{actual_key}** from storage!")
                return

            uses = row["uses"]
            current_uses = self.repo.get_equipment_uses(ctx.author.id, actual_key)
            self.repo.set_equipment(ctx.author.id, actual_key, current_uses + uses)

            label = f"({uses} uses)" if uses > 1 else ""
            await ctx.send(f"📦 Retrieved **{actual_key}** {label} from storage!")
        else:
            # Inventory items: restore to user_inventory_items
            to_unstash = min(amount, len(matching))
            for i in range(to_unstash):
                removed = self.repo.remove_from_storage(ctx.author.id, actual_key, "inventory")
                if removed:
                    self.repo.add_item(ctx.author.id, actual_key)

            label = f"x{to_unstash}" if to_unstash > 1 else ""
            await ctx.send(f"📦 Retrieved **{actual_key}** {label} from storage!")


def _resolve_equip_key(name: str, equipment: dict) -> str | None:
    """Try to match an equipment key by name."""
    lower = name.lower().replace(" ", "_")
    if lower in equipment:
        return lower
    # Fuzzy match
    for key in equipment:
        if lower in key or key in lower:
            return key
    return None


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(EconomyCog(bot))

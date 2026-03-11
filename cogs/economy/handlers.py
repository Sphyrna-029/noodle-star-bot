"""Economy commands cog."""

from datetime import datetime

import discord
from discord.ext import commands

from cogs.locations.check import require_location
from cogs.economy.use_case import EconomyUseCases
from cogs.shop.resources import RESOURCES, get_resource
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
                f"Use `!stash` in **Noodle Town** to store items safely."
            )
            return

        embed = discord.Embed(
            title="📦 Safe Storage",
            description=(
                "Items here are **100% safe** — immune to disasters, "
                "death penalties, and alien abductions.\n"
                "Use `!unstash` to withdraw items."
            ),
            color=discord.Color.dark_teal(),
        )

        # Group by category
        equip_lines = []
        categories: dict[str, list[str]] = {}

        for row in items:
            key = row["item_key"]
            count = row["count"]
            item_type = row["item_type"]

            if item_type == "equipment":
                uses = row["total_uses"]
                display = _display_name(key)
                if uses > 1:
                    equip_lines.append(f"{_item_emoji(key)} **{display}** ({uses} uses)")
                else:
                    equip_lines.append(f"{_item_emoji(key)} **{display}**")
            else:
                res = get_resource(key)
                cat = res.category if res else "other"
                display = res.display_name if res else _display_name(key)
                emoji = res.emoji if res else "📦"
                line = f"{emoji} **{display}**"
                if count > 1:
                    line += f" x{count}"
                categories.setdefault(cat, []).append(line)

        if equip_lines:
            embed.add_field(
                name="🔧 Equipment",
                value="\n".join(equip_lines),
                inline=False,
            )

        cat_headers = {
            "mineral": "💎 Minerals",
            "fish": "🐟 Fish",
            "ore": "🚀 Space Ores",
            "crop": "🌾 Crops",
            "consumable": "🍼 Consumables",
            "other": "📦 Other",
        }
        for cat_key in ("mineral", "fish", "ore", "crop", "consumable", "other"):
            lines = categories.get(cat_key, [])
            if lines:
                header = cat_headers.get(cat_key, "📦 Items")
                # Truncate long lists
                if len(lines) > 15:
                    shown = lines[:14]
                    shown.append(f"*...and {len(lines) - 14} more*")
                    lines = shown
                embed.add_field(
                    name=header,
                    value="\n".join(lines),
                    inline=False,
                )

        await ctx.send(embed=embed)

    @commands.command(name="stash")
    async def stash(self, ctx, *, item_name: str = ""):
        """Stash items to safe storage. Use !stash for menu or !stash <item> [amount]."""
        if not await require_location(ctx, "noodle_town"):
            return

        # No args — show category dropdown menu
        if not item_name:
            return await self._stash_menu(ctx)

        # Parse optional amount from the end
        parts = item_name.rsplit(" ", 1)
        amount = 1
        name = item_name
        if len(parts) == 2 and parts[1].isdigit():
            name = parts[0]
            amount = int(parts[1])
            if amount < 1:
                amount = 1

        # "all" keyword — stash everything
        if name.lower() == "all":
            return await self._stash_category(ctx, "all")

        # Category keyword
        cat_map = {
            "minerals": "mineral", "mineral": "mineral",
            "fish": "fish", "fishes": "fish",
            "ores": "ore", "ore": "ore", "space": "ore",
            "crops": "crop", "crop": "crop",
            "consumables": "consumable", "consumable": "consumable",
        }
        if name.lower() in cat_map:
            return await self._stash_category(ctx, cat_map[name.lower()])

        # Try equipment first
        equip = self.repo.get_user_equipment(ctx.author.id)
        equip_key = _resolve_equip_key(name, equip)

        if equip_key:
            uses = equip.get(equip_key, 0)
            if uses <= 0:
                await ctx.send(f"❌ You don't own **{_display_name(equip_key)}**!")
                return

            stats = self.repo.get_combat_stats(ctx.author.id)
            for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
                if stats.get(slot) == equip_key:
                    self.repo.set_equipped_combat_item(ctx.author.id, slot.replace("equipped_", ""), None)

            self.repo.set_equipment(ctx.author.id, equip_key, 0)
            self.repo.add_to_storage(ctx.author.id, equip_key, "equipment", uses)

            display = _display_name(equip_key)
            label = f"({uses} uses)" if uses > 1 else ""
            await ctx.send(f"📦 Stashed **{display}** {label} into safe storage!")
            return

        # Try inventory items
        inv_items = self.repo.get_inventory_items(ctx.author.id)
        norm = name.lower().replace(" ", "_")
        matching = [i for i in inv_items if i["item_key"] == norm]
        if not matching:
            matching = [i for i in inv_items if i["item_key"].lower() == name.lower()]
        if not matching:
            matching = [i for i in inv_items if norm in i["item_key"].lower()]

        if not matching:
            await ctx.send(f"❌ No item called **{name}** found in your inventory or equipment!")
            return

        actual_key = matching[0]["item_key"]
        to_stash = min(amount, len(matching))
        ids_to_remove = [m["id"] for m in matching[:to_stash]]

        self.repo.remove_items_by_ids(ctx.author.id, ids_to_remove)
        bulk = [(actual_key, "inventory", 1) for _ in range(to_stash)]
        self.repo.add_to_storage_bulk(ctx.author.id, bulk)

        display = _display_name(actual_key)
        label = f"x{to_stash}" if to_stash > 1 else ""
        await ctx.send(f"📦 Stashed **{display}** {label} into safe storage!")

    async def _stash_menu(self, ctx):
        """Show the stash category dropdown menu."""
        inv_items = self.repo.get_inventory_items(ctx.author.id)
        equip = self.repo.get_user_equipment(ctx.author.id)

        # Count items by category
        cat_counts: dict[str, int] = {}
        total = 0
        for item in inv_items:
            res = get_resource(item["item_key"])
            cat = res.category if res else "other"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            total += 1

        # Count equipment
        equip_count = sum(1 for v in equip.values() if v and v > 0)

        if total == 0 and equip_count == 0:
            await ctx.send(f"❌ {ctx.author.mention}, your inventory is empty — nothing to stash!")
            return

        options = []
        if total > 0:
            options.append(discord.SelectOption(
                label=f"All Items ({total})",
                value="all",
                emoji="📦",
                description=f"Stash all {total} items at once",
            ))

        cat_info = [
            ("mineral", "💎", "Minerals"),
            ("fish", "🐟", "Fish"),
            ("ore", "🚀", "Space Ores"),
            ("crop", "🌾", "Crops"),
            ("consumable", "🍼", "Consumables"),
        ]
        for cat_key, emoji, label in cat_info:
            count = cat_counts.get(cat_key, 0)
            if count > 0:
                options.append(discord.SelectOption(
                    label=f"{label} ({count})",
                    value=cat_key,
                    emoji=emoji,
                    description=f"Stash all {count} {label.lower()}",
                ))

        if equip_count > 0:
            options.append(discord.SelectOption(
                label=f"Equipment ({equip_count})",
                value="equipment",
                emoji="🔧",
                description=f"Stash all {equip_count} equipment pieces",
            ))

        if not options:
            await ctx.send(f"❌ {ctx.author.mention}, nothing to stash!")
            return

        embed = discord.Embed(
            title="📦 Stash Items",
            description=(
                "Select a category to stash **all items** of that type.\n"
                "Or use `!stash <item> [amount]` for individual items."
            ),
            color=discord.Color.dark_teal(),
        )

        view = _StashView(ctx.author.id, self.repo, options)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    async def _stash_category(self, ctx, category: str):
        """Stash all items of a category."""
        inv_items = self.repo.get_inventory_items(ctx.author.id)

        if category == "all":
            matching = inv_items
        else:
            matching = []
            for item in inv_items:
                res = get_resource(item["item_key"])
                cat = res.category if res else "other"
                if cat == category:
                    matching.append(item)

        if not matching:
            await ctx.send(f"❌ No {category} items in your inventory!")
            return

        ids = [m["id"] for m in matching]
        self.repo.remove_items_by_ids(ctx.author.id, ids)
        bulk = [(m["item_key"], "inventory", 1) for m in matching]
        self.repo.add_to_storage_bulk(ctx.author.id, bulk)

        cat_labels = {
            "mineral": "minerals", "fish": "fish", "ore": "space ores",
            "crop": "crops", "consumable": "consumables", "all": "items",
        }
        label = cat_labels.get(category, "items")
        await ctx.send(f"📦 Stashed **{len(matching)}** {label} into safe storage!")

    @commands.command(name="unstash")
    async def unstash(self, ctx, *, item_name: str = ""):
        """Withdraw items from storage. Use !unstash for menu or !unstash <item> [amount]."""
        if not await require_location(ctx, "noodle_town"):
            return

        # No args — show category dropdown menu
        if not item_name:
            return await self._unstash_menu(ctx)

        # Parse optional amount
        parts = item_name.rsplit(" ", 1)
        amount = 1
        name = item_name
        if len(parts) == 2 and parts[1].isdigit():
            name = parts[0]
            amount = int(parts[1])
            if amount < 1:
                amount = 1

        # "all" keyword
        if name.lower() == "all":
            return await self._unstash_category(ctx, "all")

        # Category keyword
        cat_map = {
            "minerals": "mineral", "mineral": "mineral",
            "fish": "fish", "fishes": "fish",
            "ores": "ore", "ore": "ore", "space": "ore",
            "crops": "crop", "crop": "crop",
            "consumables": "consumable", "consumable": "consumable",
            "equipment": "equipment",
        }
        if name.lower() in cat_map:
            return await self._unstash_category(ctx, cat_map[name.lower()])

        # Find matching items in storage
        stored = self.repo.get_storage_items(ctx.author.id)
        norm = name.lower().replace(" ", "_")
        matching = [s for s in stored if s["item_key"] == norm]
        if not matching:
            matching = [s for s in stored if s["item_key"].lower() == name.lower()]
        if not matching:
            matching = [s for s in stored if norm in s["item_key"].lower()]

        if not matching:
            await ctx.send(f"❌ No item called **{name}** found in your storage!")
            return

        actual_key = matching[0]["item_key"]
        item_type = matching[0]["item_type"]

        if item_type == "equipment":
            row = self.repo.remove_from_storage(ctx.author.id, actual_key, "equipment")
            if not row:
                await ctx.send(f"❌ Failed to retrieve **{_display_name(actual_key)}** from storage!")
                return

            uses = row["uses"]
            current_uses = self.repo.get_equipment_uses(ctx.author.id, actual_key)
            self.repo.set_equipment(ctx.author.id, actual_key, current_uses + uses)

            display = _display_name(actual_key)
            label = f"({uses} uses)" if uses > 1 else ""
            await ctx.send(f"📦 Retrieved **{display}** {label} from storage!")
        else:
            # Check inventory space before removing from storage
            bag_count = self.repo.get_inventory_count(ctx.author.id)
            bag_capacity = self.repo.get_inventory_capacity(ctx.author.id)
            available = bag_capacity - bag_count
            if available <= 0:
                await ctx.send(f"❌ {ctx.author.mention}, your inventory is full ({bag_count}/{bag_capacity})! Make room before unstashing.")
                return
            to_unstash = min(amount, len(matching), available)
            removed = self.repo.remove_from_storage_by_key(
                ctx.author.id, actual_key, "inventory", to_unstash
            )
            for _ in removed:
                self.repo.add_item(ctx.author.id, actual_key)

            display = _display_name(actual_key)
            label = f"x{len(removed)}" if len(removed) > 1 else ""
            await ctx.send(f"📦 Retrieved **{display}** {label} from storage!")

    async def _unstash_menu(self, ctx):
        """Show the unstash category dropdown menu."""
        stored = self.repo.get_storage_summary(ctx.author.id)

        if not stored:
            await ctx.send(f"📦 {ctx.author.mention}, your storage is empty!")
            return

        # Count by category
        cat_counts: dict[str, int] = {}
        equip_count = 0
        total = 0
        for row in stored:
            if row["item_type"] == "equipment":
                equip_count += row["count"]
            else:
                res = get_resource(row["item_key"])
                cat = res.category if res else "other"
                cat_counts[cat] = cat_counts.get(cat, 0) + row["count"]
            total += row["count"]

        options = []
        if total > 0:
            options.append(discord.SelectOption(
                label=f"All Items ({total})",
                value="all",
                emoji="📦",
                description=f"Withdraw all {total} items at once",
            ))

        cat_info = [
            ("mineral", "💎", "Minerals"),
            ("fish", "🐟", "Fish"),
            ("ore", "🚀", "Space Ores"),
            ("crop", "🌾", "Crops"),
            ("consumable", "🍼", "Consumables"),
        ]
        for cat_key, emoji, label in cat_info:
            count = cat_counts.get(cat_key, 0)
            if count > 0:
                options.append(discord.SelectOption(
                    label=f"{label} ({count})",
                    value=cat_key,
                    emoji=emoji,
                    description=f"Withdraw all {count} {label.lower()}",
                ))

        if equip_count > 0:
            options.append(discord.SelectOption(
                label=f"Equipment ({equip_count})",
                value="equipment",
                emoji="🔧",
                description=f"Withdraw all {equip_count} equipment pieces",
            ))

        if not options:
            await ctx.send(f"📦 {ctx.author.mention}, your storage is empty!")
            return

        embed = discord.Embed(
            title="📦 Withdraw from Storage",
            description=(
                "Select a category to withdraw **all items** of that type.\n"
                "Or use `!unstash <item> [amount]` for individual items."
            ),
            color=discord.Color.dark_teal(),
        )

        view = _UnstashView(ctx.author.id, self.repo, options)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    async def _unstash_category(self, ctx, category: str):
        """Unstash all items of a category."""
        if category == "equipment":
            return await self._unstash_all_equipment(ctx)

        stored = self.repo.get_storage_items(ctx.author.id)

        if category == "all":
            # All inventory items
            inv_items = [s for s in stored if s["item_type"] == "inventory"]
            equip_items = [s for s in stored if s["item_type"] == "equipment"]
            # Unstash inventory items (limited by available space)
            if inv_items:
                bag_count = self.repo.get_inventory_count(ctx.author.id)
                bag_capacity = self.repo.get_inventory_capacity(ctx.author.id)
                available = bag_capacity - bag_count
                if available <= 0 and not equip_items:
                    await ctx.send(f"❌ {ctx.author.mention}, your inventory is full! Make room before unstashing.")
                    return
                keys_to_remove = set()
                for item in inv_items:
                    keys_to_remove.add(item["item_key"])
                removed = self.repo.remove_from_storage_by_category(
                    ctx.author.id, keys_to_remove
                )
                # Only add items up to available space
                added = 0
                leftover = []
                for row in removed:
                    if added < available:
                        self.repo.add_item(ctx.author.id, row["item_key"])
                        added += 1
                    else:
                        leftover.append(row)
                # Put back items that didn't fit
                if leftover:
                    self.repo.add_to_storage_bulk(
                        ctx.author.id,
                        [(r["item_key"], r["item_type"], r["uses"]) for r in leftover],
                    )
            # Unstash equipment
            for item in equip_items:
                row = self.repo.remove_from_storage(
                    ctx.author.id, item["item_key"], "equipment"
                )
                if row:
                    current = self.repo.get_equipment_uses(ctx.author.id, item["item_key"])
                    self.repo.set_equipment(ctx.author.id, item["item_key"], current + row["uses"])
            inv_retrieved = added if inv_items else 0
            total = inv_retrieved + len(equip_items)
            if total == 0:
                await ctx.send("❌ Your storage is empty!")
                return
            msg = f"📦 Retrieved **{total}** items from storage!"
            if leftover:
                msg += f" ({len(leftover)} left in storage — inventory full)"
            await ctx.send(msg)
            return

        # Specific category
        cat_keys = set()
        for key, res in RESOURCES.items():
            if res.category == category:
                cat_keys.add(key)

        removed = self.repo.remove_from_storage_by_category(ctx.author.id, cat_keys)
        if not removed:
            await ctx.send(f"❌ No {category} items in your storage!")
            return

        # Only add items up to available inventory space
        bag_count = self.repo.get_inventory_count(ctx.author.id)
        bag_capacity = self.repo.get_inventory_capacity(ctx.author.id)
        available = bag_capacity - bag_count
        added = 0
        leftover = []
        for row in removed:
            if added < available:
                self.repo.add_item(ctx.author.id, row["item_key"])
                added += 1
            else:
                leftover.append(row)
        # Put back items that didn't fit
        if leftover:
            self.repo.add_to_storage_bulk(
                ctx.author.id,
                [(r["item_key"], r["item_type"], r["uses"]) for r in leftover],
            )

        cat_labels = {
            "mineral": "minerals", "fish": "fish", "ore": "space ores",
            "crop": "crops", "consumable": "consumables",
        }
        label = cat_labels.get(category, "items")
        msg = f"📦 Retrieved **{added}** {label} from storage!"
        if leftover:
            msg += f" ({len(leftover)} left in storage — inventory full)"
        await ctx.send(msg)

    async def _unstash_all_equipment(self, ctx):
        """Unstash all equipment from storage."""
        stored = self.repo.get_storage_items(ctx.author.id)
        equip_items = [s for s in stored if s["item_type"] == "equipment"]

        if not equip_items:
            await ctx.send("❌ No equipment in your storage!")
            return

        for item in equip_items:
            row = self.repo.remove_from_storage(
                ctx.author.id, item["item_key"], "equipment"
            )
            if row:
                current = self.repo.get_equipment_uses(ctx.author.id, item["item_key"])
                self.repo.set_equipment(ctx.author.id, item["item_key"], current + row["uses"])

        await ctx.send(f"📦 Retrieved **{len(equip_items)}** equipment pieces from storage!")


# ---------------------------------------------------------------------------
# Stash / Unstash Views
# ---------------------------------------------------------------------------

class _StashSelect(discord.ui.Select):
    """Dropdown for selecting a category to stash."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="📦 Select category to stash...", options=options)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, _StashView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return

        category = self.values[0]
        repo = view.repo
        user_id = view.author_id

        if category == "equipment":
            # Stash all equipment
            equip = repo.get_user_equipment(user_id)
            stats = repo.get_combat_stats(user_id)
            count = 0
            for key, uses in equip.items():
                if uses and uses > 0:
                    # Unequip if needed
                    for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
                        if stats.get(slot) == key:
                            repo.set_equipped_combat_item(user_id, slot.replace("equipped_", ""), None)
                    repo.set_equipment(user_id, key, 0)
                    repo.add_to_storage(user_id, key, "equipment", uses)
                    count += 1
            if count == 0:
                await interaction.response.send_message("❌ No equipment to stash!", ephemeral=True)
                return
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="📦 Stashed!",
                    description=f"Moved **{count}** equipment pieces to safe storage.",
                    color=discord.Color.green(),
                ),
                view=None,
            )
            return

        # Inventory category
        inv_items = repo.get_inventory_items(user_id)
        if category == "all":
            matching = inv_items
        else:
            matching = []
            for item in inv_items:
                res = get_resource(item["item_key"])
                cat = res.category if res else "other"
                if cat == category:
                    matching.append(item)

        if not matching:
            await interaction.response.send_message("❌ No items of that type!", ephemeral=True)
            return

        ids = [m["id"] for m in matching]
        repo.remove_items_by_ids(user_id, ids)
        bulk = [(m["item_key"], "inventory", 1) for m in matching]
        repo.add_to_storage_bulk(user_id, bulk)

        cat_labels = {
            "mineral": "minerals", "fish": "fish", "ore": "space ores",
            "crop": "crops", "consumable": "consumables", "all": "items",
        }
        label = cat_labels.get(category, "items")
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="📦 Stashed!",
                description=f"Moved **{len(matching)}** {label} to safe storage.",
                color=discord.Color.green(),
            ),
            view=None,
        )


class _StashView(discord.ui.View):
    def __init__(self, author_id: int, repo, options: list[discord.SelectOption], timeout: float = 60):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.repo = repo
        self.message = None
        self.add_item(_StashSelect(options))

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except Exception:
                pass


class _UnstashSelect(discord.ui.Select):
    """Dropdown for selecting a category to unstash."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="📦 Select category to withdraw...", options=options)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, _UnstashView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return

        category = self.values[0]
        repo = view.repo
        user_id = view.author_id

        if category == "equipment":
            stored = repo.get_storage_items(user_id)
            equip_items = [s for s in stored if s["item_type"] == "equipment"]
            if not equip_items:
                await interaction.response.send_message("❌ No equipment in storage!", ephemeral=True)
                return
            for item in equip_items:
                row = repo.remove_from_storage(user_id, item["item_key"], "equipment")
                if row:
                    current = repo.get_equipment_uses(user_id, item["item_key"])
                    repo.set_equipment(user_id, item["item_key"], current + row["uses"])
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="📦 Retrieved!",
                    description=f"Withdrew **{len(equip_items)}** equipment pieces from storage.",
                    color=discord.Color.green(),
                ),
                view=None,
            )
            return

        if category == "all":
            stored = repo.get_storage_items(user_id)
            inv_items = [s for s in stored if s["item_type"] == "inventory"]
            equip_items = [s for s in stored if s["item_type"] == "equipment"]
            inv_added = 0
            inv_leftover = []
            if inv_items:
                bag_count = repo.get_inventory_count(user_id)
                bag_capacity = repo.get_inventory_capacity(user_id)
                available = bag_capacity - bag_count
                keys = {item["item_key"] for item in inv_items}
                removed = repo.remove_from_storage_by_category(user_id, keys)
                for row in removed:
                    if inv_added < available:
                        repo.add_item(user_id, row["item_key"])
                        inv_added += 1
                    else:
                        inv_leftover.append(row)
                if inv_leftover:
                    repo.add_to_storage_bulk(
                        user_id,
                        [(r["item_key"], r["item_type"], r["uses"]) for r in inv_leftover],
                    )
            for item in equip_items:
                row = repo.remove_from_storage(user_id, item["item_key"], "equipment")
                if row:
                    current = repo.get_equipment_uses(user_id, item["item_key"])
                    repo.set_equipment(user_id, item["item_key"], current + row["uses"])
            total = inv_added + len(equip_items)
            desc = f"Withdrew **{total}** items from storage."
            if inv_leftover:
                desc += f" ({len(inv_leftover)} left in storage — inventory full)"
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="📦 Retrieved!",
                    description=desc,
                    color=discord.Color.green(),
                ),
                view=None,
            )
            return

        # Specific category
        cat_keys = set()
        for key, res in RESOURCES.items():
            if res.category == category:
                cat_keys.add(key)

        removed = repo.remove_from_storage_by_category(user_id, cat_keys)
        if not removed:
            await interaction.response.send_message("❌ No items of that type in storage!", ephemeral=True)
            return

        bag_count = repo.get_inventory_count(user_id)
        bag_capacity = repo.get_inventory_capacity(user_id)
        available = bag_capacity - bag_count
        added = 0
        leftover = []
        for row in removed:
            if added < available:
                repo.add_item(user_id, row["item_key"])
                added += 1
            else:
                leftover.append(row)
        if leftover:
            repo.add_to_storage_bulk(
                user_id,
                [(r["item_key"], r["item_type"], r["uses"]) for r in leftover],
            )

        cat_labels = {
            "mineral": "minerals", "fish": "fish", "ore": "space ores",
            "crop": "crops", "consumable": "consumables",
        }
        label = cat_labels.get(category, "items")
        desc = f"Withdrew **{added}** {label} from storage."
        if leftover:
            desc += f" ({len(leftover)} left in storage — inventory full)"
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="📦 Retrieved!",
                description=desc,
                color=discord.Color.green(),
            ),
            view=None,
        )


class _UnstashView(discord.ui.View):
    def __init__(self, author_id: int, repo, options: list[discord.SelectOption], timeout: float = 60):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.repo = repo
        self.message = None
        self.add_item(_UnstashSelect(options))

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _display_name(key: str) -> str:
    """Get display name for an item key."""
    res = get_resource(key)
    if res:
        return res.display_name
    return key.replace("_", " ").title()


def _item_emoji(key: str) -> str:
    """Get emoji for an item key."""
    res = get_resource(key)
    return res.emoji if res else "🔧"


def _resolve_equip_key(name: str, equipment: dict) -> str | None:
    """Try to match an equipment key by name."""
    lower = name.lower().replace(" ", "_")
    if lower in equipment:
        return lower
    for key in equipment:
        if lower in key or key in lower:
            return key
    return None


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(EconomyCog(bot))

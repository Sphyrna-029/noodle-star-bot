"""Farming commands cog."""

import discord
from discord.ext import commands

from cogs.farming.constants import (
    FARM_LEVEL_UPGRADE_COSTS,
    MAX_FARM_LEVEL,
    MAX_PLOTS,
    PLOT_COSTS,
    PRESERVER_PROCESSING_HOURS_BY_LEVEL,
    get_crop_by_name,
)
from cogs.farming.use_case import FarmingUseCases


class FarmingCog(commands.Cog):
    """Commands for the farming minigame."""

    def __init__(self, bot):
        self.bot = bot
        self.farming = FarmingUseCases()

    @commands.group(name="farm", invoke_without_command=True)
    async def farm(self, ctx):
        """View your farm and planted crops."""
        status = self.farming.get_farm_status(ctx.author.id, str(ctx.author))

        if status.total_plots == 0:
            embed = discord.Embed(
                title="🏡 Your Farm",
                description=(
                    f"{ctx.author.mention}, you don't own any farm plots yet!\n\n"
                    f"```\n"
                    f"┌─────────────────────┐\n"
                    f"│                     │\n"
                    f"│    🌾 No Plots!     │\n"
                    f"│                     │\n"
                    f"│  Buy your first     │\n"
                    f"│  plot to start      │\n"
                    f"│  farming!           │\n"
                    f"│                     │\n"
                    f"└─────────────────────┘\n"
                    f"```\n"
                    f"Use `!buyplot` for **{PLOT_COSTS.get(1, 300)}** ⭐"
                ),
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
            return

        # Build the cute grid display - simple square grid (3 columns)
        grid_lines = []
        grid_lines.append("```")

        # Pad plots list to always show owned plots in one grid
        plots_to_show = status.plots[:]
        plots_per_row = 3

        # Calculate total rows needed
        num_rows = (len(plots_to_show) + plots_per_row - 1) // plots_per_row

        for row in range(num_rows):
            start_idx = row * plots_per_row
            end_idx = min(start_idx + plots_per_row, len(plots_to_show))
            row_plots = plots_to_show[start_idx:end_idx]

            # Top border
            if len(row_plots) == 1:
                grid_lines.append("┌───┐")
            else:
                grid_lines.append("┌" + "───┬" * (len(row_plots) - 1) + "───┐")

            # Plot cells with emojis
            cells = []
            for plot in row_plots:
                if plot.is_empty:
                    cells.append(" . ")
                #elif plot.is_ready:
                #    cells.append(f"{plot.crop_emoji}✨")
                else:
                    cells.append(" * ")
            grid_lines.append("│" + "│".join(cells) + "│")

            # Bottom border
            if len(row_plots) == 1:
                grid_lines.append("└───┘")
            else:
                grid_lines.append("└" + "───┴" * (len(row_plots) - 1) + "───┘")

            # Plot details below each row
            for plot in row_plots:
                if plot.is_empty:
                    grid_lines.append(f"Plot {plot.plot_number}: Empty • Soil {plot.soil_condition}%")
                #elif plot.is_ready:
                #    grid_lines.append(f"Plot {plot.plot_number}: {plot.crop_name} - ✨ READY!")
                else:
                    seconds = plot.time_remaining_seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    if hours > 0:
                        time_str = f"{hours}h {minutes}m"
                    else:
                        time_str = f"{minutes}m"
                    streak = f" • streak x{plot.same_crop_streak}" if plot.same_crop_streak > 1 else ""
                    grid_lines.append(
                        f"Plot {plot.plot_number}: {plot.crop_emoji} {plot.crop_name} - {time_str} remaining"
                        f" • Soil {plot.soil_condition}%{streak}"
                    )

            # Add spacing between rows if not the last row
            if row < num_rows - 1:
                grid_lines.append("")

        grid_lines.append("```")

        # Build legend for ready crops
        ready_count = sum(1 for p in status.plots if p.is_ready)
        empty_count = sum(1 for p in status.plots if p.is_empty)
        growing_count = sum(1 for p in status.plots if not p.is_empty and not p.is_ready)

        legend = []
        if ready_count > 0:
            legend.append(f"✨ **{ready_count}** ready to harvest!")
        if growing_count > 0:
            legend.append(f"🌱 **{growing_count}** growing")
        if empty_count > 0:
            legend.append(f"🟫 **{empty_count}** empty")

        embed = discord.Embed(
            title="🏡 Your Farm",
            description="\n".join(grid_lines),
            color=discord.Color.green(),
        )

        if legend:
            embed.add_field(name="Status", value=" • ".join(legend), inline=False)

        next_level = status.farm_level + 1
        if status.next_farm_level_cost is not None:
            embed.add_field(
                name="Farm Level",
                value=(
                    f"🌱 Level **{status.farm_level}**\n"
                    f"⬆️ Upgrade to level **{next_level}** for **{status.next_farm_level_cost}⭐** with `!upgradefarm`"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name="Farm Level",
                value=f"🌟 Level **{status.farm_level}** (MAX)",
                inline=False,
            )
        if status.preserver_owned:
            preserver_next = (
                f"⬆️ Upgrade to Preserver level **{status.preserver_level + 1}** for **{status.preserver_next_cost}⭐** with `!farm preserver upgrade`"
                if status.preserver_next_cost is not None else
                "🌟 Preserver is max level."
            )
            ready_text = (
                f"⏳ Ready in **{status.preserver_ready_in_seconds // 3600}h {(status.preserver_ready_in_seconds % 3600) // 60}m**"
                if status.preserver_pending_stars > 0 and status.preserver_ready_in_seconds > 0 else
                ("✅ Ready to collect with `!farm preserver collect`" if status.preserver_pending_stars > 0 else "📦 No processed stars queued")
            )
            preserver_value = (
                f"🏭 Level **{status.preserver_level}**\n"
                f"💰 Pending: **{status.preserver_pending_stars}⭐**\n"
                "🧪 Start processing with `!farm preserver start`\n"
                f"{ready_text}\n"
                f"{preserver_next}"
            )
        else:
            preserver_value = "🔒 Locked\nBuy **Preserver** from `!store` to unlock melon processing."
        embed.add_field(
            name="Preserver",
            value=preserver_value,
            inline=False,
        )
        if status.growbot_owned:
            growbot_value = (
                f"🤖 Level **{status.growbot_level}**\n"
                f"Use `!farm growbot harvest`, `!farm growbot tend <fertilizer|water>`, "
                f"or `!farm growbot plant <crop>`"
            )
        else:
            growbot_value = "🔒 Locked\nBuy **Grow-Bot 3000** from `!store` to unlock farm automation."
        embed.add_field(
            name="GrowBot",
            value=growbot_value,
            inline=False,
        )

        # Add footer with next plot info
        if status.can_buy_more and status.next_plot_cost:
            embed.set_footer(
                text=(
                    f"💰 Next plot: {status.next_plot_cost}⭐ • !upgradefarm • !farm preserver upgrade "
                    "• !harvest <plot> • !farm growbot harvest"
                )
            )
        elif not status.can_buy_more:
            embed.set_footer(
                text=(
                    f"🌟 Maximum plots reached ({MAX_PLOTS}) • !upgradefarm • !farm preserver upgrade "
                    "• !harvest <plot> • !farm growbot harvest"
                )
            )

        await ctx.send(embed=embed)

    @commands.command(name="buyplot")
    async def buyplot(self, ctx, plot_number: int = 0):
        """Buy a new farm plot. Usage: !buyplot <plot_number>"""
        # If no plot number specified, show plot status
        if plot_number == 0:
            status = self.farming.get_farm_status(ctx.author.id, str(ctx.author))

            embed = discord.Embed(
                title="🏡 Farm Plot Status",
                description="Use `!buyplot <number>` to purchase a specific plot.",
                color=discord.Color.gold(),
            )

            # Show all plots (owned and available)
            plot_lines = []
            for i in range(1, MAX_PLOTS + 1):
                if i <= status.total_plots:
                    plot_lines.append(f"✅ **Plot {i}**: Owned")
                else:
                    cost = PLOT_COSTS.get(i, 0)
                    plot_lines.append(f"🔒 **Plot {i}**: Available for **{cost}⭐**")

            embed.add_field(
                name="Your Plots",
                value="\n".join(plot_lines),
                inline=False,
            )

            embed.add_field(
                name="Your Balance",
                value=f"💰 **{status.stars}⭐**",
                inline=False,
            )

            if status.can_buy_more:
                embed.set_footer(text=f"💡 Example: !buyplot {status.total_plots + 1}")
            else:
                embed.set_footer(text="🌟 You own all plots!")

            await ctx.send(embed=embed)
            return

        # Actually buy the plot
        result = self.farming.buy_plot(ctx.author.id, str(ctx.author), plot_number)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"🌱 {ctx.author.mention} bought **Plot #{result.plot_number}** for **{result.cost}** stars!\n"
            f"💰 New balance: **{result.new_balance}** stars\n\n"
            f"Plant something with `!plant <crop> {result.plot_number}`"
        )

    @commands.command(name="plant")
    async def plant(self, ctx, crop: str = "", plot: int = 0):
        """Plant a crop in a specific plot. Usage: !plant <crop> <plot_number>"""
        if not crop:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify a crop and plot number!\n"
                f"Usage: `!plant <crop> <plot_number>`\n"
                f"Example: `!plant wheat 1`\n"
                f"See available crops with `!crops`"
            )
            return

        if plot == 0:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify a plot number!\n"
                f"Usage: `!plant {crop} <plot_number>`\n"
                f"Example: `!plant {crop} 1`"
            )
            return

        result = self.farming.plant_crop(ctx.author.id, str(ctx.author), crop, plot)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Format ready time
        if result.ready_at:
            hours = (result.ready_at - __import__("datetime").datetime.now()).total_seconds() // 3600
            if hours >= 1:
                time_str = f"{int(hours)} hour(s)"
            else:
                minutes = int((result.ready_at - __import__("datetime").datetime.now()).total_seconds() // 60)
                time_str = f"{minutes} minute(s)"
        else:
            time_str = "soon"

        await ctx.send(
            f"🌱 {ctx.author.mention} planted {result.crop_emoji} **{result.crop_name}** in Plot #{result.plot_number}!\n"
            f"💰 Seed cost: **{result.seed_cost}** stars (Balance: **{result.new_balance}** stars)\n"
            f"⏰ Ready in **{time_str}**"
        )

    @commands.command(name="farmlevel")
    async def farmlevel(self, ctx):
        """View your current farm level and next upgrade cost."""
        level, next_cost, stars = self.farming.get_farm_level_info(ctx.author.id, str(ctx.author))

        embed = discord.Embed(
            title="🌱 Farm Level",
            color=discord.Color.green(),
            description=f"{ctx.author.mention}, your farm is currently **Level {level}**.",
        )
        if next_cost is None:
            embed.add_field(name="Status", value=f"🌟 Max level reached (**{MAX_FARM_LEVEL}**).", inline=False)
        else:
            embed.add_field(
                name="Next Upgrade",
                value=(
                    f"Level **{level + 1}** costs **{next_cost}⭐**.\n"
                    f"Use `!upgradefarm` to upgrade."
                ),
                inline=False,
            )
        embed.add_field(
            name="Quality Notes",
            value=(
                "Bad quality is always possible (even at high levels), but upgrades improve odds.\n"
                "Soil condition also affects quality and payout."
            ),
            inline=False,
        )
        embed.add_field(name="Your Balance", value=f"💰 **{stars}⭐**", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="upgradefarm", aliases=["farmupgrade"])
    async def upgradefarm(self, ctx):
        """Upgrade your farm level to improve harvest quality odds."""
        result = self.farming.upgrade_farm_level(ctx.author.id, str(ctx.author))
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        quality_preview = {
            1: "Bad 20% • Normal 60% • Great 20%",
            2: "Bad 16% • Normal 60% • Great 24%",
            3: "Bad 12% • Normal 58% • Great 30%",
            4: "Bad 8% • Normal 56% • Great 36%",
            5: "Bad 5% • Normal 50% • Great 45%",
        }.get(result.new_level, "Bad ? • Normal ? • Great ?")

        next_cost = FARM_LEVEL_UPGRADE_COSTS.get(result.new_level + 1)
        next_line = (
            f"\n⬆️ Next upgrade: **{next_cost}⭐**"
            if next_cost is not None else
            "\n🌟 You reached max farm level."
        )

        await ctx.send(
            f"✅ {ctx.author.mention}, {result.message}\n"
            f"💸 Cost: **{result.cost}⭐**\n"
            f"💰 New balance: **{result.new_balance}⭐**\n"
            f"🎲 Quality odds: {quality_preview}"
            f"{next_line}"
        )

    @farm.group(name="preserver", invoke_without_command=True)
    async def farm_preserver(self, ctx):
        """View your Preserver machine status."""
        owned, level, next_cost, pending, ready_in = self.farming.get_preserver_info(ctx.author.id, str(ctx.author))
        if not owned:
            await ctx.send(
                f"🏭 {ctx.author.mention}, your Preserver is locked.\n"
                f"Buy it once from `!store` to unlock crop processing and preserving."
            )
            return
        processing_hours = PRESERVER_PROCESSING_HOURS_BY_LEVEL.get(level, 6)
        processing_text = f"⏱️ Processing time: **{processing_hours}h**"
        ready_text = (
            f"⏳ Ready in **{ready_in // 3600}h {(ready_in % 3600) // 60}m**"
            if pending > 0 and ready_in > 0 else
            ("✅ Ready to collect with `!farm preserver collect`" if pending > 0 else "📦 No processed stars queued")
        )
        next_text = (
            f"⬆️ Next level costs **{next_cost}⭐** with `!farm preserver upgrade`"
            if next_cost is not None else
            "🌟 Preserver is max level."
        )
        await ctx.send(
            f"🏭 {ctx.author.mention}'s Preserver\n"
            f"Level: **{level}**\n"
            f"Pending: **{pending}⭐**\n"
            "Start processing: `!farm preserver start`\n"
            f"{processing_text}\n"
            f"{ready_text}\n"
            f"{next_text}"
        )

    @farm_preserver.command(name="upgrade")
    async def farm_preserver_upgrade(self, ctx):
        """Upgrade your Preserver machine."""
        result = self.farming.upgrade_preserver(ctx.author.id, str(ctx.author))
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return
        await ctx.send(
            f"✅ {ctx.author.mention}, {result.message}\n"
            f"💸 Cost: **{result.cost}⭐**\n"
            f"💰 New balance: **{result.new_balance}⭐**"
        )

    @farm_preserver.command(name="start")
    async def farm_preserver_start(self, ctx):
        """Start Preserver processing for ready preservable crops."""
        result = self.farming.start_preserver(ctx.author.id, str(ctx.author))
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        lines = [
            f"🏭 {ctx.author.mention} started the Preserver!",
            f"🍉 Preserved **{len(result.preserved)}** crop(s)",
            f"💰 Queued: **{result.total_queued}⭐**",
            f"📦 Pending total: **{result.pending_stars}⭐**",
        ]
        if result.ready_in_seconds > 0:
            hours = result.ready_in_seconds // 3600
            minutes = (result.ready_in_seconds % 3600) // 60
            lines.append(f"⏳ Ready in **{hours}h {minutes}m**")
        await ctx.send("\n".join(lines))

    @farm_preserver.command(name="collect")
    async def farm_preserver_collect(self, ctx):
        """Collect finished stars from your Preserver."""
        result = self.farming.collect_preserver(ctx.author.id, str(ctx.author))
        if not result.success:
            if result.ready_in_seconds > 0:
                hours = result.ready_in_seconds // 3600
                minutes = (result.ready_in_seconds % 3600) // 60
                await ctx.send(
                    f"❌ {ctx.author.mention}, Preserver still processing. Ready in **{hours}h {minutes}m**."
                )
            else:
                await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return
        await ctx.send(
            f"✅ {ctx.author.mention} collected **{result.collected_stars}⭐** from the Preserver!\n"
            f"💰 New balance: **{result.new_balance}⭐**"
        )

    @farm.group(name="growbot", invoke_without_command=True)
    async def farm_growbot(self, ctx):
        """View GrowBot status and commands."""
        status = self.farming.get_farm_status(ctx.author.id, str(ctx.author))
        if not status.growbot_owned:
            await ctx.send(
                f"🤖 {ctx.author.mention}, your GrowBot is locked.\n"
                f"Buy **Grow-Bot 3000** from `!store` for **2500⭐** to unlock it."
            )
            return
        await ctx.send(
            f"🤖 {ctx.author.mention}'s GrowBot\n"
            f"Level: **{status.growbot_level}**\n"
            "Commands:\n"
            "`!farm growbot harvest` — Harvest all ready crops\n"
            "`!farm growbot tend <fertilizer|water>` — Tend multiple plots\n"
            "`!farm growbot plant <crop> [count|plot_list]` — Plant empty plots with one crop"
        )

    @farm_growbot.command(name="harvest")
    async def farm_growbot_harvest(self, ctx):
        """Harvest all ready crops with GrowBot."""
        result = self.farming.growbot_harvest(ctx.author.id, str(ctx.author))
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        lines = [f"🤖 {ctx.author.mention}'s GrowBot harvested **{len(result.harvested)}** crop(s)!"]
        for plot_num, name, emoji, stars in result.harvested:
            crop = get_crop_by_name(name)
            mushroom_yield = crop.golden_mushroom_yield if crop else 0
            if mushroom_yield > 0:
                lines.append(f"  • Plot #{plot_num}: {emoji} {name} (+{mushroom_yield}🍄)")
            else:
                lines.append(f"  • Plot #{plot_num}: {emoji} {name} (+{stars}⭐)")

        lines.append(f"\n💰 Total: **{result.total_stars}⭐**")
        if result.mushrooms_earned > 0:
            lines.append(f"🍄 Found **{result.mushrooms_earned}** Golden Mushrooms!")

        lines.append(f"New balance: **{result.new_balance}** stars")
        await ctx.send("\n".join(lines))

    @farm_growbot.command(name="tend")
    async def farm_growbot_tend(self, ctx, item: str = ""):
        """Tend multiple plots with GrowBot."""
        if not item:
            await ctx.send(
                f"❌ {ctx.author.mention}, usage: `!farm growbot tend <fertilizer|water>`"
            )
            return

        result = self.farming.growbot_tend_all(ctx.author.id, str(ctx.author), item)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        item_display = "Fertilizer" if result.item_used == "fertilizer" else "Water"
        lines = [
            f"🤖 {ctx.author.mention}'s GrowBot tended **{len(result.tended_plots)}** plot(s) using **{item_display}**."
        ]
        for plot_number, before, after in result.tended_plots:
            lines.append(f"  • Plot #{plot_number}: {before}% → {after}%")
        if result.skipped_full_soil:
            skipped = ", ".join(str(plot) for plot in result.skipped_full_soil)
            lines.append(f"⏭️ Already max soil: Plot(s) {skipped}")
        lines.append(f"🎒 {item_display} left: **{result.remaining_items}**")
        await ctx.send("\n".join(lines))

    @farm_growbot.command(name="plant")
    async def farm_growbot_plant(self, ctx, crop: str = "", plot_selector: str = ""):
        """Plant one crop across all empty plots with GrowBot."""
        if not crop:
            await ctx.send(
                f"❌ {ctx.author.mention}, usage: `!farm growbot plant <crop> [count|plot_list]`\n"
                f"Examples: `!farm growbot plant wheat`, `!farm growbot plant melon 3`, `!farm growbot plant carrot 1,3,6`"
            )
            return

        result = self.farming.growbot_plant_all(
            ctx.author.id,
            str(ctx.author),
            crop,
            plot_selector,
        )
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        planted = ", ".join(str(plot) for plot in result.planted_plots)
        lines = [
            f"🤖 {ctx.author.mention}'s GrowBot planted {result.crop_emoji} **{result.crop_name}** in plot(s): {planted}",
            f"💸 Total seed cost: **{result.total_seed_cost}⭐**",
        ]
        if result.skipped_occupied:
            occupied = ", ".join(str(plot) for plot in result.skipped_occupied)
            lines.append(f"⏭️ Skipped occupied plot(s): {occupied}")
        lines.append(f"💰 New balance: **{result.new_balance}⭐**")
        await ctx.send("\n".join(lines))

    @commands.command(name="harvest")
    async def harvest(self, ctx, plot: str = ""):
        """Harvest a specific ready crop. Usage: !harvest <plot_number>"""
        if not plot:
            await ctx.send(
                f"❌ {ctx.author.mention}, usage: `!harvest <plot_number>`\n"
                f"Use `!farm growbot harvest` to harvest all ready plots."
            )
            return

        try:
            plot_number = int(plot)
        except ValueError:
            await ctx.send(
                f"❌ {ctx.author.mention}, invalid plot number.\n"
                f"Use `!harvest <plot_number>` or `!farm growbot harvest`."
            )
            return
        if plot_number <= 0:
            await ctx.send(
                f"❌ {ctx.author.mention}, plot number must be at least 1."
            )
            return

        result = self.farming.harvest(ctx.author.id, str(ctx.author), plot_number)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Build harvest summary
        if len(result.harvested) == 1:
            plot_num, name, emoji, stars = result.harvested[0]
            crop = get_crop_by_name(name)
            mushroom_yield = crop.golden_mushroom_yield if crop else 0
            if mushroom_yield > 0:
                await ctx.send(
                    f"🌾 {ctx.author.mention} harvested {emoji} **{name}** from Plot #{plot_num}!\n"
                    f"🍄 Found **{result.mushrooms_earned}** Golden Mushrooms!\n"
                    f"New balance: **{result.new_balance}** stars"
                )
            else:
                quality = next((q for p, q, _qm, _wm in result.quality_rolls if p == plot_num), "normal")
                quality_label = {
                    "bad": "🟤 Bad (-20%)",
                    "normal": "🟢 Normal (0%)",
                    "great": "🟡 Great (+20%)",
                }.get(quality, "🟢 Normal (0%)")
                weather_note = ""
                if any(p == plot_num and wm != 1.0 for p, _q, _qm, wm in result.quality_rolls):
                    weather_note = "\n🌤️ Event modifier applied."

                await ctx.send(
                    f"🌾 {ctx.author.mention} harvested {emoji} **{name}** from Plot #{plot_num}!\n"
                    f"🎯 Quality: **{quality_label}**{weather_note}\n"
                    f"💰 Earned **{stars}⭐**\n"
                    f"New balance: **{result.new_balance}** stars"
                )
        else:
            lines = [f"🌾 {ctx.author.mention} harvested **{len(result.harvested)}** crops!\n"]
            quality_by_plot = {
                plot: quality
                for plot, quality, _quality_mult, _weather_mult in result.quality_rolls
            }
            for plot_num, name, emoji, stars in result.harvested:
                crop = get_crop_by_name(name)
                mushroom_yield = crop.golden_mushroom_yield if crop else 0
                if mushroom_yield > 0:
                    lines.append(f"  • Plot #{plot_num}: {emoji} {name} (+{mushroom_yield}🍄)")
                else:
                    quality = quality_by_plot.get(plot_num, "normal")
                    quality_tag = {
                        "bad": "Bad",
                        "normal": "Normal",
                        "great": "Great",
                    }.get(quality, "Normal")
                    lines.append(f"  • Plot #{plot_num}: {emoji} {name} — {quality_tag} (+{stars}⭐)")

            lines.append(f"\n💰 Total: **{result.total_stars}⭐**")
            if result.mushrooms_earned > 0:
                lines.append(f"🍄 Found **{result.mushrooms_earned}** Golden Mushrooms!")

            lines.append(f"New balance: **{result.new_balance}** stars")
            await ctx.send("\n".join(lines))

    @commands.command(name="tend")
    async def tend(self, ctx, plot: int = 0, item: str = ""):
        """Tend a farm plot with fertilizer/water. Usage: !tend <plot_number> <item>"""
        if plot <= 0 or not item:
            await ctx.send(
                f"❌ {ctx.author.mention}, usage: `!tend <plot_number> <fertilizer|water>`"
            )
            return

        result = self.farming.tend_plot(ctx.author.id, str(ctx.author), plot, item)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        item_display = "Fertilizer" if result.item_used == "fertilizer" else "Water"
        await ctx.send(
            f"🧑‍🌾 {ctx.author.mention} tended Plot #{result.plot_number} using **{item_display}**.\n"
            f"🌱 Soil: **{result.soil_before}% → {result.soil_after}%**\n"
            f"🎒 {item_display} left: **{result.remaining_items}**"
        )

    @commands.command(name="crops")
    async def crops(self, ctx):
        """View available crops and their stats."""
        info = self.farming.get_crops_info()

        embed = discord.Embed(
            title="🌾 Available Crops",
            description="Plant crops with `!plant <crop> <plot_number>`",
            color=discord.Color.green(),
        )

        for name, emoji, seed_cost, sell_price, profit, growth_hours in info.crops:
            crop = get_crop_by_name(name)
            if growth_hours == 1:
                time_str = "1 hour"
            else:
                time_str = f"{growth_hours} hours"

            if crop and crop.golden_mushroom_yield > 0:
                value = (
                    f"🌱 Cost: **{seed_cost}**\n"
                    f"🍄 Yield: **{crop.golden_mushroom_yield} Golden Mushrooms**\n"
                    f"⏰ Growth: **{time_str}**\n"
                )
            else:
                value = (
                    f"🌱 Cost: **{seed_cost}**\n"
                    f"💰 Sell: **{sell_price}**\n"
                    f"⏰ Growth: **{time_str}**\n"
                )

            embed.add_field(
                name=f"{emoji} {name}",
                value=value,
                inline=True,
            )

        embed.set_footer(
            text=(
                "Seeds are bought automatically when planting. "
                "Longer crops usually offer better hourly value, but soil and rotation matter."
            )
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(FarmingCog(bot))

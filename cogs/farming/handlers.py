"""Farming commands cog."""

import discord
from discord.ext import commands

from cogs.farming.constants import MAX_PLOTS, PLOT_COSTS
from cogs.farming.use_cases import FarmingUseCases


class FarmingCog(commands.Cog):
    """Commands for the farming minigame."""

    def __init__(self, bot):
        self.bot = bot
        self.farming = FarmingUseCases()

    @commands.command(name="farm")
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
                    cells.append("🟫")
                elif plot.is_ready:
                    cells.append(f"{plot.crop_emoji}✨")
                else:
                    cells.append(f"{plot.crop_emoji}")
            grid_lines.append("│" + "│".join(cells) + "│")
            
            # Bottom border
            if len(row_plots) == 1:
                grid_lines.append("└───┘")
            else:
                grid_lines.append("└" + "───┴" * (len(row_plots) - 1) + "───┘")
            
            # Plot details below each row
            for plot in row_plots:
                if plot.is_empty:
                    grid_lines.append(f"Plot {plot.plot_number}: Empty")
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
                    grid_lines.append(f"Plot {plot.plot_number}: {plot.crop_name} - {time_str} remaining")
            
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

        # Add footer with next plot info
        if status.can_buy_more and status.next_plot_cost:
            embed.set_footer(
                text=f"💰 Next plot: {status.next_plot_cost}⭐ • !buyplot to expand • !harvest to collect"
            )
        elif not status.can_buy_more:
            embed.set_footer(text=f"🌟 Maximum plots reached ({MAX_PLOTS}) • !harvest to collect")

        await ctx.send(embed=embed)

    @commands.command(name="buyplot")
    async def buyplot(self, ctx):
        """Buy a new farm plot."""
        result = self.farming.buy_plot(ctx.author.id, str(ctx.author))

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

    @commands.command(name="harvest")
    async def harvest(self, ctx, plot: str = "all"):
        """Harvest ready crops. Usage: !harvest [plot_number|all]"""
        # Parse plot number or "all"
        plot_number = None
        if plot.lower() != "all":
            try:
                plot_number = int(plot)
            except ValueError:
                await ctx.send(
                    f"❌ {ctx.author.mention}, invalid plot number!\n"
                    f"Usage: `!harvest <plot_number>` or `!harvest all`"
                )
                return

        result = self.farming.harvest(ctx.author.id, str(ctx.author), plot_number)

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Build harvest summary
        if len(result.harvested) == 1:
            plot_num, name, emoji, stars = result.harvested[0]
            await ctx.send(
                f"🌾 {ctx.author.mention} harvested {emoji} **{name}** from Plot #{plot_num}!\n"
                f"💰 Earned **{stars}** stars!\n"
                f"New balance: **{result.new_balance}** stars"
            )
        else:
            lines = [f"🌾 {ctx.author.mention} harvested **{len(result.harvested)}** crops!\n"]
            for plot_num, name, emoji, stars in result.harvested:
                lines.append(f"  • Plot #{plot_num}: {emoji} {name} (+{stars}⭐)")
            lines.append(f"\n💰 Total: **{result.total_stars}** stars!")
            lines.append(f"New balance: **{result.new_balance}** stars")
            await ctx.send("\n".join(lines))

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
            if growth_hours == 1:
                time_str = "1 hour"
            else:
                time_str = f"{growth_hours} hours"

            embed.add_field(
                name=f"{emoji} {name}",
                value=(
                    f"🌱 Cost: **{seed_cost}**\n"
                    f"💰 Sell: **{sell_price}**\n"
                    f"⏰ Growth: **{time_str}**\n"
                ),
                inline=True,
            )

        embed.set_footer(text="You do not need to pre-purchase crops, they will automatically purchase when you plant them!\nLonger crops = higher hourly rate, but require patience!")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(FarmingCog(bot))

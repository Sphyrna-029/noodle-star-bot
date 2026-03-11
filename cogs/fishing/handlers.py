"""Fishing commands cog."""

import discord
from discord.ext import commands

from cogs.fishing.constants import FISH_LEVELS, FISHING_BAIT_TIERS, FISHING_COOLDOWN
from cogs.fishing.use_case import FishingUseCases
from cogs.fishing.dto import FishingState
from cogs.locations.check import require_location


class PullButtonView(discord.ui.View):
    """A single Pull button for when a fish is biting."""

    def __init__(self, user_id: int, fishing_uc: "FishingUseCases", timeout: float = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.fishing_uc = fishing_uc

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your fishing line!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Pull!", style=discord.ButtonStyle.success, emoji="🎣")
    async def pull_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = self.fishing_uc.pull_line(interaction.user.id, str(interaction.user))

        # Disable button after use
        for child in self.children:
            child.disabled = True

        if not result.success:
            await interaction.response.edit_message(
                content=f"🎣 {interaction.user.mention}, {result.message}",
                view=self,
            )
            return

        # Build success embed (same as the !pull command)
        if result.catch_rarity == "legendary":
            header = "🌟 **LEGENDARY CATCH!** 🌟"
            color = discord.Color.gold()
        elif result.catch_rarity == "rare":
            header = "✨ **RARE CATCH!** ✨"
            color = discord.Color.blue()
        else:
            header = "🎣 **You caught something!**"
            color = discord.Color.green()

        embed = discord.Embed(title=header, color=color)

        if result.stars_earned > 0:
            embed.description = (
                f"{interaction.user.mention} caught a {result.catch_emoji} **{result.catch_name}**!\n\n"
                f"Added to inventory! (sell value: **{result.stars_earned}** ⭐)\n"
                f"🎒 Bag: **{result.bag_count}/{result.bag_capacity}**\n"
                f"💰 Wallet: **{result.new_balance}** stars"
            )
        else:
            embed.description = (
                f"{interaction.user.mention} caught a {result.catch_emoji} **{result.catch_name}**!\n\n"
                f"*It's worthless junk... but at least you caught something!*\n"
                f"🎒 Bag: **{result.bag_count}/{result.bag_capacity}**\n"
                f"💰 Wallet: **{result.new_balance}** stars"
            )

        if result.found_items:
            embed.add_field(name="**ITEM DROP!**", value="\n".join(result.found_items), inline=False)
        if result.extra_messages:
            for msg in result.extra_messages:
                embed.add_field(name="\u200b", value=msg, inline=False)
        if result.level_name:
            embed.set_footer(text=f"{result.level_emoji} {result.level_name}")

        if result.disaster:
            if result.disaster_protected:
                embed.add_field(name=result.disaster_header, value=result.disaster_protected_msg, inline=False)
            else:
                disaster_text = result.disaster_unprotected_msg
                if result.items_destroyed:
                    disaster_text += f"\n💰 Wallet: **{result.new_balance}** stars"
                embed.add_field(name=result.disaster_header, value=disaster_text, inline=False)
                embed.color = discord.Color.red()

        await interaction.response.edit_message(content=None, embed=embed, view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True


class FishingCog(commands.Cog):
    """Commands for the fishing minigame."""

    def __init__(self, bot):
        self.bot = bot
        self.fishing = FishingUseCases()
        # Set up the bite notification callback
        self.fishing.set_bite_callback(self._on_bite)

    async def _on_bite(
        self,
        user_id: int,
        channel_id: int,
        pull_window: int,
    ) -> None:
        """
        Callback for bite notifications.

        pull_window: seconds remaining, or -1 if fish escaped
        """
        # Try to resolve the user first
        user = self.bot.get_user(user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                return

        # Try to get the channel from cache; if missing, attempt fetch
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                channel = None

        # Prepare messages
        if pull_window == -1:
            msg = (
                f"🐟💨 {user.mention}, the fish got away! "
                f"You didn't pull in time. Your line snapped."
            )
            view = None
        else:
            msg = (
                f"🎣 **{user.mention}, you feel a tug!** "
                f"Type `!pull` or click the button within **{pull_window} seconds**!"
            )
            view = PullButtonView(user_id, self.fishing, timeout=pull_window)

        # Send to channel if available, otherwise DM the user
        try:
            if channel is not None:
                await channel.send(msg, view=view)
            else:
                # Fallback to DM
                try:
                    await user.send(msg, view=view)
                except Exception:
                    # If DM fails, give up silently
                    return
        except Exception:
            # Don't let callback exceptions crash the service
            return

    @commands.command(name="fish")
    async def fish(self, ctx, bait: str = ''):
        """Cast your fishing line and wait for a bite.

        Usage: `!fish` or `!fish <bait>` to equip bait then cast.
        """
        if not await require_location(ctx, "starfish_bay"):
            return
        # If a bait type was provided, ensure user is not already fishing first
        if bait:
            session = self.fishing.get_session(ctx.author.id)
            if session is not None:
                await ctx.send(
                    f"🎣 {ctx.author.mention}, you're already fishing! Wait for the current attempt or use `!fishing` to check status."
                )
                return

            equip_result = self.fishing.equip_bait(
                ctx.author.id,
                str(ctx.author),
                bait,
            )

            if not equip_result.success:
                await ctx.send(f"🎣 {ctx.author.mention}, {equip_result.message}")
                return

            # Inform user of equip success
            await ctx.send(f"✅ {ctx.author.mention}, {equip_result.message}")

        result = await self.fishing.cast_line(
            ctx.author.id,
            str(ctx.author),
            ctx.channel.id,
        )

        if not result.success:
            await ctx.send(f"🎣 {ctx.author.mention}, {result.message}")
            return

        await ctx.send(f"🎣 {ctx.author.mention}, {result.message}")

    @commands.command(name="pull")
    async def pull(self, ctx):
        """Pull your fishing line when you feel a tug!"""
        if not await require_location(ctx, "starfish_bay"):
            return
        result = self.fishing.pull_line(ctx.author.id, str(ctx.author))

        if not result.success:
            failure_message = f"🎣 {ctx.author.mention}, {result.message}"
            if result.extra_messages:
                failure_message += "\n" + "\n".join(result.extra_messages)
            await ctx.send(failure_message)
            return

        # Format success message based on rarity
        if result.catch_rarity == "legendary":
            header = "🌟 **LEGENDARY CATCH!** 🌟"
            color = discord.Color.gold()
        elif result.catch_rarity == "rare":
            header = "✨ **RARE CATCH!** ✨"
            color = discord.Color.blue()
        else:
            header = "🎣 **You caught something!**"
            color = discord.Color.green()

        embed = discord.Embed(title=header, color=color)

        if result.stars_earned > 0:
            embed.description = (
                f"{ctx.author.mention} caught a {result.catch_emoji} **{result.catch_name}**!\n\n"
                f"Added to inventory! (sell value: **{result.stars_earned}** \u2b50)\n"
                f"\ud83c\udf92 Bag: **{result.bag_count}/{result.bag_capacity}**\n"
                f"\ud83d\udcb0 Wallet: **{result.new_balance}** stars"
            )
        else:
            # Junk item
            embed.description = (
                f"{ctx.author.mention} caught a {result.catch_emoji} **{result.catch_name}**!\n\n"
                f"*It's worthless junk... but at least you caught something!*\n"
                f"\ud83c\udf92 Bag: **{result.bag_count}/{result.bag_capacity}**\n"
                f"\ud83d\udcb0 Wallet: **{result.new_balance}** stars"
            )

        # Item drops
        if result.found_items:
            embed.add_field(
                name="**ITEM DROP!**",
                value="\n".join(result.found_items),
                inline=False,
            )

        # Extra messages (e.g. heart of leviathan bank protection)
        if result.extra_messages:
            for msg in result.extra_messages:
                embed.add_field(name="\u200b", value=msg, inline=False)

        # Show fishing level in footer
        if result.level_name:
            embed.set_footer(text=f"{result.level_emoji} {result.level_name}")

        # Handle disaster messages
        if result.disaster:
            if result.disaster_protected:
                embed.add_field(
                    name=result.disaster_header,
                    value=result.disaster_protected_msg,
                    inline=False,
                )
            else:
                disaster_text = result.disaster_unprotected_msg
                if result.items_destroyed:
                    disaster_text += f"\n\ud83d\udcb0 Wallet: **{result.new_balance}** stars"
                embed.add_field(
                    name=result.disaster_header,
                    value=disaster_text,
                    inline=False,
                )
                embed.color = discord.Color.red()

        await ctx.send(embed=embed)

    @commands.command(name="fishing")
    async def fishing_status(self, ctx):
        """Check your current fishing status."""
        status = self.fishing.get_status(ctx.author.id, str(ctx.author))

        embed = discord.Embed(
            title=f"🎣 {ctx.author.display_name}'s Fishing Status",
            color=discord.Color.blue(),
        )

        # Equipped bait
        if status.equipped_bait:
            bait_info = FISHING_BAIT_TIERS[status.equipped_bait]
            embed.add_field(
                name="Equipped Bait",
                value=f"{bait_info.emoji} {bait_info.display_name}",
                inline=True,
            )
        else:
            embed.add_field(
                name="Equipped Bait",
                value="None (will use Worm)",
                inline=True,
            )

        if status.is_fishing:
            if status.state == FishingState.WAITING:
                embed.add_field(
                    name="Status",
                    value="🎣 Waiting for a bite...",
                    inline=True,
                )
                if status.time_until_bite is not None:
                    # Don't show exact time, just a hint
                    if status.time_until_bite > 60:
                        hint = "Be patient..."
                    elif status.time_until_bite > 10:
                        hint = "Should be soon..."
                    else:
                        hint = "Any moment now!"
                    embed.add_field(
                        name="Hint",
                        value=hint,
                        inline=True,
                    )

            elif status.state == FishingState.BITING:
                embed.add_field(
                    name="Status",
                    value="🐟 **A FISH IS BITING!**",
                    inline=True,
                )
                if status.time_until_expires is not None:
                    embed.add_field(
                        name="Time Left",
                        value=f"**{status.time_until_expires}s** to `!pull`!",
                        inline=True,
                    )
                pull_view = PullButtonView(
                    ctx.author.id, self.fishing,
                    timeout=status.time_until_expires or 60,
                )
                await ctx.send(embed=embed, view=pull_view)
                return

            embed.color = discord.Color.orange()

        else:
            embed.add_field(
                name="Status",
                value="Not currently fishing",
                inline=True,
            )

            if status.cooldown_remaining is not None and status.cooldown_remaining > 0:
                minutes = status.cooldown_remaining // 60
                seconds = status.cooldown_remaining % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                embed.add_field(
                    name="Cooldown",
                    value=f"Wait **{time_str}** to fish again",
                    inline=True,
                )
                embed.color = discord.Color.red()
            else:
                embed.add_field(
                    name="Ready",
                    value="Use `!fish` to cast your line!",
                    inline=True,
                )
                embed.color = discord.Color.green()

        await ctx.send(embed=embed)

    @commands.command(name="fishlevel")
    async def fishlevel(self, ctx, level: int = 0):
        """View or switch your fishing level. Usage: !fishlevel [number]"""
        if level != 0:
            # Switch active level
            success, msg = self.fishing.set_active_fish_level(ctx.author.id, level)
            if success:
                # Add bank risk warning for levels 4-5
                if level >= 4:
                    level_config = FISH_LEVELS[level]
                    max_bank_loss = max(h.bank_loss_pct for h in level_config["hazards"])
                    warning = f"\n⚠️ **WARNING:** This level has disasters that can take up to {int(max_bank_loss * 100)}% of your BANK if a disaster hits! Use protection items!"
                    msg += warning
                await ctx.send(f"🎣 {ctx.author.mention}, {msg}")
            else:
                await ctx.send(f"❌ {ctx.author.mention}, {msg}")
            return

        # Show level info
        info = self.fishing.get_fish_level_info(ctx.author.id)

        lines = [f"🎣 **Fishing Levels** — {ctx.author.mention}\n"]

        for lvl_num, lvl in info.levels.items():
            if lvl_num <= info.unlocked_level:
                active = " ◀️" if lvl_num == info.active_level else ""
                hazard_warning = ""
                if lvl["disaster_chance"] > 0:
                    hazard_info = f" ⚠️ {int(lvl['disaster_chance'] * 100)}% hazard"
                    # Add bank risk info for levels 4-5
                    if lvl_num >= 4:
                        max_bank_loss = max(h.bank_loss_pct for h in lvl["hazards"])
                        if max_bank_loss > 0:
                            hazard_info += f" | Bank risk: up to {int(max_bank_loss * 100)}% if a disaster hits"
                    hazard_warning = hazard_info
                lines.append(
                    f"{lvl['emoji']} **Level {lvl_num} — {lvl['name']}** ✅{active}{hazard_warning}"
                )
            else:
                lines.append(
                    f"🔒 **Level {lvl_num} — {lvl['name']}** — *Unlock in mine first*"
                )

        lines.append("\nUse `!fishlevel <number>` to switch levels")
        lines.append("Fishing levels share unlocks with mining — use `!unlock <number>` to unlock new levels")
        lines.append("\n💡 Levels 4-5 can affect your bank balance if a disaster hits!")

        await ctx.send("\n".join(lines))

    @commands.command(name="use")
    async def use_item(self, ctx, item_type: str = '', item_name: str = ''):
        """Use an item. Usage: !use bait <type> | !use jig"""
        if item_type is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, please specify what to use!\n"
                f"Examples: `!use bait worm`, `!use jig`"
            )
            return

        item_type = item_type.lower().strip()

        if item_type == "bait":
            if item_name is None:
                # Show available bait types
                bait_list = []
                for bait_key, bait_info in FISHING_BAIT_TIERS.items():
                    bait_list.append(
                        f"{bait_info['emoji']} **{bait_info['display_name']}** (`{bait_key}`)"
                    )
                await ctx.send(
                    f"🎣 {ctx.author.mention}, specify which bait to equip:\n"
                    + "\n".join(bait_list)
                    + "\n\nExample: `!use bait herring`"
                )
                return

            result = self.fishing.equip_bait(
                ctx.author.id,
                str(ctx.author),
                item_name,
            )

            if not result.success:
                await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
                return

            await ctx.send(f"✅ {ctx.author.mention}, {result.message}")

        elif item_type == "jig":
            success, msg = self.fishing.activate_jig(ctx.author.id, str(ctx.author))
            if success:
                await ctx.send(f"✅ {ctx.author.mention}, {msg}")
            else:
                await ctx.send(f"❌ {ctx.author.mention}, {msg}")

        else:
            await ctx.send(
                f"❌ {ctx.author.mention}, unknown item type `{item_type}`!\n"
                f"Available: `bait`, `jig`"
            )

    @commands.command(name="equipbait", aliases=["eb"])
    async def equip_bait(self, ctx, item_type: str = '', item_name: str = ''):
        """Alias for !use. Equip bait for fishing."""
        await self.use_item(ctx, item_type, item_name)

    @commands.command(name="baitshop")
    async def bait_shop(self, ctx):
        """View available bait and their effects."""
        embed = discord.Embed(
            title="🎣 Bait Shop",
            description="Buy bait from `!store`, then equip with `!use bait <type>`",
            color=discord.Color.blue(),
        )

        for bait_key, bait_info in FISHING_BAIT_TIERS.items():
            min_wait = int(bait_info.bite_wait_min.total_seconds())
            max_wait = int(bait_info.bite_wait_max.total_seconds())
            pull_window = int(bait_info.pull_window.total_seconds())
            embed.add_field(
                name=f"{bait_info.emoji} {bait_info.display_name}",
                value=(
                    f"**Bite wait:** {min_wait}-{max_wait}s\n"
                    f"**Pull window:** {pull_window}s\n"
                    f"**Rare boost:** {bait_info.rare_boost}x"
                ),
                inline=True,
            )

        embed.set_footer(
            text=f"Fishing cooldown: {int(FISHING_COOLDOWN.total_seconds())}s between attempts"
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(FishingCog(bot))

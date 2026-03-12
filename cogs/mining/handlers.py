"""Mining commands cog — interactive mine button with live stamina bar."""

import discord
from discord.ext import commands

from cogs.locations.check import require_location
from cogs.mining.constants import MINE_LEVELS, MINERAL_TABLES, MINING_STAMINA_COST
from cogs.mining.use_case import MiningUseCases


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _progress_bar(current: int, maximum: int, length: int = 10) -> str:
    pct = current / maximum if maximum else 0
    filled = int(pct * length)
    return "█" * filled + "░" * (length - filled)


def _rarity_header(result) -> str:
    if result.stars_earned >= 100:
        return "🎉 JACKPOT!"
    elif result.stars_earned >= 40:
        return "✨ RARE FIND!"
    return f"{result.level_emoji} Mining in {result.level_name}..."


def _build_mine_embed(result, author: discord.Member | discord.User, stamina: int, max_stamina: int) -> discord.Embed:
    """Build the mining result embed with stamina bar."""
    header = _rarity_header(result)

    embed = discord.Embed(
        title=header,
        description=(
            f"{result.mineral_emoji} **{result.mineral_name}** — sell value: **{result.stars_earned}** ⭐\n"
            f"🎒 Bag: **{result.bag_count}/{result.bag_capacity}** · 💰 Wallet: **{result.new_balance}** stars"
        ),
        color=discord.Color.gold() if result.stars_earned >= 40 else discord.Color.dark_grey(),
    )

    stam_bar = _progress_bar(stamina, max_stamina)
    embed.add_field(
        name="⚡ Stamina",
        value=f"{stamina}/{max_stamina} {stam_bar}",
        inline=False,
    )

    # Extra messages (achievements)
    if result.extra_messages:
        embed.add_field(
            name="🏆 Achievement",
            value="\n".join(result.extra_messages),
            inline=False,
        )

    # Item drops
    if result.found_items:
        embed.add_field(
            name="✨ Item Drop!",
            value="\n".join(result.found_items),
            inline=False,
        )

    embed.set_footer(text=f"⛏️ {author.display_name}")
    return embed


# ---------------------------------------------------------------------------
# Interactive Mine View
# ---------------------------------------------------------------------------

class MineView(discord.ui.View):
    """Persistent mine button that updates the embed each click."""

    def __init__(self, author_id: int, username: str, mining_uc: MiningUseCases, bot, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.username = username
        self.mining = mining_uc
        self.bot = bot
        self.message = None

    @discord.ui.button(label="Mine Again", emoji="⛏️", style=discord.ButtonStyle.primary)
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Not your mine!", ephemeral=True)
            return

        result = self.mining.mine(self.author_id, self.username)

        if not result.success:
            # Stamina or inventory full — disable button, show reason
            button.disabled = True
            button.label = "Can't Mine"
            button.style = discord.ButtonStyle.secondary
            embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
            embed.color = discord.Color.red()
            embed.set_field_at(0, name="⚡ Stamina", value=f"❌ {result.message}", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
            return

        # Get updated stamina
        from cogs.combat.use_case.health import HealthUseCases
        health_uc = HealthUseCases(self.mining.repo)
        status = health_uc.get_status(self.author_id)

        embed = _build_mine_embed(result, interaction.user, status.current_stamina, status.max_stamina)

        # Check if next mine is possible
        active_level = self.mining.repo.get_active_mine_level(self.author_id)
        next_cost = MINING_STAMINA_COST[active_level]
        can_mine_again = (
            status.current_stamina >= next_cost
            and result.bag_count < result.bag_capacity
            and not result.ambush_mob_key
        )

        if not can_mine_again and not result.ambush_mob_key:
            button.disabled = True
            button.label = "Can't Mine"
            button.style = discord.ButtonStyle.secondary
            if status.current_stamina < next_cost:
                embed.set_field_at(0, name="⚡ Stamina", value=f"{status.current_stamina}/{status.max_stamina} {_progress_bar(status.current_stamina, status.max_stamina)}\n❌ Not enough stamina ({next_cost} needed)", inline=False)
            elif result.bag_count >= result.bag_capacity:
                embed.description += "\n❌ Inventory full!"

        if result.ambush_mob_key:
            # Ambush! Disable button and let the ambush handler take over
            button.disabled = True
            button.label = "Ambushed!"
            button.style = discord.ButtonStyle.danger

        await interaction.response.edit_message(embed=embed, view=self)

        # Handle ambush AFTER edit (sends as a new message)
        if result.ambush_mob_key:
            self.stop()
            await _handle_ambush(interaction, result, self.author_id, self.username)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Ambush handler (shared between command and button)
# ---------------------------------------------------------------------------

async def _handle_ambush(ctx_or_interaction, result, user_id: int, username: str):
    """Spawn an ambush battle. Works with both Context and Interaction."""
    from cogs.combat.ambush_constants import MINING_AMBUSH_MOBS, AMBUSH_DEFEAT_PENALTIES, AMBUSH_FLEE_LOCKOUT
    from cogs.combat.use_case.combat import CombatUseCases
    from cogs.combat.handlers import BattleView, is_in_battle
    from cogs.gambling.handlers import is_in_duel

    if is_in_battle(user_id) or is_in_duel(user_id):
        return

    mobs = MINING_AMBUSH_MOBS.get(result.ambush_level, [])
    mob = next((m for m in mobs if m.key == result.ambush_mob_key), None)
    if not mob:
        return

    combat_uc = CombatUseCases()
    penalty = AMBUSH_DEFEAT_PENALTIES["mining"][result.ambush_level]
    flee_lockout = AMBUSH_FLEE_LOCKOUT[result.ambush_level]
    battle, error = combat_uc.start_ambush(
        user_id=user_id,
        username=username,
        mob=mob,
        activity="mining",
        activity_level=result.ambush_level,
        penalty=penalty,
        flee_lockout_turns=flee_lockout,
    )

    # Determine how to send
    if isinstance(ctx_or_interaction, discord.Interaction):
        send = ctx_or_interaction.followup.send
    else:
        send = ctx_or_interaction.send

    if battle:
        battle_view = BattleView(battle, combat_uc, user_id, username)
        embed = battle_view._create_embed()
        msg = await send(embed=embed, view=battle_view)
        battle_view.message = msg
    elif error:
        await send(f"⚠️ A {result.ambush_mob_emoji} **{result.ambush_mob_name}** ambushed you but you were too weak to fight! {error}")


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class MiningCog(commands.Cog):
    """Commands for mining minerals."""

    def __init__(self, bot):
        self.bot = bot
        self.mining = MiningUseCases()

    @commands.command(name="mine")
    async def mine(self, ctx):
        """Mine for minerals to earn noodle stars!"""
        if not await require_location(ctx, "crystal_cave"):
            return

        # Gear warning on initial mine command
        from cogs.combat.ambush_constants import MINING_AMBUSH_MOBS
        from cogs.combat.use_case.gear_check import gear_warning
        active_level = self.mining.repo.get_active_mine_level(ctx.author.id)
        mobs = MINING_AMBUSH_MOBS.get(active_level, [])
        warning = gear_warning(ctx.author.id, mobs, self.mining.repo)
        if warning:
            await ctx.send(warning)

        result = self.mining.mine(ctx.author.id, str(ctx.author))

        if not result.success:
            await ctx.send(f"⏰ {ctx.author.mention}, {result.message}")
            return

        # Get current stamina for the bar
        from cogs.combat.use_case.health import HealthUseCases
        health_uc = HealthUseCases(self.mining.repo)
        status = health_uc.get_status(ctx.author.id)

        embed = _build_mine_embed(result, ctx.author, status.current_stamina, status.max_stamina)

        # Check if another mine is possible
        active_level = self.mining.repo.get_active_mine_level(ctx.author.id)
        next_cost = MINING_STAMINA_COST[active_level]
        can_mine_again = (
            status.current_stamina >= next_cost
            and result.bag_count < result.bag_capacity
            and not result.ambush_mob_key
        )

        if can_mine_again:
            view = MineView(ctx.author.id, str(ctx.author), self.mining, self.bot)
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg
        else:
            # No button if can't mine again
            if status.current_stamina < next_cost and not result.ambush_mob_key:
                embed.set_field_at(0, name="⚡ Stamina", value=f"{status.current_stamina}/{status.max_stamina} {_progress_bar(status.current_stamina, status.max_stamina)}\n❌ Not enough stamina ({next_cost} needed)", inline=False)
            elif result.bag_count >= result.bag_capacity and not result.ambush_mob_key:
                embed.description += "\n❌ Inventory full!"
            await ctx.send(embed=embed)

        # Handle ambush
        if result.ambush_mob_key:
            await _handle_ambush(ctx, result, ctx.author.id, str(ctx.author))

    @commands.command(name="minelevel")
    async def minelevel(self, ctx, level: int = 0):
        """View or switch your mine level. Usage: !minelevel [number]"""
        if level != 0:
            success, msg = self.mining.set_active_level(ctx.author.id, level)
            if success:
                await ctx.send(f"⛏️ {ctx.author.mention}, {msg}")
            else:
                await ctx.send(f"❌ {ctx.author.mention}, {msg}")
            return

        info = self.mining.get_level_info(ctx.author.id)

        lines = [f"⛏️ **Mine Levels** — {ctx.author.mention}\n"]

        for lvl_num, lvl in info.levels.items():
            if lvl_num <= info.unlocked_level:
                active = " ◀️" if lvl_num == info.active_level else ""
                lines.append(f"{lvl['emoji']} **Level {lvl_num} — {lvl['name']}** ✅{active}")
            elif lvl_num == info.unlocked_level + 1:
                lines.append(f"🔒 **Level {lvl_num} — {lvl['name']}** — *{lvl['cost']} stars to unlock*")
            else:
                lines.append(f"🔒 **Level {lvl_num} — {lvl['name']}** — *Locked*")

        lines.append(f"\nUse `!minelevel <number>` to switch levels")
        lines.append(f"Use `!unlock <number>` to unlock the next level")
        lines.append(f"\n⚔️ Higher levels have tougher ambush encounters — stay prepared!")

        await ctx.send("\n".join(lines))

    @commands.command(name="unlock")
    async def unlock(self, ctx, level: int = 0):
        """Unlock a new mine level. Usage: !unlock <level>"""
        if not await require_location(ctx, "crystal_cave", "noodle_town"):
            return
        if level is None:
            await ctx.send(f"❌ {ctx.author.mention}, please specify a level to unlock! Usage: `!unlock <level>`")
            return

        result = self.mining.unlock_level(ctx.author.id, str(ctx.author), level)

        if result.success:
            level_config = MINE_LEVELS[result.level]
            minerals = MINERAL_TABLES[result.level]["normal"]
            mineral_list = " ".join(f"{m.emoji} {m.name} ({m.stars}⭐)" for m in minerals)

            message = (
                f"🎊 {ctx.author.mention}, {result.message}\n"
                f"Cost: **{result.cost}** stars\n\n"
                f"**New minerals available:**\n{mineral_list}"
            )

            await ctx.send(message)
        else:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(MiningCog(bot))

"""Mining commands cog."""

from discord.ext import commands

from cogs.mining.constants import MINE_LEVELS
from cogs.mining.use_cases import MiningUseCases


class MiningCog(commands.Cog):
    """Commands for mining minerals."""

    def __init__(self, bot):
        self.bot = bot
        self.mining = MiningUseCases()

    @commands.command(name="mine")
    async def mine(self, ctx, use_item: str = ''):
        """Mine for minerals to earn noodle stars!"""
        result = self.mining.mine(ctx.author.id, str(ctx.author), use_item)

        if not result.success:
            await ctx.send(f"⏰ {ctx.author.mention}, {result.message}")
            return

        # Build header based on mineral value
        top_minerals = {m.name for m in MINE_LEVELS[1]["minerals_normal"][-1:]}
        for lvl in MINE_LEVELS.values():
            for m in lvl["minerals_normal"][-1:]:
                top_minerals.add(m.name)
            for m in lvl["minerals_normal"][-2:-1]:
                top_minerals.add(m.name)

        # Check rarity by star value
        if result.stars_earned >= 100:
            header = "🎉 **JACKPOT!** 🎉"
        elif result.stars_earned >= 40:
            header = "✨ **RARE FIND!** ✨"
        else:
            header = f"{result.level_emoji} **Mining in {result.level_name}...**"

        message = (
            f"{header}\n"
            f"{ctx.author.mention} mined {result.mineral_emoji} **{result.mineral_name}**!\n"
            f"You earned **{result.stars_earned}** noodle stars! ⭐"
        )

        # Handle disaster messages using the generic hazard data
        if result.disaster:
            if result.disaster_protected:
                message += f"\n\n{result.disaster_header}\n{result.disaster_protected_msg}"
            else:
                message += f"\n\n{result.disaster_header}\n{result.disaster_unprotected_msg}"

        message += f"\nNew balance: **{result.new_balance}** stars!"

        await ctx.send(message)

    @commands.command(name="minelevel")
    async def minelevel(self, ctx, level: int = 0):
        """View or switch your mine level. Usage: !minelevel [number]"""
        if level != 0:
            # Switch active level
            success, msg = self.mining.set_active_level(ctx.author.id, level)
            if success:
                await ctx.send(f"⛏️ {ctx.author.mention}, {msg}")
            else:
                await ctx.send(f"❌ {ctx.author.mention}, {msg}")
            return

        # Show level info
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

        await ctx.send("\n".join(lines))

    @commands.command(name="unlock")
    async def unlock(self, ctx, level: int = 0):
        """Unlock a new mine level. Usage: !unlock <level>"""
        if level is None:
            await ctx.send(f"❌ {ctx.author.mention}, please specify a level to unlock! Usage: `!unlock <level>`")
            return

        result = self.mining.unlock_level(ctx.author.id, str(ctx.author), level)

        if result.success:
            level_config = MINE_LEVELS[result.level]
            minerals = level_config["minerals_normal"]
            mineral_list = " ".join(f"{m.emoji} {m.name} ({m.stars}⭐)" for m in minerals)
            await ctx.send(
                f"🎊 {ctx.author.mention}, {result.message}\n"
                f"Cost: **{result.cost}** stars\n\n"
                f"**New minerals available:**\n{mineral_list}"
            )
        else:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(MiningCog(bot))

"""Mining commands cog."""

from discord.ext import commands

from cogs.mining.constants import MINE_LEVELS, MINERAL_TABLES
from cogs.mining.use_case import MiningUseCases


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
        top_minerals = {m.name for m in MINERAL_TABLES[1]["normal"][-1:]}
        for lvl_num in MINE_LEVELS.keys():
            for m in MINERAL_TABLES[lvl_num]["normal"][-1:]:
                top_minerals.add(m.name)
            for m in MINERAL_TABLES[lvl_num]["normal"][-2:-1]:
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

        # Extra messages (e.g. heart of leviathan bank protection)
        for extra in result.extra_messages:
            message += f"\n{extra}"

        message += f"\nNew balance: **{result.new_balance}** stars!"

        # Item drops
        if result.found_items:
            message += "\n\n**ITEM DROP!**\n" + "\n".join(result.found_items)

        await ctx.send(message)

    @commands.command(name="minelevel")
    async def minelevel(self, ctx, level: int = 0):
        """View or switch your mine level. Usage: !minelevel [number]"""
        if level != 0:
            # Switch active level
            success, msg = self.mining.set_active_level(ctx.author.id, level)
            if success:
                # Add bank risk warning for levels 4-5
                if level >= 4:
                    level_config = MINE_LEVELS[level]
                    max_bank_loss = max(h.bank_loss_pct for h in level_config["hazards"])
                    warning = f"\n⚠️ **WARNING:** This level has disasters that can take up to {int(max_bank_loss * 100)}% of your BANK if a disaster hits! Use protection items!"
                    msg += warning
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
                risk_warning = ""
                if lvl_num >= 4:
                    max_bank_loss = max(h.bank_loss_pct for h in lvl["hazards"])
                    if max_bank_loss > 0:
                        risk_warning = f" ⚠️ Bank risk: up to {int(max_bank_loss * 100)}% if a disaster hits"
                lines.append(f"{lvl['emoji']} **Level {lvl_num} — {lvl['name']}** ✅{active}{risk_warning}")
            elif lvl_num == info.unlocked_level + 1:
                risk_warning = ""
                if lvl_num >= 4:
                    max_bank_loss = max(h.bank_loss_pct for h in lvl["hazards"])
                    if max_bank_loss > 0:
                        risk_warning = f" ⚠️ Bank risk: up to {int(max_bank_loss * 100)}% if a disaster hits"
                lines.append(f"🔒 **Level {lvl_num} — {lvl['name']}** — *{lvl['cost']} stars to unlock*{risk_warning}")
            else:
                lines.append(f"🔒 **Level {lvl_num} — {lvl['name']}** — *Locked*")

        lines.append(f"\nUse `!minelevel <number>` to switch levels")
        lines.append(f"Use `!unlock <number>` to unlock the next level")
        lines.append(f"\n💡 Levels 4-5 can affect your bank balance if a disaster hits!")

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
            minerals = MINERAL_TABLES[result.level]["normal"]
            mineral_list = " ".join(f"{m.emoji} {m.name} ({m.stars}⭐)" for m in minerals)

            message = (
                f"🎊 {ctx.author.mention}, {result.message}\n"
                f"Cost: **{result.cost}** stars\n\n"
                f"**New minerals available:**\n{mineral_list}"
            )

            # Add bank risk warning for levels 4-5
            if result.level >= 4:
                max_bank_loss = max(h.bank_loss_pct for h in level_config["hazards"])
                message += f"\n\n⚠️ **WARNING:** This level has disasters that can take up to {int(max_bank_loss * 100)}% of your BANK balance if a disaster hits! Keep protection items in your inventory!"

            await ctx.send(message)
        else:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(MiningCog(bot))

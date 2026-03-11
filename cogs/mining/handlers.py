"""Mining commands cog."""

from discord.ext import commands

from cogs.locations.check import require_location
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
        if not await require_location(ctx, "crystal_cave"):
            return
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
            f"Added to inventory! (sell value: **{result.stars_earned}** ⭐)\n🎒 Bag: **{result.bag_count}/{result.bag_capacity}**"
        )

        # Extra messages
        for extra in result.extra_messages:
            message += f"\n{extra}"

        message += f"\n💰 Wallet: **{result.new_balance}** stars"

        # Item drops
        if result.found_items:
            message += "\n\n**ITEM DROP!**\n" + "\n".join(result.found_items)

        await ctx.send(message)

        # Handle ambush encounter
        if result.ambush_mob_key:
            from cogs.combat.ambush_constants import MINING_AMBUSH_MOBS, AMBUSH_DEFEAT_PENALTIES, AMBUSH_FLEE_LOCKOUT
            from cogs.combat.use_case.combat import CombatUseCases
            from cogs.combat.handlers import BattleView

            mobs = MINING_AMBUSH_MOBS.get(result.ambush_level, [])
            mob = next((m for m in mobs if m.key == result.ambush_mob_key), None)
            if mob:
                combat_uc = CombatUseCases()
                penalty = AMBUSH_DEFEAT_PENALTIES["mining"][result.ambush_level]
                flee_lockout = AMBUSH_FLEE_LOCKOUT[result.ambush_level]
                battle, error = combat_uc.start_ambush(
                    user_id=ctx.author.id,
                    username=str(ctx.author),
                    mob=mob,
                    activity="mining",
                    activity_level=result.ambush_level,
                    penalty=penalty,
                    flee_lockout_turns=flee_lockout,
                )
                if battle:
                    battle_view = BattleView(battle, combat_uc, ctx.author.id, str(ctx.author))
                    embed = battle_view._create_embed()
                    msg = await ctx.send(embed=embed, view=battle_view)
                    battle_view.message = msg
                elif error:
                    await ctx.send(f"⚠️ {ctx.author.mention}, a {result.ambush_mob_emoji} **{result.ambush_mob_name}** ambushed you but you were too weak to fight! {error}")

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

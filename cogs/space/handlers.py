"""Space mining commands cog."""

import asyncio

from discord.ext import commands

from cogs.locations.check import require_location
from cogs.space.constants import SPACE_MINERAL_TABLES, SPACE_PLANETS
from cogs.space.use_case import SpaceUseCases


class SpaceCog(commands.Cog):
    """Commands for space mining."""

    def __init__(self, bot):
        self.bot = bot
        self.space = SpaceUseCases()

    @commands.command(name="launch")
    async def launch(self, ctx):
        """Launch into space with your rocket ship!"""
        if not await require_location(ctx, "starport_ziti"):
            return
        result = self.space.launch(ctx.author.id, str(ctx.author))

        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        # Countdown sequence
        msg = await ctx.send(f"🚀 {ctx.author.mention} is preparing for launch...\n**3...**")
        await asyncio.sleep(1)
        await msg.edit(content=f"🚀 {ctx.author.mention} is preparing for launch...\n**3... 2...**")
        await asyncio.sleep(1)
        await msg.edit(content=f"🚀 {ctx.author.mention} is preparing for launch...\n**3... 2... 1...**")
        await asyncio.sleep(1)
        await msg.edit(
            content=(
                f"🚀🔥 **LIFTOFF!** 🔥🚀\n\n"
                f"{ctx.author.mention} has blasted off into space!\n"
                f"🌕 **The Moon** is now available for space mining!\n\n"
                f"Use `!spacemine` to mine on the Moon\n"
                f"Use `!planets` to view available planets"
            )
        )

    @commands.command(name="spacemine")
    async def spacemine(self, ctx):
        """Mine for space ores on your active planet!"""
        if not await require_location(ctx, "starport_ziti"):
            return

        # Gear warning
        from cogs.combat.ambush_constants import SPACE_AMBUSH_MOBS
        from cogs.combat.use_case.gear_check import gear_warning
        active_planet = self.space.repo.get_active_space_planet(ctx.author.id)
        mobs = SPACE_AMBUSH_MOBS.get(active_planet, [])
        warning = gear_warning(ctx.author.id, mobs, self.space.repo)
        if warning:
            await ctx.send(warning)

        result = self.space.mine(ctx.author.id, str(ctx.author))

        if not result.success:
            await ctx.send(f"⏰ {ctx.author.mention}, {result.message}")
            return

        # Build header based on mineral value
        if result.stars_earned >= 500:
            header = "🎉 **COSMIC JACKPOT!** 🎉"
        elif result.stars_earned >= 200:
            header = "✨ **RARE SPACE FIND!** ✨"
        else:
            header = f"{result.planet_emoji} **Mining on {result.planet_name}...**"

        message = (
            f"{header}\n"
            f"{ctx.author.mention} mined {result.mineral_emoji} **{result.mineral_name}**!\n"
            f"Added to inventory! (sell value: **{result.stars_earned}** ⭐)\n"
            f"🎒 Bag: **{result.bag_count}/{result.bag_capacity}**"
        )

        message += f"\n💰 Wallet: **{result.new_balance}** stars"

        await ctx.send(message)

        # Handle ambush encounter
        if result.ambush_mob_key:
            from cogs.combat.ambush_constants import SPACE_AMBUSH_MOBS, AMBUSH_DEFEAT_PENALTIES, AMBUSH_FLEE_LOCKOUT
            from cogs.combat.use_case.combat import CombatUseCases
            from cogs.combat.handlers import BattleView, is_in_battle

            if not is_in_battle(ctx.author.id):
                mobs = SPACE_AMBUSH_MOBS.get(result.ambush_level, [])
                mob = next((m for m in mobs if m.key == result.ambush_mob_key), None)
                if mob:
                    combat_uc = CombatUseCases()
                    penalty = AMBUSH_DEFEAT_PENALTIES["space"][result.ambush_level]
                    flee_lockout = AMBUSH_FLEE_LOCKOUT[result.ambush_level]
                    battle, error = combat_uc.start_ambush(
                        user_id=ctx.author.id,
                        username=str(ctx.author),
                        mob=mob,
                        activity="space",
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

    @commands.command(name="planets")
    async def planets(self, ctx, planet: int = 0):
        """View or switch your active planet. Usage: !planets [number]"""
        if not self.space.has_launched(ctx.author.id):
            await ctx.send(
                f"❌ {ctx.author.mention}, you haven't launched into space yet! "
                f"Buy a 🚀 **Rocket Ship** from the `!store` and use `!launch`."
            )
            return

        if planet != 0:
            # Switch active planet
            success, msg = self.space.set_active_planet(ctx.author.id, planet)
            if success:
                planet_config = SPACE_PLANETS[planet]
                ambush_pct = int(planet_config["disaster_chance"] * 100)
                msg += f"\n⚔️ Ambush chance: **{ambush_pct}%** per mine"
                await ctx.send(f"🚀 {ctx.author.mention}, {msg}")
            else:
                await ctx.send(f"❌ {ctx.author.mention}, {msg}")
            return

        # Show planet info
        info = self.space.get_planet_info(ctx.author.id)

        lines = [f"🚀 **Space Planets** — {ctx.author.mention}\n"]

        for planet_num, planet_data in info.planets.items():
            ambush_pct = int(planet_data["disaster_chance"] * 100)
            if planet_num <= info.unlocked_planet:
                active = " ◀️" if planet_num == info.active_planet else ""
                lines.append(f"{planet_data['emoji']} **Planet {planet_num} — {planet_data['name']}** ✅{active} ⚔️ {ambush_pct}%")
            elif planet_num == info.unlocked_planet + 1:
                lines.append(f"🔒 **Planet {planet_num} — {planet_data['name']}** — *{planet_data['cost']} stars to unlock* ⚔️ {ambush_pct}%")
            else:
                lines.append(f"🔒 **Planet {planet_num} — {planet_data['name']}** — *Locked*")

        lines.append(f"\nUse `!planets <number>` to switch planets")
        lines.append(f"Use `!unlockplanet <number>` to unlock the next planet")
        lines.append(f"\n⚔️ = Ambush chance per mine (halved by Lucky Charm)")

        await ctx.send("\n".join(lines))

    @commands.command(name="unlockplanet")
    async def unlockplanet(self, ctx, planet: int = 0):
        """Unlock a new space planet. Usage: !unlockplanet <planet>"""
        if not await require_location(ctx, "starport_ziti", "noodle_town"):
            return
        if planet == 0:
            await ctx.send(f"❌ {ctx.author.mention}, please specify a planet to unlock! Usage: `!unlockplanet <number>`")
            return

        result = self.space.unlock_planet(ctx.author.id, str(ctx.author), planet)

        if result.success:
            planet_config = SPACE_PLANETS[result.planet]
            minerals = SPACE_MINERAL_TABLES[result.planet]["normal"]
            mineral_list = " ".join(f"{m.emoji} {m.name} ({m.stars}⭐)" for m in minerals)

            ambush_pct = int(planet_config["disaster_chance"] * 100)
            message = (
                f"🎊 {ctx.author.mention}, {result.message}\n"
                f"Cost: **{result.cost}** stars\n\n"
                f"**New space ores available:**\n{mineral_list}\n\n"
                f"⚔️ Ambush chance: **{ambush_pct}%** per mine"
            )

            await ctx.send(message)
        else:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(SpaceCog(bot))

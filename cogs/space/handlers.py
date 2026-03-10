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
    async def spacemine(self, ctx, use_item: str = ''):
        """Mine for space ores on your active planet!"""
        if not await require_location(ctx, "starport_ziti"):
            return
        result = self.space.mine(ctx.author.id, str(ctx.author), use_item)

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
            f"You earned **{result.stars_earned}** noodle stars! ⭐"
        )

        # Handle disaster messages
        if result.disaster:
            if result.disaster_protected:
                message += f"\n\n{result.disaster_header}\n{result.disaster_protected_msg}"
            else:
                message += f"\n\n{result.disaster_header}\n{result.disaster_unprotected_msg}"

        # Extra messages (e.g. heart of leviathan bank protection)
        for extra in result.extra_messages:
            message += f"\n{extra}"

        message += f"\nNew balance: **{result.new_balance}** stars!"

        await ctx.send(message)

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
                # Add bank risk warning for planets 3+
                max_bank_loss = max(h.bank_loss_pct for h in planet_config["hazards"])
                if max_bank_loss > 0:
                    warning = f"\n⚠️ **WARNING:** This planet has disasters that can take up to {int(max_bank_loss * 100)}% of your BANK! Use protection items!"
                    msg += warning
                await ctx.send(f"🚀 {ctx.author.mention}, {msg}")
            else:
                await ctx.send(f"❌ {ctx.author.mention}, {msg}")
            return

        # Show planet info
        info = self.space.get_planet_info(ctx.author.id)

        lines = [f"🚀 **Space Planets** — {ctx.author.mention}\n"]

        for planet_num, planet_data in info.planets.items():
            if planet_num <= info.unlocked_planet:
                active = " ◀️" if planet_num == info.active_planet else ""
                risk_warning = ""
                max_bank_loss = max(h.bank_loss_pct for h in planet_data["hazards"])
                if max_bank_loss > 0:
                    risk_warning = f" ⚠️ Bank risk: {int(max_bank_loss * 100)}%"
                lines.append(f"{planet_data['emoji']} **Planet {planet_num} — {planet_data['name']}** ✅{active}{risk_warning}")
            elif planet_num == info.unlocked_planet + 1:
                risk_warning = ""
                max_bank_loss = max(h.bank_loss_pct for h in planet_data["hazards"])
                if max_bank_loss > 0:
                    risk_warning = f" ⚠️ Bank risk: {int(max_bank_loss * 100)}%"
                lines.append(f"🔒 **Planet {planet_num} — {planet_data['name']}** — *{planet_data['cost']} stars to unlock*{risk_warning}")
            else:
                lines.append(f"🔒 **Planet {planet_num} — {planet_data['name']}** — *Locked*")

        lines.append(f"\nUse `!planets <number>` to switch planets")
        lines.append(f"Use `!unlockplanet <number>` to unlock the next planet")
        lines.append(f"\n💡 Planets 3-5 have disasters that can affect your bank balance!")

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

            message = (
                f"🎊 {ctx.author.mention}, {result.message}\n"
                f"Cost: **{result.cost}** stars\n\n"
                f"**New space ores available:**\n{mineral_list}"
            )

            # Add bank risk warning for planets with bank-affecting hazards
            max_bank_loss = max(h.bank_loss_pct for h in planet_config["hazards"])
            if max_bank_loss > 0:
                message += f"\n\n⚠️ **WARNING:** This planet has disasters that can take up to {int(max_bank_loss * 100)}% of your BANK balance! Keep protection items in your inventory!"

            await ctx.send(message)
        else:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(SpaceCog(bot))

"""Mining commands cog."""

from discord.ext import commands

from services.mining import MiningService


class MiningCog(commands.Cog):
    """Commands for mining minerals."""

    def __init__(self, bot):
        self.bot = bot
        self.mining = MiningService()

    @commands.command(name="mine")
    async def mine(self, ctx, use_item: str = None):
        """Mine for minerals to earn noodle stars!"""
        result = self.mining.mine(ctx.author.id, str(ctx.author), use_item)

        if not result.success:
            await ctx.send(f"⏰ {ctx.author.mention}, {result.message}")
            return

        # Create message based on mineral rarity
        if result.mineral_name == "Diamond":
            header = "🎉 **JACKPOT!** 🎉"
        elif result.mineral_name == "Gold":
            header = "✨ **RARE FIND!** ✨"
        else:
            header = "⛏️ **Mining...**"

        message = (
            f"{header}\n"
            f"{ctx.author.mention} mined {result.mineral_emoji} **{result.mineral_name}**!\n"
            f"You earned **{result.stars_earned}** noodle stars! ⭐"
        )

        # Handle disaster messages
        if result.disaster == "collapse":
            if result.disaster_protected:
                message += (
                    f"\n\n💥 **MINE COLLAPSE!** 💥\n"
                    f"🪖 Your helmet protected you from the collapse!\n"
                    f"*Your helmet was destroyed in the process.*"
                )
            else:
                message += (
                    f"\n\n💥 **MINE COLLAPSE!** 💥\n"
                    f"You were caught in the collapse and lost **{result.stars_lost}** stars! 😱\n"
                    f"💀 **All your items were destroyed!**\n"
                    f"💡 *Buy a helmet from the !store to protect yourself!*"
                )

        elif result.disaster == "goblin":
            if result.disaster_protected:
                message += (
                    f"\n\n👹 **GOBLIN ATTACK!** 👹\n"
                    f"⚔️ You fought off the goblin with your sword!\n"
                    f"*Your sword broke in the battle.*"
                )
            else:
                message += (
                    f"\n\n👹 **GOBLIN ATTACK!** 👹\n"
                    f"The goblin stole **{result.stars_lost}** stars from you! 😱\n"
                    f"💀 **The goblin destroyed all your items!**\n"
                    f"💡 *Buy a sword from the !store to protect yourself!*"
                )

        message += f"\nNew balance: **{result.new_balance}** stars!"

        await ctx.send(message)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(MiningCog(bot))

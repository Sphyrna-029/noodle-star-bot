"""Alien abduction random event cog."""

import random

from discord.ext import commands

from cogs.space.constants import SPACE_ABDUCTION_BONUS
from database.repository import UserRepository


ABDUCTION_CHANCE = 0.0005 # ~%2 per day

ABDUCTION_MESSAGES = [
    (
        "🛸 **ALIEN ABDUCTION!** 🛸\n\n"
        "{mention} was minding their own business when a tractor beam "
        "locked onto them mid-command! The aliens were particularly interested "
        "in their noodle stars and confiscated **{stars_lost} stars** from their wallet.\n\n"
        "They also took all your items for \"galactic research purposes.\"\n\n"
        "You were returned 3 hours later with no memory, weird tan lines, "
        "and a strong craving for space noodles. 👽\n\n"
        "🏦 Bank stars were safe — the aliens couldn't crack the PIN."
    ),
    (
        "👽 **YOU'VE BEEN PROBED... FINANCIALLY!** 👽\n\n"
        "{mention} just got snatched up by a UFO! The alien captain, "
        "who introduced himself as Zorp, said your **{stars_lost} wallet stars** "
        "were needed to fuel their hyperdrive.\n\n"
        "Your items? Gone. Zorp's kids wanted souvenirs from Earth.\n\n"
        "You were dropped back off in a Walmart parking lot at 3 AM "
        "wearing a tinfoil hat you don't remember putting on.\n\n"
        "🏦 Good news: the aliens don't believe in banks, so yours is untouched."
    ),
    (
        "🌌 **CLOSE ENCOUNTER OF THE WORST KIND** 🌌\n\n"
        "A flying saucer just yeeted {mention} into orbit! "
        "During the ride, the aliens made you play space poker and you lost "
        "**{stars_lost} stars** because apparently you can't bluff a telepathic squid.\n\n"
        "They also emptied your pockets. Every last item. Gone.\n\n"
        "They dropped you back on Earth with a bumper sticker that reads "
        "\"I got abducted by aliens and all I got was this crippling debt.\"\n\n"
        "🏦 At least your bank account survived — alien wifi couldn't reach it."
    ),
    (
        "🛸 **BEAM ME UP, SCOTTY — WAIT, NO!** 🛸\n\n"
        "{mention} has been abducted by aliens who needed **{stars_lost} stars** "
        "to pay their space parking tickets!\n\n"
        "Your inventory was seized at the intergalactic customs checkpoint. "
        "Apparently raw potatoes are considered a controlled substance on Planet Glorb.\n\n"
        "You woke up in your bed 6 hours later with a receipt written in alien "
        "that roughly translates to \"lmao thanks for the stars, nerd.\"\n\n"
        "🏦 Your bank was spared — the aliens' hacking skills were \"still loading.\""
    ),
    (
        "👾 **EXTRATERRESTRIAL MUGGING!** 👾\n\n"
        "Three grey aliens in a trenchcoat just jumped {mention} in broad daylight! "
        "They demanded your wallet and you had no choice but to hand over "
        "**{stars_lost} stars**.\n\n"
        "They also took all your items and called them \"primitive but amusing.\"\n\n"
        "Before vanishing, the tallest one said \"tell anyone about this and we'll "
        "abduct your pets next.\" Then they flew away in a ship shaped like a noodle bowl.\n\n"
        "🏦 They couldn't access your bank — turns out aliens have terrible credit scores."
    ),
    (
        "🛸 **INTERGALACTIC REPO MAN** 🛸\n\n"
        "Turns out {mention} owed the Galactic Federation **{stars_lost} stars** "
        "in unpaid taxes from a past life on Planet Ziltoid!\n\n"
        "A very polite alien in a suit beamed you up, showed you the paperwork "
        "(written in crayon, oddly), and cleaned out your wallet and inventory.\n\n"
        "He gave you a lollipop shaped like Saturn and a pamphlet titled "
        "\"So You've Been Involuntarily Relocated: A Guide.\"\n\n"
        "🏦 Your bank was exempt — interstellar law doesn't cover Earth banks. Yet."
    ),
]


class AlienAbductionCog(commands.Cog):
    """Random alien abduction event that can trigger on any command."""

    def __init__(self, bot):
        self.bot = bot
        self.repo = UserRepository()

    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Listener that fires before every command — 0.5% alien abduction chance."""
        if ctx.author.bot:
            return

        # Don't trigger during banking commands
        if ctx.command and ctx.command.name in ("deposit", "withdraw"):
            return

        # Space explorers have higher abduction chance
        chance = ABDUCTION_CHANCE
        inventory = self.repo.get_user_inventory(ctx.author.id)
        if inventory.get("space_planet_level", 0) > 0:
            chance += SPACE_ABDUCTION_BONUS

        if random.random() > chance:
            return

        # Get the user's current data
        user = self.repo.get_user(ctx.author.id, str(ctx.author))
        stars_lost = user.stars

        if stars_lost == 0 and all(v == 0 for k, v in user.inventory.items()):
            # Nothing to lose — aliens aren't interested in broke people
            return

        # Check for ray-gun protection (saves items, still lose stars)
        inventory = self.repo.get_user_inventory(ctx.author.id)
        ray_gun_uses = inventory.get("ray_gun", 0)

        if ray_gun_uses > 0:
            # Ray-gun saves items but stars are still lost
            self.repo.update_user_stars(ctx.author.id, str(ctx.author), 0)
            self.repo.update_user_inventory(ctx.author.id, "ray_gun", ray_gun_uses - 1)
            remaining = ray_gun_uses - 1

            await ctx.send(
                f"🛸 **ALIEN ABDUCTION!** 🛸\n\n"
                f"{ctx.author.mention} was beamed up by aliens! They took **{stars_lost} stars** "
                f"from your wallet...\n\n"
                f"🔫 But you pulled out your **Ray-Gun** and blasted them before they could "
                f"touch your items! The aliens fled in terror.\n"
                f"*Your ray-gun is running low on charge.* ({remaining} uses remaining)\n\n"
                f"🏦 Bank stars were safe — the aliens couldn't crack the PIN."
            )
            return

        # Wipe wallet stars (set to 0)
        self.repo.update_user_stars(ctx.author.id, str(ctx.author), 0)

        # Wipe all inventory items (aliens take EVERYTHING)
        self.repo.clear_all_items(ctx.author.id)

        # Pick a random abduction message
        message = random.choice(ABDUCTION_MESSAGES).format(
            mention=ctx.author.mention,
            stars_lost=stars_lost,
        )

        await ctx.send(message)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(AlienAbductionCog(bot))

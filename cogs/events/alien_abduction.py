"""Alien abduction random event cog.

With a ray-gun the player fights the alien in interactive combat (both
sides get +75 ATK).  Without a ray-gun the alien auto-wins and the
standard alien defeat penalties are applied immediately.
"""

import random

from discord.ext import commands

from cogs.combat.ambush_constants import (
    ALIEN_ATK_BONUS, ALIEN_MOB, AMBUSH_DEFEAT_PENALTIES,
)
from cogs.space.constants import SPACE_ABDUCTION_CHANCE
from database.repository import UserRepository


ABDUCTION_CHANCE = 0.0005  # ~2% per day

NO_RAYGUN_MESSAGES = [
    (
        "🛸 **ALIEN ABDUCTION!** 🛸\n\n"
        "{mention} was minding their own business when a tractor beam "
        "locked onto them mid-command! Without a **Ray-Gun** you were "
        "helpless against the 👽 **Alien Raider**!\n\n"
        "They confiscated **{stars_lost} stars** from your wallet and took "
        "all your items for \"galactic research purposes.\"\n\n"
        "You were returned 3 hours later with no memory, weird tan lines, "
        "and a strong craving for space noodles."
    ),
    (
        "👽 **YOU'VE BEEN PROBED... FINANCIALLY!** 👽\n\n"
        "{mention} just got snatched up by a UFO! The alien captain, "
        "Zorp, overpowered you easily — you didn't even have a **Ray-Gun** "
        "to fight back.\n\n"
        "They took **{stars_lost} wallet stars** and all your items. "
        "Zorp's kids wanted souvenirs from Earth.\n\n"
        "You were dropped in a Walmart parking lot at 3 AM "
        "wearing a tinfoil hat you don't remember putting on."
    ),
    (
        "🌌 **CLOSE ENCOUNTER OF THE WORST KIND** 🌌\n\n"
        "A flying saucer just yeeted {mention} into orbit! "
        "Without a **Ray-Gun** to defend yourself, the alien "
        "took **{stars_lost} stars** and emptied your pockets.\n\n"
        "They dropped you back on Earth with a bumper sticker that reads "
        "\"I got abducted by aliens and all I got was this crippling debt.\""
    ),
]

RAYGUN_INTRO_MESSAGES = [
    (
        "🛸 **ALIEN ABDUCTION!** 🛸\n\n"
        "{mention} was beamed up by aliens! But you whip out your "
        "🔫 **Ray-Gun** — let's see who wins this fight!\n\n"
        "*Both sides are supercharged with alien energy (+{atk_bonus} ATK each)!*\n"
        "Ray-Gun charge: {remaining} uses remaining."
    ),
    (
        "👽 **ALIEN ENCOUNTER!** 👽\n\n"
        "{mention} got snatched by a UFO, but this time you came prepared "
        "with your 🔫 **Ray-Gun**! The alien energy field boosts both fighters "
        "(+{atk_bonus} ATK).\n\n"
        "Ray-Gun charge: {remaining} uses remaining. **FIGHT!**"
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

        # Space explorers have per-planet abduction chance
        inventory = self.repo.get_user_inventory(ctx.author.id)
        space_level = inventory.get("space_planet_level", 0)
        if space_level > 0:
            chance = SPACE_ABDUCTION_CHANCE.get(space_level, ABDUCTION_CHANCE)
        else:
            chance = ABDUCTION_CHANCE

        if random.random() > chance:
            return

        # Get the user's current data
        user = self.repo.get_user(ctx.author.id, str(ctx.author))
        stars_lost = user.stars

        # Check if user has anything worth stealing
        inventory = self.repo.get_user_inventory(ctx.author.id)
        equipment = self.repo.get_user_equipment(ctx.author.id)
        bag_count = self.repo.get_inventory_count(ctx.author.id)
        if stars_lost == 0 and bag_count == 0 and not equipment:
            return
        ray_gun_uses = inventory.get("ray_gun", 0)

        if ray_gun_uses > 0:
            # ── Ray-gun: interactive combat with +75 ATK both sides ──
            self.repo.update_user_inventory(ctx.author.id, "ray_gun", ray_gun_uses - 1)
            remaining = ray_gun_uses - 1

            intro = random.choice(RAYGUN_INTRO_MESSAGES).format(
                mention=ctx.author.mention,
                atk_bonus=ALIEN_ATK_BONUS,
                remaining=remaining,
            )
            await ctx.send(intro)

            from cogs.combat.use_case.combat import CombatUseCases
            from cogs.combat.handlers import BattleView

            combat_uc = CombatUseCases()
            penalty = AMBUSH_DEFEAT_PENALTIES["alien"][0]
            battle, error = combat_uc.start_ambush(
                user_id=ctx.author.id,
                username=str(ctx.author),
                mob=ALIEN_MOB,
                activity="alien",
                activity_level=0,
                penalty=penalty,
                flee_lockout_turns=5,
                atk_bonus=ALIEN_ATK_BONUS,
            )
            if battle:
                battle_view = BattleView(battle, combat_uc, ctx.author.id, str(ctx.author))
                embed = battle_view._create_embed()
                msg = await ctx.send(embed=embed, view=battle_view)
                battle_view.message = msg
            elif error:
                # Too weak to fight — auto-lose
                await self._apply_auto_loss(ctx, stars_lost)
            return

        # ── No ray-gun: auto-lose ──
        await self._apply_auto_loss(ctx, stars_lost)

    async def _apply_auto_loss(self, ctx, stars_lost: int):
        """Apply alien defeat penalties without combat (no ray-gun or too weak)."""
        from cogs.combat.use_case.combat import CombatUseCases
        from cogs.combat.dto import BattleState, AmbushContext

        penalty = AMBUSH_DEFEAT_PENALTIES["alien"][0]

        # Build a minimal BattleState so resolve_defeat can apply penalties
        ambush_ctx = AmbushContext(
            activity="alien",
            activity_level=0,
            penalty=penalty,
            flee_lockout_turns=0,
        )
        battle = BattleState(
            mob_key=ALIEN_MOB.key,
            mob_name=ALIEN_MOB.name,
            mob_emoji=ALIEN_MOB.emoji,
            dungeon_level=0,
            player_hp=0,
            player_max_hp=100,
            player_stamina=0,
            player_max_stamina=100,
            player_attack=0,
            player_defense=0,
            mob_hp=ALIEN_MOB.hp,
            mob_max_hp=ALIEN_MOB.hp,
            mob_attack=ALIEN_MOB.attack,
            mob_defense=ALIEN_MOB.defense,
            mob_stamina=ALIEN_MOB.stamina,
            mob_max_stamina=ALIEN_MOB.stamina,
            finished=True,
            player_won=False,
            ambush=ambush_ctx,
        )

        combat_uc = CombatUseCases()
        result = combat_uc.resolve_defeat(ctx.author.id, str(ctx.author), battle)

        message = random.choice(NO_RAYGUN_MESSAGES).format(
            mention=ctx.author.mention,
            stars_lost=stars_lost,
        )
        if result.bank_loss > 0:
            message += f"\n🏦 The aliens also raided your bank for **{result.bank_loss}** stars!"
        else:
            message += "\n🏦 Bank stars were safe — the aliens couldn't crack the PIN."

        await ctx.send(message)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(AlienAbductionCog(bot))

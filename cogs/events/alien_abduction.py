"""Alien abduction random event cog.

Triggers at 1% chance when a player travels away from Noodle Town.
With a ray-gun the player fights the alien in interactive combat (both
sides get +75 ATK).  Without a ray-gun the alien auto-wins and the
standard alien defeat penalties are applied immediately.
"""

import random

import discord
from discord.ext import commands

from cogs.combat.ambush_constants import (
    ALIEN_ATK_BONUS, ALIEN_MOB, AMBUSH_DEFEAT_PENALTIES,
)
from database.repository import UserRepository


ABDUCTION_CHANCE = 0.01  # 1% on travel away from Noodle Town

NO_RAYGUN_MESSAGES = [
    (
        "🛸 **ALIEN ABDUCTION!** 🛸\n\n"
        "{mention} was traveling when a tractor beam "
        "locked onto them! Without a **Ray-Gun** you were "
        "helpless against the 👽 **Alien Raider**!\n\n"
        "They confiscated **{stars_lost} stars** from your wallet!\n\n"
        "You were returned 3 hours later with no memory, weird tan lines, "
        "and a strong craving for space noodles."
    ),
    (
        "👽 **YOU'VE BEEN PROBED... FINANCIALLY!** 👽\n\n"
        "{mention} just got snatched up by a UFO mid-travel! The alien captain, "
        "Zorp, overpowered you easily — you didn't even have a **Ray-Gun** "
        "to fight back.\n\n"
        "They took **{stars_lost} wallet stars**. "
        "Zorp's kids wanted souvenirs from Earth.\n\n"
        "You were dropped in a Walmart parking lot at 3 AM "
        "wearing a tinfoil hat you don't remember putting on."
    ),
    (
        "🌌 **CLOSE ENCOUNTER OF THE WORST KIND** 🌌\n\n"
        "A flying saucer just yeeted {mention} into orbit mid-travel! "
        "Without a **Ray-Gun** to defend yourself, the alien "
        "took **{stars_lost} stars** from your wallet.\n\n"
        "They dropped you back on Earth with a bumper sticker that reads "
        "\"I got abducted by aliens and all I got was this crippling debt.\""
    ),
]

RAYGUN_INTRO_MESSAGES = [
    (
        "🛸 **ALIEN ABDUCTION!** 🛸\n\n"
        "{mention} was beamed up by aliens while traveling! But you whip out your "
        "🔫 **Ray-Gun** — let's see who wins this fight!\n\n"
        "*Both sides are supercharged with alien energy (+{atk_bonus} ATK each)!*\n"
        "Ray-Gun charge: {remaining} uses remaining."
    ),
    (
        "👽 **ALIEN ENCOUNTER!** 👽\n\n"
        "{mention} got snatched by a UFO mid-travel, but this time you came prepared "
        "with your 🔫 **Ray-Gun**! The alien energy field boosts both fighters "
        "(+{atk_bonus} ATK).\n\n"
        "Ray-Gun charge: {remaining} uses remaining. **FIGHT!**"
    ),
]


class AlienAbductionCog(commands.Cog):
    """Random alien abduction event that triggers when traveling away from Noodle Town."""

    def __init__(self, bot):
        self.bot = bot
        self.repo = UserRepository()

    async def try_abduction(self, ctx_or_interaction):
        """Called by the travel system when leaving Noodle Town. Returns True if abduction happened.

        Accepts either a commands.Context or discord.Interaction.
        """
        if random.random() > ABDUCTION_CHANCE:
            return False

        # Normalize ctx vs interaction
        if isinstance(ctx_or_interaction, discord.Interaction):
            user = ctx_or_interaction.user
            send = ctx_or_interaction.followup.send
        else:
            user = ctx_or_interaction.author
            send = ctx_or_interaction.send

        user_id = user.id
        username = str(user)
        mention = user.mention

        # Check if user has anything worth stealing
        user_data = self.repo.get_user(user_id, username)
        if user_data.stars == 0:
            return False

        inventory = self.repo.get_user_inventory(user_id)
        ray_gun_uses = inventory.get("ray_gun", 0)

        from cogs.combat.use_case.combat import CombatUseCases
        from cogs.combat.handlers import BattleView, is_in_battle

        if is_in_battle(user_id):
            return False

        if ray_gun_uses > 0:
            # ── Ray-gun: interactive combat with +75 ATK both sides ──
            combat_uc = CombatUseCases()
            penalty = AMBUSH_DEFEAT_PENALTIES["alien"][0]
            battle, error = combat_uc.start_ambush(
                user_id=user_id,
                username=username,
                mob=ALIEN_MOB,
                activity="alien",
                activity_level=0,
                penalty=penalty,
                flee_lockout_turns=5,
                atk_bonus=ALIEN_ATK_BONUS,
            )
            if battle:
                # Consume ray-gun only after confirming fight can start
                self.repo.update_user_inventory(user_id, "ray_gun", ray_gun_uses - 1)
                remaining = ray_gun_uses - 1

                intro = random.choice(RAYGUN_INTRO_MESSAGES).format(
                    mention=mention,
                    atk_bonus=ALIEN_ATK_BONUS,
                    remaining=remaining,
                )
                await send(intro)

                battle_view = BattleView(battle, combat_uc, user_id, username)
                embed = battle_view._create_embed()
                msg = await send(embed=embed, view=battle_view)
                battle_view.message = msg
                return True
            elif error:
                # Too weak to fight — auto-lose (ray-gun NOT consumed)
                await self._apply_auto_loss(user_id, username, mention, send)
                return True
            return False

        # ── No ray-gun: auto-lose ──
        await self._apply_auto_loss(user_id, username, mention, send)
        return True

    async def _apply_auto_loss(self, user_id, username, mention, send):
        """Apply alien defeat penalties without combat (no ray-gun or too weak)."""
        from cogs.combat.use_case.combat import CombatUseCases
        from cogs.combat.dto import BattleState, AmbushContext
        from cogs.combat.constants import BASE_HP, BASE_STAMINA

        combat_uc = CombatUseCases()
        penalty = AMBUSH_DEFEAT_PENALTIES["alien"][0]

        # Read actual player stats to avoid corrupting stamina
        stats = combat_uc.repo.get_combat_stats(user_id)

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
            player_hp=1,
            player_max_hp=stats["max_hp"] or BASE_HP,
            player_stamina=stats["current_stamina"] or BASE_STAMINA,
            player_max_stamina=stats["max_stamina"] or BASE_STAMINA,
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

        result = combat_uc.resolve_defeat(user_id, username, battle)

        message = random.choice(NO_RAYGUN_MESSAGES).format(
            mention=mention,
            stars_lost=result.stars_lost,
        )
        message += "\n🏦 Bank stars were safe — the aliens couldn't crack the PIN."

        await send(message)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(AlienAbductionCog(bot))

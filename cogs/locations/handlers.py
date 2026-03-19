"""Location and travel commands cog."""

import discord
from discord.ext import commands

from cogs.locations.constants import LOCATIONS
from cogs.locations.use_case import LocationUseCases
from database.repository import UserRepository


def _get_location_mobs(user_id: int, location_key: str, repo: UserRepository = None) -> list:
    """Return the ambush/dungeon mobs relevant to a location for gear checking."""
    repo = repo or UserRepository()
    if location_key == "crystal_cave":
        from cogs.combat.ambush_constants import MINING_AMBUSH_MOBS
        level = repo.get_active_mine_level(user_id)
        return MINING_AMBUSH_MOBS.get(level, [])
    elif location_key == "starfish_bay":
        from cogs.combat.ambush_constants import FISHING_AMBUSH_MOBS
        level = repo.get_active_fish_level(user_id)
        return FISHING_AMBUSH_MOBS.get(level, [])
    elif location_key == "starport_ziti":
        from cogs.combat.ambush_constants import SPACE_AMBUSH_MOBS
        planet = repo.get_active_space_planet(user_id)
        return SPACE_AMBUSH_MOBS.get(planet, [])
    elif location_key == "noodle_colosseum":
        from cogs.combat.constants import MOBS_BY_LEVEL
        stats = repo.get_combat_stats(user_id)
        level = stats["active_combat_level"]
        return MOBS_BY_LEVEL.get(level, [])
    return []


async def _check_alien_arrival(bot, ctx_or_interaction, new_location: str):
    """Pre-roll alien encounter when arriving at Noodle Town and warn if telescope owned."""
    if new_location != "noodle_town":
        return
    cog = bot.get_cog("AlienAbductionCog")
    if cog is None:
        return

    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        send = ctx_or_interaction.followup.send
    else:
        user = ctx_or_interaction.author
        send = ctx_or_interaction.send

    has_alien = cog.pre_roll_alien(user.id)
    if has_alien:
        repo = UserRepository()
        inv = repo.get_user_inventory(user.id)
        if inv.get("telescope", 0) > 0:
            from cogs.events.alien_abduction import TELESCOPE_WARNING
            if isinstance(ctx_or_interaction, discord.Interaction):
                await send(TELESCOPE_WARNING, ephemeral=True)
            else:
                await send(TELESCOPE_WARNING)


async def _check_abduction(bot, ctx_or_interaction, previous_location: str, new_location: str):
    """Check for alien abduction when traveling away from Noodle Town."""
    if previous_location != "noodle_town" or new_location == "noodle_town":
        return
    cog = bot.get_cog("AlienAbductionCog")
    if cog is None:
        return
    await cog.try_abduction(ctx_or_interaction)


class TravelButton(discord.ui.Button):
    """Button for traveling to a specific location."""

    def __init__(self, location_key: str, disabled: bool = False):
        loc = LOCATIONS[location_key]
        _ROW_0 = ("noodle_town", "crystal_cave", "starfish_bay")
        super().__init__(
            label=loc.name,
            emoji=loc.emoji,
            style=discord.ButtonStyle.primary if not disabled else discord.ButtonStyle.secondary,
            disabled=disabled,
            row=0 if location_key in _ROW_0 else 1,
        )
        self.location_key = location_key

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, TravelView):
            await interaction.response.send_message(
                "This menu has expired. Use `!travel` to open a new one.",
                ephemeral=True,
            )
            return

        if interaction.user.id != view.author_id:
            await interaction.response.send_message(
                "This isn't your travel menu! Use `!travel` to open your own.",
                ephemeral=True,
            )
            return

        location_uc = LocationUseCases()
        previous = location_uc.get_location(interaction.user.id)
        result = location_uc.travel(interaction.user.id, self.location_key)

        if not result.success:
            await interaction.response.edit_message(
                embed=_build_error_embed(result.message),
                view=view,
            )
            return

        # Rebuild view with updated location
        new_view = TravelView(view.author_id, self.location_key, has_aether=view.has_aether)
        loc = LOCATIONS[self.location_key]
        embed = discord.Embed(
            title=f"🚶 Traveled to {loc.name} {loc.emoji}",
            description=f"{loc.description}\n\nSelect another destination or close this menu.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"📍 You are now at {loc.name}")
        await interaction.response.edit_message(embed=embed, view=new_view)
        await _check_alien_arrival(interaction.client, interaction, self.location_key)
        await _check_abduction(interaction.client, interaction, previous, self.location_key)

        # Gear warning for dangerous locations
        from cogs.combat.use_case.gear_check import gear_warning
        mobs = _get_location_mobs(interaction.user.id, self.location_key)
        warning = gear_warning(interaction.user.id, mobs)
        if warning:
            await interaction.followup.send(warning, ephemeral=True)


class TravelView(discord.ui.View):
    """Button-based travel menu showing all locations."""

    def __init__(self, author_id: int, current_location: str, has_aether: bool = True, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.current_location = current_location
        self.has_aether = has_aether

        for loc_key in LOCATIONS:
            if loc_key == "aetherdepths" and not has_aether:
                continue
            is_current = loc_key == current_location
            self.add_item(TravelButton(loc_key, disabled=is_current))


def _build_travel_embed(current_location: str, has_aether: bool = True) -> discord.Embed:
    loc = LOCATIONS[current_location]
    embed = discord.Embed(
        title="🗺️ World Map",
        description=f"📍 Current Location: **{loc.name}** {loc.emoji}\n\nSelect a destination to travel.",
        color=discord.Color.blue(),
    )

    lines = []
    for loc_data in LOCATIONS.values():
        if loc_data.key == "aetherdepths" and not has_aether:
            continue
        marker = " ◀️ *you are here*" if loc_data.key == current_location else ""
        lines.append(f"{loc_data.emoji} **{loc_data.name}** — {loc_data.description}{marker}")

    embed.add_field(name="Locations", value="\n".join(lines), inline=False)
    return embed


def _build_error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="❌ Can't Travel",
        description=message,
        color=discord.Color.red(),
    )


class LocationsCog(commands.Cog):
    """Commands for traveling between locations."""

    def __init__(self, bot):
        self.bot = bot
        self.locations = LocationUseCases()

    _TRAVEL_ALIASES: dict[str, str] = {
        # Noodle Town
        "town": "noodle_town", "noodle": "noodle_town", "noodle_town": "noodle_town",
        "noodletown": "noodle_town", "home": "noodle_town", "shop": "noodle_town",
        "store": "noodle_town", "bank": "noodle_town", "gamble": "noodle_town",
        # Crystal Cave
        "mine": "crystal_cave", "mining": "crystal_cave", "cave": "crystal_cave",
        "crystal": "crystal_cave", "crystal_cave": "crystal_cave",
        # Starfish Bay
        "fish": "starfish_bay", "fishing": "starfish_bay", "bay": "starfish_bay",
        "starfish": "starfish_bay", "starfish_bay": "starfish_bay",
        # Fusilli Farms
        "farm": "fusilli_farms", "farming": "fusilli_farms", "farms": "fusilli_farms",
        "fusilli": "fusilli_farms", "fusilli_farms": "fusilli_farms",
        # Starport Ziti
        "space": "starport_ziti", "spacemine": "starport_ziti", "starport": "starport_ziti",
        "ziti": "starport_ziti", "starport_ziti": "starport_ziti", "launch": "starport_ziti",
        # Noodle Colosseum
        "colosseum": "noodle_colosseum", "fight": "noodle_colosseum", "combat": "noodle_colosseum",
        "arena": "noodle_colosseum", "noodle_colosseum": "noodle_colosseum",
        "dungeon": "noodle_colosseum", "battle": "noodle_colosseum",
    }

    @commands.command(name="travel", aliases=["t"])
    async def travel(self, ctx, *, destination: str = ""):
        """Travel to a location. Usage: !t <place> or !travel for the menu."""
        if not destination:
            current = self.locations.get_location(ctx.author.id)
            repo = UserRepository()
            stats = repo.get_combat_stats(ctx.author.id)
            has_aether = stats["combat_level"] >= 5
            view = TravelView(ctx.author.id, current, has_aether=has_aether)
            embed = _build_travel_embed(current, has_aether=has_aether)
            await ctx.send(embed=embed, view=view)
            return

        loc_key = self._TRAVEL_ALIASES.get(destination.strip().lower())
        if loc_key is None:
            await ctx.send(
                f"❌ {ctx.author.mention}, unknown destination **{destination}**.\n"
                f"Try: `town`, `mine`, `fish`, `farm`, `space` — or just `!t` for the menu."
            )
            return

        previous = self.locations.get_location(ctx.author.id)
        result = self.locations.travel(ctx.author.id, loc_key)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        loc = LOCATIONS[loc_key]
        await ctx.send(f"🚶 {ctx.author.mention} traveled to **{loc.name}** {loc.emoji}")
        await _check_alien_arrival(self.bot, ctx, loc_key)
        await _check_abduction(self.bot, ctx, previous, loc_key)

        # Gear warning for dangerous locations
        from cogs.combat.use_case.gear_check import gear_warning
        mobs = _get_location_mobs(ctx.author.id, loc_key)
        warning = gear_warning(ctx.author.id, mobs)
        if warning:
            await ctx.send(warning)

    @commands.command(name="where")
    async def where(self, ctx, member: discord.Member = None):
        """Check your current location (or another player's)."""
        target = member or ctx.author
        current = self.locations.get_location(target.id)
        loc = LOCATIONS.get(current)

        if loc is None:
            await ctx.send(f"📍 {target.mention} is somewhere unknown...")
            return

        if target.id == ctx.author.id:
            await ctx.send(f"📍 {ctx.author.mention}, you are at **{loc.name}** {loc.emoji}")
        else:
            await ctx.send(f"📍 {target.display_name} is at **{loc.name}** {loc.emoji}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(LocationsCog(bot))

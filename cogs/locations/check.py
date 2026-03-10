"""Location check helper for gating commands by location."""

import discord

from cogs.locations.constants import LOCATIONS
from cogs.locations.use_case import LocationUseCases


class _TravelPromptView(discord.ui.View):
    """Yes/No buttons to travel when a command fails due to wrong location."""

    def __init__(self, author_id: int, destination: str, location_uc: LocationUseCases,
                 timeout: float = 60):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.destination = destination
        self.location_uc = location_uc

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your prompt!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Yes, travel there", style=discord.ButtonStyle.success, emoji="🚶")
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = self.location_uc.travel(interaction.user.id, self.destination)
        loc = LOCATIONS[self.destination]

        for child in self.children:
            child.disabled = True

        if result.success:
            await interaction.response.edit_message(
                content=f"🚶 {interaction.user.mention} traveled to **{loc.name}** {loc.emoji}! Try your command again.",
                view=self,
            )
        else:
            await interaction.response.edit_message(
                content=f"❌ {interaction.user.mention}, {result.message}",
                view=self,
            )
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"👍 Staying put.", view=self
        )
        self.stop()

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True


async def require_location(ctx, *required_locations: str) -> bool:
    """Check if user is at one of the required locations.

    Sends an error message with travel buttons and returns False if not.
    Returns True if the user is at a valid location.
    """
    location_uc = LocationUseCases()
    current = location_uc.get_location(ctx.author.id)

    if current in required_locations:
        return True

    names = []
    for loc_key in required_locations:
        loc = LOCATIONS[loc_key]
        names.append(f"**{loc.name}** {loc.emoji}")

    location_str = " or ".join(names)

    # Pick the first required location as the travel destination
    dest = required_locations[0]
    dest_loc = LOCATIONS[dest]

    view = _TravelPromptView(ctx.author.id, dest, location_uc)
    await ctx.send(
        f"❌ {ctx.author.mention}, you need to be at {location_str} to do that!\n"
        f"Travel to **{dest_loc.name}** {dest_loc.emoji}?",
        view=view,
    )
    return False

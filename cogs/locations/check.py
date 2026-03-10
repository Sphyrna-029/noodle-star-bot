"""Location check helper for gating commands by location."""

from cogs.locations.constants import LOCATIONS
from cogs.locations.use_case import LocationUseCases


async def require_location(ctx, *required_locations: str) -> bool:
    """Check if user is at one of the required locations.

    Sends an error message and returns False if not.
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
    await ctx.send(
        f"❌ {ctx.author.mention}, you need to be at {location_str} to do that!\n"
        f"Use `!travel` to open the travel menu."
    )
    return False

"""Discord command checks for Noodle Star Bot."""

from discord.ext import commands


def is_moderator():
    """
    Check if the user has moderator permissions.

    Checks for the 'moderate_members' permission.
    """

    async def predicate(ctx):
        return ctx.author.guild_permissions.moderate_members

    return commands.check(predicate)

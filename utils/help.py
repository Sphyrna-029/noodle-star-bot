"""Custom embed-based help command for Noodle Star Bot."""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

import discord
from discord.ext import commands


class NoodleHelpCommand(commands.HelpCommand):
    """Help command that renders a compact embed grouped by cog."""

    # Desired category order (match user preference)
    CATEGORY_ORDER = [
        "Economy",
        "Gambling",
        "Mining",
        "Fishing",
        "Shop",
        "Moderator",
        "Other",
    ]

    def __init__(self):
        super().__init__(no_category="Other")

    # --- Formatting helpers -------------------------------------------------

    def _clean_cog_name(self, cog: Optional[commands.Cog]) -> str:
        if cog is None:
            return self.no_category or "Other"
        name = getattr(cog, "qualified_name", None) or cog.__class__.__name__
        if name.endswith("Cog"):
            name = name[:-3]
        return name or (self.no_category or "Other")

    def _format_command_line(self, command: commands.Command) -> str:
        # Include prefix + signature for usage
        signature = self.get_command_signature(command)
        summary = command.help or command.short_doc or "No description"
        return f"`{signature}` — {summary}"

    def _sort_categories(self, categories: Iterable[str]) -> List[str]:
        order_index = {name: i for i, name in enumerate(self.CATEGORY_ORDER)}
        return sorted(
            categories,
            key=lambda name: (order_index.get(name, 999), name.lower()),
        )

    def _sort_commands(self, cmds: Iterable[commands.Command]) -> List[commands.Command]:
        return sorted(cmds, key=lambda c: c.name)

    # --- Send helpers --------------------------------------------------------

    async def send_bot_help(self, mapping):
        ctx = self.context
        embed = discord.Embed(
            title="Noodle Star Bot Commands",
            description="Here are the available commands grouped by category.",
            color=discord.Color.blurple(),
        )

        # Build category -> commands mapping
        category_map: dict[str, List[commands.Command]] = {}
        for cog, cmds in mapping.items():
            filtered = await self.filter_commands(cmds, sort=False)
            if not filtered:
                continue
            category = self._clean_cog_name(cog)
            category_map.setdefault(category, []).extend(filtered)

        # Render fields in preferred order
        for category in self._sort_categories(category_map.keys()):
            commands_list = self._sort_commands(category_map[category])
            lines = [self._format_command_line(cmd) for cmd in commands_list]
            value = "\n".join(lines) if lines else "No commands."
            embed.add_field(name=category, value=value, inline=False)

        embed.set_footer(
            text="Use !help <command> for details • Use !help <category> for a category"
        )

        await ctx.send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        ctx = self.context
        embed = discord.Embed(
            title=f"Command: {command.qualified_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Usage",
            value=f"`{self.get_command_signature(command)}`",
            inline=False,
        )
        embed.add_field(
            name="Description",
            value=command.help or command.short_doc or "No description",
            inline=False,
        )

        # Aliases (if any)
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False,
            )

        await ctx.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        ctx = self.context
        commands_list = await self.filter_commands(cog.get_commands(), sort=True)

        embed = discord.Embed(
            title=f"{self._clean_cog_name(cog)} Commands",
            color=discord.Color.blurple(),
        )
        lines = [self._format_command_line(cmd) for cmd in commands_list]
        embed.add_field(
            name="Commands",
            value="\n".join(lines) if lines else "No commands.",
            inline=False,
        )

        await ctx.send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        ctx = self.context

        embed = discord.Embed(
            title=f"Command Group: {group.qualified_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Usage",
            value=f"`{self.get_command_signature(group)}`",
            inline=False,
        )
        embed.add_field(
            name="Description",
            value=group.help or group.short_doc or "No description",
            inline=False,
        )

        subcommands = await self.filter_commands(group.commands, sort=True)
        if subcommands:
            lines = [self._format_command_line(cmd) for cmd in subcommands]
            embed.add_field(
                name="Subcommands",
                value="\n".join(lines),
                inline=False,
            )

        await ctx.send(embed=embed)

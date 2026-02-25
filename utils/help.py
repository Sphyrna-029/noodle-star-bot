"""Custom embed-based help command for Noodle Star Bot."""

from __future__ import annotations

from typing import Iterable, List, Optional

import discord
from discord.ext import commands


class NoodleHelpCommand(commands.HelpCommand):
    """Help command that renders a compact embed grouped by cog."""

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
        super().__init__(
            no_category="Other",
            command_attrs={
                "help": "Show available commands and usage details.",
            },
        )

    # --- Formatting helpers -------------------------------------------------

    def _clean_cog_name(self, cog: Optional[commands.Cog]) -> str:
        if cog is None:
            return self.no_category or "Other"
        name = getattr(cog, "qualified_name", None) or cog.__class__.__name__
        if name.endswith("Cog"):
            name = name[:-3]
        return name or (self.no_category or "Other")

    def _format_command_line(self, command: commands.Command) -> str:
        signature = self.get_command_signature(command)
        summary = command.help or command.short_doc or "No description"
        line = f"`{signature}` — {summary}"
        # Guard against giant docstrings/signatures that exceed embed limits.
        return line[:1000] + "…" if len(line) > 1000 else line

    def _sort_categories(self, categories: Iterable[str]) -> List[str]:
        order_index = {name: i for i, name in enumerate(self.CATEGORY_ORDER)}
        return sorted(categories, key=lambda n: (order_index.get(n, 999), n.lower()))

    def _sort_commands(self, cmds: Iterable[commands.Command]) -> List[commands.Command]:
        return sorted(cmds, key=lambda c: c.name)

    def _build_chunks(self, lines: List[str], *, max_len: int = 1024) -> List[str]:
        if not lines:
            return []

        chunks: List[str] = []
        current = ""

        for raw_line in lines:
            line = raw_line
            if len(line) > max_len:
                # Hard-wrap extreme lines to prevent field limit crashes.
                segments = [line[i : i + max_len] for i in range(0, len(line), max_len)]
            else:
                segments = [line]

            for segment in segments:
                candidate = f"{current}\n{segment}" if current else segment
                if len(candidate) > max_len:
                    if current:
                        chunks.append(current)
                    current = segment
                else:
                    current = candidate

        if current:
            chunks.append(current)

        return chunks

    async def _safe_send_embed(self, embed: discord.Embed, *, fallback_text: str) -> None:
        """Try embed first; fallback to plain text if embeds fail."""
        ctx = self.context
        try:
            await ctx.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send(fallback_text)

    def _truncate(self, text: str, *, max_len: int = 1900) -> str:
        return text[:max_len] + "…" if len(text) > max_len else text

    # --- Send helpers --------------------------------------------------------

    async def send_bot_help(self, mapping):
        ctx = self.context
        prefix = ctx.clean_prefix

        embed = discord.Embed(
            title="✨ Noodle Star Bot — Help",
            description="Here are the available commands grouped by category.",
            color=discord.Color.blurple(),
        )

        category_map: dict[str, List[commands.Command]] = {}
        for cog, cmds in mapping.items():
            if not cmds:
                continue
            filtered = await self.filter_commands(cmds, sort=False)
            if not filtered:
                continue
            category = self._clean_cog_name(cog)
            category_map.setdefault(category, []).extend(filtered)

        fallback_lines: List[str] = ["Noodle Star Bot Commands"]

        if not category_map:
            embed.add_field(name="Commands", value="No commands are currently available.", inline=False)
            fallback_lines.append("No commands are currently available.")
        else:
            for category in self._sort_categories(category_map.keys()):
                commands_list = self._sort_commands(category_map[category])
                lines = [self._format_command_line(cmd) for cmd in commands_list]
                chunks = self._build_chunks(lines)

                if not chunks:
                    chunks = ["No commands."]

                # Respect Discord embed field limit (25 fields total).
                for index, chunk in enumerate(chunks):
                    if len(embed.fields) >= 24:
                        remaining = sum(len(self._sort_commands(v)) for v in category_map.values())
                        embed.add_field(
                            name="More Commands",
                            value=(
                                "There are additional commands not shown here due to Discord limits. "
                                f"Use `{prefix}help <category>` for full details."
                            ),
                            inline=False,
                        )
                        break
                    name = category if index == 0 else f"{category} (cont.)"
                    embed.add_field(name=name, value=chunk, inline=False)

                fallback_lines.append(f"\n[{category}]")
                fallback_lines.extend(line.replace("`", "") for line in lines)

        embed.set_footer(
            text=(
                f"Use {prefix}help <command> for details • "
                f"Use {prefix}help <category> for a category"
            )
        )

        fallback_lines.append(
            f"\nUse {prefix}help <command> for details • Use {prefix}help <category> for a category"
        )

        await self._safe_send_embed(embed, fallback_text=self._truncate("\n".join(fallback_lines)))

    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(
            title=f"📘 Command: {command.qualified_name}",
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

        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False,
            )

        fallback = (
            f"Command: {command.qualified_name}\n"
            f"Usage: {self.get_command_signature(command)}\n"
            f"Description: {command.help or command.short_doc or 'No description'}"
        )
        await self._safe_send_embed(embed, fallback_text=self._truncate(fallback))

    async def send_cog_help(self, cog: commands.Cog):
        commands_list = await self.filter_commands(cog.get_commands(), sort=True)

        embed = discord.Embed(
            title=f"📚 {self._clean_cog_name(cog)} Commands",
            color=discord.Color.blurple(),
        )
        lines = [self._format_command_line(cmd) for cmd in commands_list]
        chunks = self._build_chunks(lines)
        if not chunks:
            chunks = ["No commands."]

        for index, chunk in enumerate(chunks):
            embed.add_field(
                name="Commands" if index == 0 else "Commands (cont.)",
                value=chunk,
                inline=False,
            )

        fallback = "\n".join([
            f"{self._clean_cog_name(cog)} Commands",
            *[line.replace("`", "") for line in lines],
        ])
        await self._safe_send_embed(embed, fallback_text=self._truncate(fallback))

    async def send_group_help(self, group: commands.Group):
        embed = discord.Embed(
            title=f"📦 Command Group: {group.qualified_name}",
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
            chunks = self._build_chunks(lines)
            for index, chunk in enumerate(chunks):
                embed.add_field(
                    name="Subcommands" if index == 0 else "Subcommands (cont.)",
                    value=chunk,
                    inline=False,
                )

        fallback = (
            f"Command Group: {group.qualified_name}\n"
            f"Usage: {self.get_command_signature(group)}\n"
            f"Description: {group.help or group.short_doc or 'No description'}"
        )
        await self._safe_send_embed(embed, fallback_text=self._truncate(fallback))

    async def send_error_message(self, error: str):
        """Use a friendly embed for help lookup failures."""
        embed = discord.Embed(
            title="❌ Help Lookup Failed",
            description=error,
            color=discord.Color.red(),
        )
        await self._safe_send_embed(embed, fallback_text=error)

"""Pet commands cog."""

import os

import discord
from discord.ext import commands

from cogs.pets.use_case import PetUseCases


class PetsCog(commands.Cog):
    """Commands for pet adoption and care."""

    def __init__(self, bot):
        self.bot = bot
        self.pets = PetUseCases()

    @staticmethod
    def _build_pet_image(status) -> discord.File | None:
        if not status.sprite_path:
            return None
        if not os.path.isfile(status.sprite_path):
            return None
        return discord.File(status.sprite_path, filename=os.path.basename(status.sprite_path))

    async def _send_pet_status(self, ctx, target: discord.Member) -> None:
        status = self.pets.get_pet_status(target.id)

        if status is None:
            if target.id == ctx.author.id:
                await ctx.send(
                    f"❌ {ctx.author.mention}, you don't have an active pet. Use `!pet shop` first."
                )
                return
            await ctx.send(f"❌ {target.display_name} does not have an active pet.")
            return

        embed = discord.Embed(
            title=f"{status.pet_emoji} {target.display_name}'s Pet: {status.display_name}",
            color=discord.Color.green(),
        )
        embed.add_field(name="Hunger", value=f"{status.hunger}%", inline=True)
        embed.add_field(name="Cleanliness", value=f"{status.cleanliness}%", inline=True)
        embed.add_field(name="Happiness", value=f"{status.happiness}%", inline=True)
        embed.add_field(
            name="Mood",
            value=f"**{status.mood.title()}** (sprite: `{status.sprite_state}`)",
            inline=False,
        )
        embed.set_footer(
            text="Care: !pet feed • !pet clean • !pet play | Rename: !pet rename <name>"
        )

        image_file = self._build_pet_image(status)
        if image_file is not None:
            embed.set_image(url=f"attachment://{image_file.filename}")
            await ctx.send(embed=embed, file=image_file)
            return

        await ctx.send(embed=embed)

    @commands.group(name="pet", invoke_without_command=True)
    async def pet(self, ctx, member: discord.Member = None):
        """Pet commands. Use !pet help in global help for subcommands."""
        target = member or ctx.author
        await self._send_pet_status(ctx, target)

    @pet.command(name="shop")
    async def pet_shop(self, ctx):
        """View pets available for adoption."""
        items = self.pets.get_pet_shop_items()

        embed = discord.Embed(
            title="🐾 Pet Shop",
            description="Buy a companion with `!pet buy <name>`.",
            color=discord.Color.gold(),
        )

        for item in items:
            embed.add_field(
                name=f"{item.emoji} {item.display_name} - {item.price}⭐",
                value=item.description,
                inline=False,
            )

        embed.set_footer(text="No neglect penalties: pets never die or punish you for inactivity.")
        await ctx.send(embed=embed)

    @pet.command(name="buy")
    async def pet_buy(self, ctx, *, pet_name: str = ""):
        """Buy/adopt a pet from the pet shop."""
        if not pet_name.strip():
            await ctx.send(f"❌ {ctx.author.mention}, specify a pet name. Use `!pet shop`.")
            return

        result = self.pets.buy_pet(ctx.author.id, str(ctx.author), pet_name)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(
            f"✅ {ctx.author.mention}, {result.message} Cost: **{result.price}⭐**\n"
            f"💰 New balance: **{result.new_balance}⭐**"
        )

    @pet.command(name="list")
    async def pet_list(self, ctx):
        """List all pets you own."""
        result = self.pets.list_owned_pets(ctx.author.id)
        if not result.pets:
            await ctx.send(f"❌ {ctx.author.mention}, you don't own any pets yet. Use `!pet shop`.")
            return

        lines = []
        for pet in result.pets:
            active_marker = " (active)" if pet.is_active else ""
            lines.append(
                f"{pet.pet_emoji} **{pet.display_name}**{active_marker}"
                f" - H:{pet.hunger}% C:{pet.cleanliness}% P:{pet.happiness}%"
            )

        embed = discord.Embed(
            title=f"🐾 {ctx.author.display_name}'s Pets",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Switch: !pet select <name> | Name: !pet name <pet> | <nickname>")
        await ctx.send(embed=embed)

    @pet.command(name="select")
    async def pet_select(self, ctx, *, pet_name: str = ""):
        """Set one of your owned pets as active."""
        if not pet_name.strip():
            await ctx.send(f"❌ {ctx.author.mention}, specify which pet to activate.")
            return

        result = self.pets.select_active_pet(ctx.author.id, pet_name)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(f"✅ {ctx.author.mention}, {result.message}")

    @pet.command(name="name")
    async def pet_name(self, ctx, *, name_args: str = ""):
        """Name a specific owned pet. Usage: !pet name <pet> | <nickname>"""
        if "|" not in name_args:
            await ctx.send(
                f"❌ {ctx.author.mention}, usage: `!pet name <pet> | <nickname>` "
                "(example: `!pet name cat | Luna`)."
            )
            return

        pet_name, nickname = (part.strip() for part in name_args.split("|", 1))
        if not pet_name or not nickname:
            await ctx.send(f"❌ {ctx.author.mention}, provide both pet and nickname.")
            return

        result = self.pets.name_pet(ctx.author.id, pet_name, nickname)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(f"✅ {ctx.author.mention}, {result.message}")

    @pet.command(name="rename")
    async def pet_rename(self, ctx, *, nickname: str = ""):
        """Rename your active pet."""
        if not nickname.strip():
            await ctx.send(f"❌ {ctx.author.mention}, specify a nickname.")
            return

        result = self.pets.rename_active_pet(ctx.author.id, nickname)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return

        await ctx.send(f"✅ {ctx.author.mention}, {result.message}")

    @pet.command(name="feed")
    async def pet_feed(self, ctx):
        """Feed your active pet."""
        result = self.pets.feed_pet(ctx.author.id)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return
        await ctx.send(f"🍜 {ctx.author.mention}, {result.message}")

    @pet.command(name="clean")
    async def pet_clean(self, ctx):
        """Clean your active pet."""
        result = self.pets.clean_pet(ctx.author.id)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return
        await ctx.send(f"🧼 {ctx.author.mention}, {result.message}")

    @pet.command(name="play")
    async def pet_play(self, ctx):
        """Play with your active pet."""
        result = self.pets.play_with_pet(ctx.author.id)
        if not result.success:
            await ctx.send(f"❌ {ctx.author.mention}, {result.message}")
            return
        await ctx.send(f"🎾 {ctx.author.mention}, {result.message}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(PetsCog(bot))

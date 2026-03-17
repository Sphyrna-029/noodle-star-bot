"""Action hub command — context-aware player dashboard with quick-action buttons."""

import discord
from discord.ext import commands
from datetime import datetime

from cogs.combat.constants import COMBAT_ITEMS
from cogs.locations.constants import LOCATIONS, TRAVEL_COOLDOWN_SECONDS
from cogs.locations.handlers import TravelView, _build_travel_embed
from cogs.locations.use_case import LocationUseCases
from cogs.combat.use_case.equipment import EquipmentUseCases
from cogs.combat.use_case.health import HealthUseCases
from cogs.fishing.use_case import FishingUseCases
from cogs.fishing.dto import FishingState
from database.repository import UserRepository


# ---------------------------------------------------------------------------
# Context-aware action buttons
# ---------------------------------------------------------------------------

_LOCATION_ACTIONS: dict[str, list[dict]] = {
    "noodle_town": [
        {"label": "Store", "emoji": "🛒", "command": "store"},
        {"label": "Deposit", "emoji": "🏦", "command": "deposit"},
        {"label": "Gamble", "emoji": "🎰", "command": "gamble"},
        {"label": "Inventory", "emoji": "🎒", "command": "inventory"},
    ],
    "crystal_cave": [
        {"label": "Mine", "emoji": "⛏️", "command": "mine"},
        {"label": "Consume", "emoji": "🍽️", "command": "consume"},
        {"label": "Inventory", "emoji": "🎒", "command": "inventory"},
    ],
    "starfish_bay": [
        {"label": "Fish", "emoji": "🎣", "command": "fish"},
        {"label": "Consume", "emoji": "🍽️", "command": "consume"},
        {"label": "Inventory", "emoji": "🎒", "command": "inventory"},
    ],
    "fusilli_farms": [
        {"label": "Harvest All", "emoji": "🌾", "command": "harvest all"},
        {"label": "Crops", "emoji": "🌱", "command": "crops"},
        {"label": "Inventory", "emoji": "🎒", "command": "inventory"},
    ],
    "starport_ziti": [
        {"label": "Space Mine", "emoji": "🚀", "command": "spacemine"},
        {"label": "Consume", "emoji": "🍽️", "command": "consume"},
        {"label": "Inventory", "emoji": "🎒", "command": "inventory"},
    ],
    "noodle_colosseum": [
        {"label": "Fight", "emoji": "⚔️", "command": "fight"},
        {"label": "Consume", "emoji": "🍽️", "command": "consume"},
        {"label": "Gear", "emoji": "🛡️", "command": "gear"},
    ],
}


class _ActionButton(discord.ui.Button):
    """Button that invokes a bot command when clicked."""

    def __init__(self, label: str, emoji: str, command_str: str, row: int = 0):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.primary, row=row)
        self.command_str = command_str

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ActionView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return

        await interaction.response.defer()

        # Build a fake message to create a proper context for the command
        # We copy the original message and swap its content
        fake_msg = interaction.message
        fake_msg.content = f"!{self.command_str}"
        fake_msg.author = interaction.user
        ctx = await interaction.client.get_context(fake_msg)
        if ctx.command:
            await interaction.client.invoke(ctx)
        else:
            await interaction.followup.send(
                f"❌ Command `{self.command_str}` not found.", ephemeral=True
            )


class _TravelButton(discord.ui.Button):
    """Opens the travel menu."""

    def __init__(self, row: int = 1):
        super().__init__(label="Travel", emoji="🗺️", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ActionView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return

        location_uc = LocationUseCases()
        current = location_uc.get_location(interaction.user.id)
        travel_view = TravelView(interaction.user.id, current)
        embed = _build_travel_embed(current)
        await interaction.response.send_message(embed=embed, view=travel_view, ephemeral=False)


class _EquipBestButton(discord.ui.Button):
    """Equips the best owned gear in every slot."""

    def __init__(self, row: int = 1):
        super().__init__(label="Equip Best Gear", emoji="\u2694\ufe0f", style=discord.ButtonStyle.success, row=row)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ActionView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return

        equip_uc = EquipmentUseCases()
        result = equip_uc.equip_best(interaction.user.id)
        await interaction.response.send_message(result.message, ephemeral=True)


class ActionView(discord.ui.View):
    """Action hub view with context-aware buttons."""

    def __init__(self, author_id: int, location: str, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message = None

        # Add location-specific action buttons (row 0)
        actions = _LOCATION_ACTIONS.get(location, [])
        for action in actions:
            self.add_item(_ActionButton(
                label=action["label"],
                emoji=action["emoji"],
                command_str=action["command"],
                row=0,
            ))

        # Add equip best gear and travel buttons (row 1)
        self.add_item(_EquipBestButton(row=1))
        self.add_item(_TravelButton(row=1))

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Hint generation
# ---------------------------------------------------------------------------

def _generate_hint(
    location: str,
    inventory: dict,
    wallet: int,
    bank: int,
    inv_count: int,
    inv_capacity: int,
    fishing_status=None,
    ready_crops: int = 0,
) -> str | None:
    """Generate a contextual progression hint."""
    mine_level = inventory.get("mine_level", 1)
    fish_level = inventory.get("active_fish_level", 1)
    farm_level = inventory.get("farm_level", 1)
    space_planet = inventory.get("space_planet_level", 0)
    farm_plots = inventory.get("farm_plots", 0)
    has_rocket = inventory.get("rocket_ship", 0)

    # Urgent hints first
    if inv_count >= inv_capacity:
        return "Your inventory is **full**! Sell items with `!sell` or upgrade your bag."

    if inv_count >= inv_capacity - 5:
        return f"Inventory almost full ({inv_count}/{inv_capacity}). Consider selling or upgrading your bag."

    # Fishing active state
    if fishing_status and fishing_status.is_fishing:
        if fishing_status.state == FishingState.BITING:
            return "A fish is biting! Use `!pull` now!"
        elif fishing_status.state == FishingState.WAITING:
            return "Line is cast — waiting for a bite..."

    # Ready crops
    if ready_crops > 0:
        return f"You have **{ready_crops}** crop{'s' if ready_crops != 1 else ''} ready to harvest!"

    # Progression hints
    if mine_level < 5 and wallet >= [0, 100, 500, 2000, 5000][mine_level - 1]:
        return f"You can unlock Mine Level {mine_level + 1}! Use `!unlock {mine_level + 1}`."

    if mine_level >= 5 and not has_rocket and wallet + bank >= 10000:
        return "You've mastered mining! Buy a Rocket Ship (`!buy rocket`) to explore space."

    if farm_plots == 0 and wallet >= 500:
        return "You can start farming! Buy your first plot with `!buyplot 1`."

    # Location-specific hints
    if location == "noodle_town" and wallet >= 100:
        return "Deposit your stars to keep them safe! Use `!deposit`."

    return None


# ---------------------------------------------------------------------------
# Embed builder
# ---------------------------------------------------------------------------

def _progress_bar(pct: float, length: int = 8) -> str:
    filled = int(pct * length)
    return "█" * filled + "░" * (length - filled)


def _build_action_embed(
    user: discord.Member | discord.User,
    location: str,
    wallet: int,
    bank: int,
    health_status,
    inv_count: int,
    inv_capacity: int,
    inventory: dict,
    combat_stats: dict,
    fishing_status=None,
    ready_crops: int = 0,
    travel_cd_remaining: int = 0,
    fishing_cd_remaining: int = 0,
) -> discord.Embed:
    loc = LOCATIONS.get(location)
    loc_display = f"{loc.emoji} {loc.name}" if loc else location

    embed = discord.Embed(
        title=f"📋 {user.display_name}'s Action Hub",
        color=discord.Color.blurple(),
    )

    # ── Status overview ──
    hp_pct = health_status.current_hp / health_status.max_hp if health_status.max_hp else 0
    stam_pct = health_status.current_stamina / health_status.max_stamina if health_status.max_stamina else 0
    status_lines = [
        f"📍 **Location:** {loc_display}",
        f"💫 **Wallet:** {wallet:,} | 🏦 **Bank:** {bank:,}",
        f"❤️ **HP:** {health_status.current_hp}/{health_status.max_hp} {_progress_bar(hp_pct)}",
        f"⚡ **Stamina:** {health_status.current_stamina}/{health_status.max_stamina} {_progress_bar(stam_pct)}",
        f"🎒 **Inventory:** {inv_count}/{inv_capacity}",
    ]
    embed.description = "\n".join(status_lines)

    # ── Levels ──
    mine_lvl = inventory.get("mine_level", 1)
    fish_lvl = inventory.get("active_fish_level", 1)
    farm_lvl = inventory.get("farm_level", 1)
    space_planet = inventory.get("space_planet_level", 0)
    combat_lvl = combat_stats.get("combat_level", 0)
    dungeon_lvl = combat_stats.get("active_combat_level", 1)

    level_parts = [
        f"⛏️ Mine {mine_lvl}",
        f"🎣 Fish {fish_lvl}",
        f"🌾 Farm {farm_lvl}",
    ]
    if space_planet > 0:
        level_parts.append(f"🚀 Planet {space_planet}")
    level_parts.append(f"🏟️ Dungeon {dungeon_lvl}")

    embed.add_field(name="Levels", value=" · ".join(level_parts), inline=False)

    # ── Equipment ──
    weapon = combat_stats.get("equipped_weapon")
    shield = combat_stats.get("equipped_shield")
    armor = combat_stats.get("equipped_armor")

    gear_parts = []
    if weapon and weapon in COMBAT_ITEMS:
        item = COMBAT_ITEMS[weapon]
        gear_parts.append(f"🗡️ {item.name}")
    if shield and shield in COMBAT_ITEMS:
        item = COMBAT_ITEMS[shield]
        gear_parts.append(f"🛡️ {item.name}")
    if armor and armor in COMBAT_ITEMS:
        item = COMBAT_ITEMS[armor]
        gear_parts.append(f"🦺 {item.name}")

    if gear_parts:
        embed.add_field(name="Equipment", value=" · ".join(gear_parts), inline=False)
    else:
        embed.add_field(name="Equipment", value="*None equipped*", inline=False)

    # ── Cooldowns ──
    cd_parts = []
    if travel_cd_remaining > 0:
        cd_parts.append(f"🗺️ Travel: {travel_cd_remaining}s")
    if fishing_status and fishing_status.is_fishing:
        if fishing_status.state == FishingState.BITING:
            secs = fishing_status.time_until_expires or 0
            cd_parts.append(f"🎣 **BITING!** {secs}s left")
        elif fishing_status.state == FishingState.WAITING:
            secs = fishing_status.time_until_bite or 0
            cd_parts.append(f"🎣 Waiting for bite ~{secs}s")
    elif fishing_cd_remaining > 0:
        cd_parts.append(f"🎣 Fish CD: {fishing_cd_remaining}s")
    if ready_crops > 0:
        cd_parts.append(f"🌾 {ready_crops} crop{'s' if ready_crops != 1 else ''} ready!")

    if cd_parts:
        embed.add_field(name="Active Timers", value=" · ".join(cd_parts), inline=False)

    # ── Hint ──
    hint = _generate_hint(
        location, inventory, wallet, bank,
        inv_count, inv_capacity, fishing_status, ready_crops,
    )
    if hint:
        embed.add_field(name="💡 Tip", value=hint, inline=False)

    embed.set_footer(text="Use the buttons below or type commands directly.")
    return embed


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class ActionCog(commands.Cog):
    """Quick action hub — !action or !a."""

    def __init__(self, bot):
        self.bot = bot
        self.repo = UserRepository()
        self.health_uc = HealthUseCases(self.repo)
        self.location_uc = LocationUseCases()
        self.fishing_uc = FishingUseCases()

    @commands.command(name="action", aliases=["a"])
    async def action(self, ctx):
        """Open your action hub — see stats, timers, and quick actions."""
        user_id = ctx.author.id
        username = str(ctx.author)

        # Gather all data
        location = self.location_uc.get_location(user_id)
        wallet = self.repo.get_user_stars(user_id, username)
        bank = self.repo.get_user_bank(user_id)
        health_status = self.health_uc.get_status(user_id)
        inv_count = self.repo.get_inventory_count(user_id)
        inv_capacity = self.repo.get_inventory_capacity(user_id)
        inventory = self.repo.get_user_inventory(user_id)
        combat_stats = self.repo.get_combat_stats(user_id)

        # Fishing status
        fishing_status = self.fishing_uc.get_status(user_id, username)

        # Fishing cooldown
        fishing_cd = 0
        if fishing_status.cooldown_remaining and fishing_status.cooldown_remaining > 0:
            fishing_cd = fishing_status.cooldown_remaining

        # Travel cooldown
        travel_cd = 0
        with self.repo.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT last_travel FROM user_activity WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row and row["last_travel"]:
                last = datetime.fromisoformat(row["last_travel"])
                elapsed = (datetime.now() - last).total_seconds()
                remaining = TRAVEL_COOLDOWN_SECONDS - elapsed
                if remaining > 0:
                    travel_cd = int(remaining)

        # Farm ready crops
        ready_crops = 0
        planted = self.repo.get_planted_crops(user_id)
        now = datetime.now()
        for crop in planted:
            if now >= crop.ready_at:
                ready_crops += 1

        # Build embed and view
        embed = _build_action_embed(
            user=ctx.author,
            location=location,
            wallet=wallet,
            bank=bank,
            health_status=health_status,
            inv_count=inv_count,
            inv_capacity=inv_capacity,
            inventory=inventory,
            combat_stats=combat_stats,
            fishing_status=fishing_status,
            ready_crops=ready_crops,
            travel_cd_remaining=travel_cd,
            fishing_cd_remaining=fishing_cd,
        )

        view = ActionView(ctx.author.id, location)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg


# ---------------------------------------------------------------------------
# Cog setup
# ---------------------------------------------------------------------------

async def setup(bot):
    await bot.add_cog(ActionCog(bot))

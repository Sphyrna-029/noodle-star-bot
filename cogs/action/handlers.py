"""Action hub command — context-aware player dashboard with quick-action buttons."""

import discord
from discord.ext import commands
from datetime import datetime

from cogs.combat.constants import COMBAT_ITEMS
from cogs.fishing.constants import FISHING_BAIT_TIERS
from cogs.locations.constants import LOCATIONS, TRAVEL_COOLDOWN_SECONDS
from cogs.locations.handlers import TravelView, _build_travel_embed
from cogs.locations.use_case import LocationUseCases
from cogs.combat.use_case.equipment import EquipmentUseCases
from cogs.combat.use_case.health import HealthUseCases
from cogs.fishing.use_case import FishingUseCases
from cogs.fishing.dto import FishingState
from database.repository import UserRepository


# ---------------------------------------------------------------------------
# Helpers — invoke a bot command from an interaction
# ---------------------------------------------------------------------------

async def _invoke_command(interaction: discord.Interaction, command_str: str):
    """Build a fake message context and invoke a bot command."""
    fake_msg = interaction.message
    fake_msg.content = f"!{command_str}"
    fake_msg.author = interaction.user
    ctx = await interaction.client.get_context(fake_msg)
    if ctx.command:
        await interaction.client.invoke(ctx)
    else:
        await interaction.followup.send(
            f"\u274c Command `{command_str}` not found.", ephemeral=True
        )


# ---------------------------------------------------------------------------
# Modals — text input for amounts
# ---------------------------------------------------------------------------

class _AmountModal(discord.ui.Modal):
    """Modal that asks for a number/amount then invokes a command."""

    def __init__(self, command: str, title: str, label: str,
                 placeholder: str = "Enter amount or 'all'"):
        super().__init__(title=title)
        self.command_str = command
        self.amount_input = discord.ui.TextInput(
            label=label,
            placeholder=placeholder,
            required=True,
            max_length=20,
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        amount = self.amount_input.value.strip()
        await _invoke_command(interaction, f"{self.command_str} {amount}")


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

class _ActionButton(discord.ui.Button):
    """Button that invokes a bot command when clicked."""

    def __init__(self, label: str, emoji: str, command_str: str, row: int = 0,
                 style: discord.ButtonStyle = discord.ButtonStyle.primary):
        super().__init__(label=label, emoji=emoji, style=style, row=row)
        self.command_str = command_str

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ActionView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return
        await interaction.response.defer()
        await _invoke_command(interaction, self.command_str)


class _ModalButton(discord.ui.Button):
    """Button that opens a Modal for amount input, then invokes a command."""

    def __init__(self, label: str, emoji: str, command: str,
                 modal_title: str, modal_label: str,
                 placeholder: str = "Enter amount or 'all'",
                 row: int = 0,
                 style: discord.ButtonStyle = discord.ButtonStyle.primary):
        super().__init__(label=label, emoji=emoji, style=style, row=row)
        self.command = command
        self.modal_title = modal_title
        self.modal_label = modal_label
        self.placeholder = placeholder

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ActionView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return
        modal = _AmountModal(
            command=self.command,
            title=self.modal_title,
            label=self.modal_label,
            placeholder=self.placeholder,
        )
        await interaction.response.send_modal(modal)


class _TravelButton(discord.ui.Button):
    """Opens the travel menu."""

    def __init__(self, row: int = 2):
        super().__init__(label="Travel", emoji="\U0001f5fa\ufe0f", style=discord.ButtonStyle.secondary, row=row)

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

    def __init__(self, row: int = 2):
        super().__init__(label="Equip Best Gear", emoji="\u2694\ufe0f", style=discord.ButtonStyle.success, row=row)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ActionView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return
        equip_uc = EquipmentUseCases()
        result = equip_uc.equip_best(interaction.user.id)
        await interaction.response.send_message(result.message, ephemeral=True)


# ---------------------------------------------------------------------------
# Selects — dropdowns for item/bait choices
# ---------------------------------------------------------------------------

class _BaitSelect(discord.ui.Select):
    """Dropdown to pick bait and cast line."""

    def __init__(self, bait_inventory: dict, equipped_bait: str | None):
        options = []
        for key, tier in FISHING_BAIT_TIERS.items():
            count = bait_inventory.get(key, 0)
            if count <= 0 and key != "worm":
                continue  # skip unowned bait (worm is always available conceptually)
            if count <= 0:
                continue
            is_equipped = (key == equipped_bait)
            options.append(discord.SelectOption(
                label=f"{tier.display_name} x{count}",
                value=key,
                emoji=tier.emoji,
                description=f"Rare boost: {tier.rare_boost}x" + (" (equipped)" if is_equipped else ""),
                default=is_equipped,
            ))
        if not options:
            options.append(discord.SelectOption(
                label="No bait available",
                value="_none",
                description="Buy bait from the store",
            ))
        super().__init__(placeholder="\U0001f3a3 Select bait & cast...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ActionView) or interaction.user.id != view.author_id:
            await interaction.response.send_message("Not your menu!", ephemeral=True)
            return
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.send_message("You have no bait! Buy some from `!store`.", ephemeral=True)
            return
        await interaction.response.defer()
        await _invoke_command(interaction, f"fish {selected}")


# ---------------------------------------------------------------------------
# Location button configs
# ---------------------------------------------------------------------------

def _build_noodle_town_items() -> list:
    """Buttons for Noodle Town — includes modals for deposit/withdraw/gamble."""
    return [
        _ActionButton(label="Store", emoji="\U0001f6d2", command_str="store", row=0),
        _ModalButton(
            label="Deposit", emoji="\U0001f3e6", command="deposit",
            modal_title="Deposit Stars", modal_label="How many stars to deposit?",
            row=0,
        ),
        _ModalButton(
            label="Withdraw", emoji="\U0001f4b0", command="withdraw",
            modal_title="Withdraw Stars", modal_label="How many stars to withdraw?",
            row=0,
        ),
        _ModalButton(
            label="Gamble", emoji="\U0001f3b0", command="gamble",
            modal_title="Gamble Stars", modal_label="How many stars to gamble?",
            placeholder="Enter amount",
            row=0,
        ),
        _ActionButton(label="Inventory", emoji="\U0001f392", command_str="inventory", row=0),
    ]


def _build_crystal_cave_items() -> list:
    return [
        _ActionButton(label="Mine", emoji="\u26cf\ufe0f", command_str="mine", row=0),
        _ActionButton(label="Sell All", emoji="\U0001f4b5", command_str="sell all", row=0),
        _ActionButton(label="Consume", emoji="\U0001f37d\ufe0f", command_str="consume", row=0),
        _ActionButton(label="Inventory", emoji="\U0001f392", command_str="inventory", row=0),
    ]


def _build_starfish_bay_items(bait_inventory: dict, equipped_bait: str | None) -> list:
    items = [
        _ActionButton(label="Pull", emoji="\U0001f3a3", command_str="pull", row=0),
        _ActionButton(label="Sell All", emoji="\U0001f4b5", command_str="sell all", row=0),
        _ActionButton(label="Consume", emoji="\U0001f37d\ufe0f", command_str="consume", row=0),
        _ActionButton(label="Inventory", emoji="\U0001f392", command_str="inventory", row=0),
    ]
    # Bait select goes on row 1
    items.append(_BaitSelect(bait_inventory, equipped_bait))
    return items


def _build_fusilli_farms_items() -> list:
    return [
        _ActionButton(label="Harvest All", emoji="\U0001f33e", command_str="harvest all", row=0),
        _ActionButton(label="Crops", emoji="\U0001f331", command_str="crops", row=0),
        _ActionButton(label="Sell All", emoji="\U0001f4b5", command_str="sell all", row=0),
        _ActionButton(label="Inventory", emoji="\U0001f392", command_str="inventory", row=0),
    ]


def _build_starport_ziti_items() -> list:
    return [
        _ActionButton(label="Space Mine", emoji="\U0001f680", command_str="spacemine", row=0),
        _ActionButton(label="Sell All", emoji="\U0001f4b5", command_str="sell all", row=0),
        _ActionButton(label="Consume", emoji="\U0001f37d\ufe0f", command_str="consume", row=0),
        _ActionButton(label="Inventory", emoji="\U0001f392", command_str="inventory", row=0),
    ]


def _build_colosseum_items() -> list:
    return [
        _ActionButton(label="Fight", emoji="\u2694\ufe0f", command_str="fight", row=0),
        _ActionButton(label="Consume", emoji="\U0001f37d\ufe0f", command_str="consume", row=0),
        _ActionButton(label="Gear", emoji="\U0001f6e1\ufe0f", command_str="gear", row=0),
    ]


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

class ActionView(discord.ui.View):
    """Action hub view with context-aware buttons, selects, and modals."""

    def __init__(self, author_id: int, location: str,
                 bait_inventory: dict | None = None,
                 equipped_bait: str | None = None,
                 timeout: float = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message = None

        # Add location-specific components (row 0 buttons, row 1 selects)
        if location == "noodle_town":
            items = _build_noodle_town_items()
        elif location == "crystal_cave":
            items = _build_crystal_cave_items()
        elif location == "starfish_bay":
            items = _build_starfish_bay_items(bait_inventory or {}, equipped_bait)
        elif location == "fusilli_farms":
            items = _build_fusilli_farms_items()
        elif location == "starport_ziti":
            items = _build_starport_ziti_items()
        elif location == "noodle_colosseum":
            items = _build_colosseum_items()
        else:
            items = []

        for item in items:
            self.add_item(item)

        # Utility buttons (row 2)
        self.add_item(_EquipBestButton(row=2))
        self.add_item(_TravelButton(row=2))

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
            return "Line is cast \u2014 waiting for a bite..."

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
    return "\u2588" * filled + "\u2591" * (length - filled)


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
        title=f"\U0001f4cb {user.display_name}'s Action Hub",
        color=discord.Color.blurple(),
    )

    # ── Status overview ──
    hp_pct = health_status.current_hp / health_status.max_hp if health_status.max_hp else 0
    stam_pct = health_status.current_stamina / health_status.max_stamina if health_status.max_stamina else 0
    status_lines = [
        f"\U0001f4cd **Location:** {loc_display}",
        f"\U0001f4ab **Wallet:** {wallet:,} | \U0001f3e6 **Bank:** {bank:,}",
        f"\u2764\ufe0f **HP:** {health_status.current_hp}/{health_status.max_hp} {_progress_bar(hp_pct)}",
        f"\u26a1 **Stamina:** {health_status.current_stamina}/{health_status.max_stamina} {_progress_bar(stam_pct)}",
        f"\U0001f392 **Inventory:** {inv_count}/{inv_capacity}",
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
        f"\u26cf\ufe0f Mine {mine_lvl}",
        f"\U0001f3a3 Fish {fish_lvl}",
        f"\U0001f33e Farm {farm_lvl}",
    ]
    if space_planet > 0:
        level_parts.append(f"\U0001f680 Planet {space_planet}")
    level_parts.append(f"\U0001f3df\ufe0f Dungeon {dungeon_lvl}")

    embed.add_field(name="Levels", value=" \u00b7 ".join(level_parts), inline=False)

    # ── Equipment ──
    weapon = combat_stats.get("equipped_weapon")
    shield = combat_stats.get("equipped_shield")
    armor = combat_stats.get("equipped_armor")

    gear_parts = []
    if weapon and weapon in COMBAT_ITEMS:
        item = COMBAT_ITEMS[weapon]
        gear_parts.append(f"\U0001f5e1\ufe0f {item.name}")
    if shield and shield in COMBAT_ITEMS:
        item = COMBAT_ITEMS[shield]
        gear_parts.append(f"\U0001f6e1\ufe0f {item.name}")
    if armor and armor in COMBAT_ITEMS:
        item = COMBAT_ITEMS[armor]
        gear_parts.append(f"\U0001f9ba {item.name}")

    if gear_parts:
        embed.add_field(name="Equipment", value=" \u00b7 ".join(gear_parts), inline=False)
    else:
        embed.add_field(name="Equipment", value="*None equipped*", inline=False)

    # ── Cooldowns ──
    cd_parts = []
    if travel_cd_remaining > 0:
        cd_parts.append(f"\U0001f5fa\ufe0f Travel: {travel_cd_remaining}s")
    if fishing_status and fishing_status.is_fishing:
        if fishing_status.state == FishingState.BITING:
            secs = fishing_status.time_until_expires or 0
            cd_parts.append(f"\U0001f3a3 **BITING!** {secs}s left")
        elif fishing_status.state == FishingState.WAITING:
            secs = fishing_status.time_until_bite or 0
            cd_parts.append(f"\U0001f3a3 Waiting for bite ~{secs}s")
    elif fishing_cd_remaining > 0:
        cd_parts.append(f"\U0001f3a3 Fish CD: {fishing_cd_remaining}s")
    if ready_crops > 0:
        cd_parts.append(f"\U0001f33e {ready_crops} crop{'s' if ready_crops != 1 else ''} ready!")

    if cd_parts:
        embed.add_field(name="Active Timers", value=" \u00b7 ".join(cd_parts), inline=False)

    # ── Hint ──
    hint = _generate_hint(
        location, inventory, wallet, bank,
        inv_count, inv_capacity, fishing_status, ready_crops,
    )
    if hint:
        embed.add_field(name="\U0001f4a1 Tip", value=hint, inline=False)

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

        # Bait data (for Starfish Bay dropdown)
        bait_inventory = None
        equipped_bait = None
        if location == "starfish_bay":
            bait_inventory = self.repo.get_bait_inventory(user_id)
            equipped_bait = self.repo.get_equipped_bait(user_id)

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

        view = ActionView(
            ctx.author.id, location,
            bait_inventory=bait_inventory,
            equipped_bait=equipped_bait,
        )
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg


# ---------------------------------------------------------------------------
# Cog setup
# ---------------------------------------------------------------------------

async def setup(bot):
    await bot.add_cog(ActionCog(bot))

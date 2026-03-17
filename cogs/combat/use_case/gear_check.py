"""Gear danger check — warns players when their equipment is weak for the area."""

from cogs.combat.constants import BASE_HP, COMBAT_ITEMS
from cogs.combat.use_case.health import HealthUseCases
from database.repository import UserRepository


def gear_warning(user_id: int, mobs: list, repo: UserRepository = None) -> str | None:
    """Compare player stats against the strongest mob in *mobs*.

    Returns a warning string with skull/magnifying-glass flavour,
    or None if the player looks reasonably prepared.
    """
    if not mobs:
        return None

    repo = repo or UserRepository()
    stats = repo.get_combat_stats(user_id)

    # Player totals (mirrors combat.py logic)
    player_atk = 5
    player_def = 2
    hp_bonus = 0
    for slot in ("equipped_weapon", "equipped_shield", "equipped_armor"):
        key = stats.get(slot)
        if key and key in COMBAT_ITEMS:
            item = COMBAT_ITEMS[key]
            player_atk += item.attack
            player_def += item.defense
            hp_bonus += item.hp_bonus

    max_hp = BASE_HP + hp_bonus
    # Apply regen so we use up-to-date HP, not stale DB value
    health = HealthUseCases(repo).get_status(user_id)
    current_hp = health.current_hp

    # Pick the toughest mob
    mob = max(mobs, key=lambda m: m.attack)

    # Estimated damage mob deals per hit: mob_atk - player_def // 2
    mob_dmg = max(1, mob.attack - player_def // 2)
    hits_to_die = max_hp / mob_dmg if mob_dmg > 0 else 999

    # Danger tiers
    warnings = []
    if hits_to_die <= 2:
        warnings.append(f"💀💀 **Extreme danger!** A {mob.emoji} **{mob.name}** will overwhelm you!")
    elif hits_to_die <= 4:
        warnings.append(f"💀 **Dangerous!** A {mob.emoji} **{mob.name}** hits very hard here.")

    if player_atk <= mob.defense:
        warnings.append("⚔️ Your attack is too low — you'll barely scratch them!")

    if current_hp <= mob_dmg * 2:
        warnings.append(f"❤️ Your HP is critically low ({current_hp}/{max_hp})!")

    if not warnings:
        return None

    header = "🔍💀 **Gear Check**"
    return header + "\n" + "\n".join(warnings)

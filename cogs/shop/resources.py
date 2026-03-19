"""Resource catalog — item display info and alias lookup for the sell system."""

from dataclasses import dataclass
from typing import Final, Optional


@dataclass(frozen=True, slots=True)
class ResourceInfo:
    """Display metadata for a sellable resource item."""
    item_key: str
    display_name: str
    emoji: str
    category: str  # "mineral", "fish", "ore", "crop", "consumable"


# Home locations by category — selling at home gives no bonus
CATEGORY_HOME: Final[dict[str, str]] = {
    "mineral": "crystal_cave",
    "fish": "starfish_bay",
    "crop": "fusilli_farms",
    "ore": "starport_ziti",
    "consumable": "",  # no home
}

# Category aliases for !sell <category>
CATEGORY_ALIASES: Final[dict[str, str]] = {
    "minerals": "mineral",
    "mineral": "mineral",
    "fish": "fish",
    "fishes": "fish",
    "fishing": "fish",
    "ore": "ore",
    "ores": "ore",
    "space": "ore",
    "crop": "crop",
    "crops": "crop",
    "farming": "crop",
    "consumable": "consumable",
    "consumables": "consumable",
    "supplies": "consumable",
}

# Build the full resource registry
# Key derivation matches what each gathering system uses:
# Mining: name.lower().replace(" ", "_")
# Fishing: name.lower().replace(" ", "_").replace("'", "")
# Space: name.lower().replace(" ", "_").replace("-", "_")
# Farming: name.lower().replace(" ", "_")

_RESOURCES: dict[str, ResourceInfo] = {}

def _r(key: str, name: str, emoji: str, category: str) -> None:
    """Register a resource."""
    _RESOURCES[key] = ResourceInfo(item_key=key, display_name=name, emoji=emoji, category=category)

# ── Mining Minerals (25) ────────────────────────────────────
# Level 1 - Surface
_r("stone", "Stone", "🪨", "mineral")
_r("coal", "Coal", "⚫", "mineral")
_r("iron", "Iron", "⚙️", "mineral")
_r("gold", "Gold", "🟡", "mineral")
_r("diamond", "Diamond", "💎", "mineral")
# Level 2 - Caverns
_r("sandstone", "Sandstone", "🧱", "mineral")
_r("copper", "Copper", "🟤", "mineral")
_r("silver", "Silver", "⬜", "mineral")
_r("emerald", "Emerald", "💚", "mineral")
_r("ruby", "Ruby", "❤️", "mineral")
# Level 3 - Deep Tunnels
_r("slate", "Slate", "🪨", "mineral")
_r("tin", "Tin", "🪙", "mineral")
_r("platinum", "Platinum", "🔘", "mineral")
_r("sapphire", "Sapphire", "💙", "mineral")
_r("amethyst", "Amethyst", "💜", "mineral")
# Level 4 - Molten Core
_r("obsidian", "Obsidian", "🖤", "mineral")
_r("titanium", "Titanium", "⚪", "mineral")
_r("mithril", "Mithril", "🔵", "mineral")
_r("opal", "Opal", "🌈", "mineral")
_r("star_fragment", "Star Fragment", "🌟", "mineral")
# Level 5 - The Abyss
_r("darkite", "Darkite", "🌑", "mineral")
_r("adamantium", "Adamantium", "⛓️", "mineral")
_r("dragonstone", "Dragonstone", "🐉", "mineral")
_r("void_crystal", "Void Crystal", "🔮", "mineral")
_r("noodle_gem", "Noodle Gem", "🍜", "mineral")

# ── Fish (75) ───────────────────────────────────────────────
# Level 1 - Calm Pond
_r("old_boot", "Old Boot", "🥾", "fish")
_r("seaweed", "Seaweed", "🌿", "fish")
_r("tin_can", "Tin Can", "🥫", "fish")
_r("small_fish", "Small Fish", "🐟", "fish")
_r("crab", "Crab", "🦀", "fish")
_r("shrimp", "Shrimp", "🦐", "fish")
_r("salmon", "Salmon", "🐠", "fish")
_r("tuna", "Tuna", "🐟", "fish")
_r("lobster", "Lobster", "🦞", "fish")
_r("octopus", "Octopus", "🐙", "fish")
_r("treasure_chest", "Treasure Chest", "📦", "fish")
_r("golden_fish", "Golden Fish", "✨", "fish")
_r("giant_squid", "Giant Squid", "🦑", "fish")
_r("ancient_artifact", "Ancient Artifact", "🏺", "fish")
_r("mermaids_pearl", "Mermaid's Pearl", "🔮", "fish")
# Level 2 - River Rapids
_r("driftwood", "Driftwood", "🪵", "fish")
_r("river_stone", "River Stone", "🪨", "fish")
_r("crawdad", "Crawdad", "🦐", "fish")
_r("trout", "Trout", "🐟", "fish")
_r("catfish", "Catfish", "🐈", "fish")
_r("bass", "Bass", "🐠", "fish")
_r("river_salmon", "River Salmon", "🐠", "fish")
_r("sturgeon", "Sturgeon", "🐋", "fish")
_r("snapping_turtle", "Snapping Turtle", "🐢", "fish")
_r("giant_catfish", "Giant Catfish", "🐟", "fish")
_r("river_chest", "River Chest", "📦", "fish")
_r("platinum_trout", "Platinum Trout", "✨", "fish")
_r("river_dragon", "River Dragon", "🐉", "fish")
_r("lost_crown", "Lost Crown", "👑", "fish")
_r("river_spirit_gem", "River Spirit Gem", "💎", "fish")
# Level 3 - Coral Reef
_r("sea_sponge", "Sea Sponge", "🧽", "fish")
_r("starfish", "Starfish", "⭐", "fish")
_r("clownfish", "Clownfish", "🐠", "fish")
_r("parrotfish", "Parrotfish", "🦜", "fish")
_r("sea_urchin", "Sea Urchin", "🟣", "fish")
_r("moray_eel", "Moray Eel", "🐍", "fish")
_r("reef_shark", "Reef Shark", "🦈", "fish")
_r("giant_clam", "Giant Clam", "🐚", "fish")
_r("manta_ray", "Manta Ray", "🦅", "fish")
_r("sea_turtle", "Sea Turtle", "🐢", "fish")
_r("sunken_treasure", "Sunken Treasure", "💰", "fish")
_r("golden_seahorse", "Golden Seahorse", "✨", "fish")
_r("coral_golem", "Coral Golem", "🪸", "fish")
_r("neptunes_trident", "Neptune's Trident", "🔱", "fish")
_r("pearl_of_the_deep", "Pearl of the Deep", "🔮", "fish")
# Level 4 - Shipwreck Depths
_r("barnacle_cluster", "Barnacle Cluster", "🪨", "fish")
_r("rusty_anchor", "Rusty Anchor", "⚓", "fish")
_r("anglerfish", "Anglerfish", "🐡", "fish")
_r("barracuda", "Barracuda", "🐟", "fish")
_r("swordfish", "Swordfish", "⚔️", "fish")
_r("electric_eel", "Electric Eel", "⚡", "fish")
_r("hammerhead_shark", "Hammerhead Shark", "🦈", "fish")
_r("giant_octopus", "Giant Octopus", "🐙", "fish")
_r("sunken_cannon", "Sunken Cannon", "💣", "fish")
_r("ghost_ship_wheel", "Ghost Ship Wheel", "☠️", "fish")
_r("pirates_hoard", "Pirate's Hoard", "💰", "fish")
_r("phantom_captain", "Phantom Captain", "👻", "fish")
_r("diamond_anchor", "Diamond Anchor", "💎", "fish")
_r("cursed_gold", "Cursed Gold", "🏴‍☠️", "fish")
_r("davy_jones_chest", "Davy Jones' Chest", "📦", "fish")
# Level 5 - The Abyss Trench
_r("void_coral", "Void Coral", "🖤", "fish")
_r("bioluminescent_jelly", "Bioluminescent Jelly", "🪼", "fish")
_r("abyssal_crab", "Abyssal Crab", "🦀", "fish")
_r("vampire_squid", "Vampire Squid", "🦑", "fish")
_r("gulper_eel", "Gulper Eel", "🐍", "fish")
_r("dragonfish", "Dragonfish", "🐉", "fish")
_r("colossal_squid", "Colossal Squid", "🦑", "fish")
_r("megalodon_tooth", "Megalodon Tooth", "🦷", "fish")
_r("abyssal_pearl", "Abyssal Pearl", "⚪", "fish")
_r("deep_sea_crown", "Deep Sea Crown", "👑", "fish")
_r("trench_treasure", "Trench Treasure", "💰", "fish")
_r("leviathan_scale", "Leviathan Scale", "🐲", "fish")
_r("poseidons_eye", "Poseidon's Eye", "🔮", "fish")
_r("world_serpent_fang", "World Serpent Fang", "🐍", "fish")
_r("heart_of_the_abyss", "Heart of the Abyss", "💜", "fish")

# ── Space Ores (25) ─────────────────────────────────────────
# Planet 1 - Moon
_r("moon_dust", "Moon Dust", "🌕", "ore")
_r("helium_3", "Helium-3", "🫧", "ore")
_r("lunar_quartz", "Lunar Quartz", "🤍", "ore")
_r("selenite", "Selenite", "🌙", "ore")
_r("cosmic_pearl", "Cosmic Pearl", "🦪", "ore")
# Planet 2 - Mars
_r("red_sand", "Red Sand", "🔴", "ore")
_r("martian_iron", "Martian Iron", "🧲", "ore")
_r("phobos_shard", "Phobos Shard", "💫", "ore")
_r("olympus_ruby", "Olympus Ruby", "🌋", "ore")
_r("stardust_crystal", "Stardust Crystal", "✴️", "ore")
# Planet 3 - Saturn
_r("ring_fragment", "Ring Fragment", "🪐", "ore")
_r("titan_ore", "Titan Ore", "🟠", "ore")
_r("ammonia_ice", "Ammonia Ice", "🧊", "ore")
_r("saturn_sapphire", "Saturn Sapphire", "💍", "ore")
_r("nova_core", "Nova Core", "💥", "ore")
# Planet 4 - Uranus
_r("ice_rock", "Ice Rock", "❄️", "ore")
_r("methane_crystal", "Methane Crystal", "🟢", "ore")
_r("miranda_stone", "Miranda Stone", "🌀", "ore")
_r("uranian_diamond", "Uranian Diamond", "💠", "ore")
_r("nebula_shard", "Nebula Shard", "🌌", "ore")
# Planet 5 - Pluto
_r("frozen_nitrogen", "Frozen Nitrogen", "🥶", "ore")
_r("charon_basalt", "Charon Basalt", "🗿", "ore")
_r("dark_matter", "Dark Matter", "⚛️", "ore")
_r("plutonium_core", "Plutonium Core", "☢️", "ore")
_r("eternity_gem", "Eternity Gem", "👑", "ore")

# ── Crops (5) ───────────────────────────────────────────────
_r("wheat", "Wheat", "🌾", "crop")
_r("carrot", "Carrot", "🥕", "crop")
_r("corn", "Corn", "🌽", "crop")
_r("tomato", "Tomato", "🍅", "crop")
_r("melon", "Melon", "🍉", "crop")

# ── Aetherdepths Materials (15) ────────────────────────────
# Level 1
_r("hollow_stone", "Hollow Stone", "🪨", "mineral")
_r("primordial_dust", "Primordial Dust", "✨", "mineral")
_r("aether_shard", "Aether Shard", "💠", "mineral")
# Level 2
_r("forge_cinder", "Forge Cinder", "🔥", "mineral")
_r("molten_slag", "Molten Slag", "🟠", "mineral")
_r("infernal_core", "Infernal Core", "🔴", "mineral")
# Level 3
_r("voidcell", "Voidcell", "🟣", "mineral")
_r("crystal_marrow", "Crystal Marrow", "💎", "mineral")
_r("prismatic_lens", "Prismatic Lens", "🌈", "mineral")
# Level 4
_r("warden_seal", "Warden Seal", "🏛️", "mineral")
_r("temporal_fragment", "Temporal Fragment", "⏳", "mineral")
_r("chrono_crystal", "Chrono Crystal", "⌛", "mineral")
# Level 5
_r("core_ember", "Core Ember", "🌋", "mineral")
_r("world_essence", "World Essence", "🌍", "mineral")
_r("heart_of_the_world", "Heart of the World", "❤️‍🔥", "mineral")

# ── Consumables ─────────────────────────────────────────────
_r("raw_potato", "Raw Potato", "🥔", "consumable")
_r("golden_mushroom", "Golden Mushroom", "🍄", "consumable")
_r("health_potion", "Health Potion", "❤️‍🩹", "consumable")
_r("bait_worm", "Worm Bait", "🪱", "consumable")
_r("bait_herring", "Herring Bait", "🐟", "consumable")
_r("bait_sturgeon", "Sturgeon Bait", "🐋", "consumable")
_r("stamina_elixir", "Stamina Elixir", "⚗️", "consumable")
_r("minor_stamina_brew", "Minor Stamina Brew", "🧪", "consumable")
_r("stamina_tonic", "Stamina Tonic", "🧴", "consumable")
_r("void_energy_flask", "Void Energy Flask", "⚗️", "consumable")
_r("fertilizer", "Fertilizer", "🧪", "consumable")
_r("water", "Water", "💧", "consumable")

# ── Combat Spoils (sellable mob loot) ─────────────────────────
_r("battle_spoils", "Battle Spoils", "🏆", "consumable")
_r("aether_spoils", "Aether Spoils", "🏆", "consumable")

# ── Special Equipment ─────────────────────────────────────────
_r("jackhammer", "Jackhammer", "⛏️", "consumable")

# ── Build alias index ───────────────────────────────────────
# Maps lowercased alias → item_key

_ALIAS_INDEX: dict[str, str] = {}

def _build_aliases() -> None:
    for key, info in _RESOURCES.items():
        # Item key itself
        _ALIAS_INDEX[key] = key
        # Display name lowercased
        _ALIAS_INDEX[info.display_name.lower()] = key
        # Display name with underscores
        underscore_name = info.display_name.lower().replace(" ", "_")
        if underscore_name != key:
            _ALIAS_INDEX[underscore_name] = key

_build_aliases()

# Short aliases that don't collide with other item keys
_ALIAS_INDEX["worm"] = "bait_worm"
_ALIAS_INDEX["herring"] = "bait_herring"
_ALIAS_INDEX["elixir"] = "stamina_elixir"

# ── Public API ──────────────────────────────────────────────

RESOURCES: Final[dict[str, ResourceInfo]] = _RESOURCES


def get_resource(item_key: str) -> Optional[ResourceInfo]:
    """Get resource info by exact item_key."""
    return _RESOURCES.get(item_key)


def resolve_item(alias: str) -> Optional[ResourceInfo]:
    """Resolve a user-typed name/alias to a ResourceInfo."""
    norm = alias.strip().lower()
    key = _ALIAS_INDEX.get(norm)
    if key is None:
        # Try with underscores
        key = _ALIAS_INDEX.get(norm.replace(" ", "_"))
    if key is None:
        return None
    return _RESOURCES.get(key)


def resolve_category(alias: str) -> Optional[str]:
    """Resolve a category alias to a canonical category key."""
    return CATEGORY_ALIASES.get(alias.strip().lower())


def get_home_location(category: str) -> str:
    """Get the home location for a category (no sell bonus there)."""
    return CATEGORY_HOME.get(category, "")

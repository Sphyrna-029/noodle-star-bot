"""Crafting use cases — craft combat items and potions from resources."""

from cogs.combat.constants import COMBAT_ITEMS, CRAFT_RECIPES, STAMINA_RECOVERY
from cogs.combat.dto import CraftResult, RecipeInfo
from database.repository import UserRepository


def _is_t6_plus(recipe_key: str) -> bool:
    """Check if a recipe produces T6+ combat gear (requires Aetherdepths)."""
    item = COMBAT_ITEMS.get(recipe_key)
    return item is not None and item.tier >= 6


class CraftingUseCases:
    """Manages crafting of combat items and consumables."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def craft(self, user_id: int, recipe_key: str) -> CraftResult:
        """Attempt to craft an item using inventory materials."""
        recipe = CRAFT_RECIPES.get(recipe_key)
        if not recipe:
            return CraftResult(
                success=False,
                message=f"Unknown recipe: `{recipe_key}`. Use `!recipes` to see available recipes.",
            )

        # T6+ gear requires Aetherdepths unlock
        if _is_t6_plus(recipe.result_key):
            aether = self.repo.get_aether_stats(user_id)
            if aether["aether_level"] < 1:
                return CraftResult(
                    success=False,
                    message="This recipe requires access to **The Aetherdepths**! Unlock it first.",
                )

        # Check if already owns equipment (non-stackable combat items)
        if recipe.result_key in COMBAT_ITEMS:
            if self.repo.has_equipment(user_id, recipe.result_key):
                return CraftResult(
                    success=False,
                    message=f"You already own **{recipe.result_name}** {recipe.result_emoji}!",
                )

        # Check ingredients
        inv_items = self.repo.get_inventory_items(user_id)
        item_counts: dict[str, list[int]] = {}
        for item in inv_items:
            key = item["item_key"]
            item_counts.setdefault(key, []).append(item["id"])

        missing = []
        for ingredient_key, required_count in recipe.ingredients:
            available = len(item_counts.get(ingredient_key, []))
            if available < required_count:
                display_name = ingredient_key.replace("_", " ").title()
                missing.append(f"**{display_name}** ({available}/{required_count})")

        if missing:
            return CraftResult(
                success=False,
                message=f"Missing ingredients:\n" + "\n".join(missing),
            )

        # Check inventory space for consumable results (equipment goes to separate table)
        if recipe.result_key not in COMBAT_ITEMS:
            if not self.repo.has_space(user_id):
                return CraftResult(
                    success=False,
                    message="Your inventory is full! Make room before crafting.",
                )

        # Consume ingredients (batch removal for atomicity)
        all_ids_to_remove = []
        for ingredient_key, required_count in recipe.ingredients:
            all_ids_to_remove.extend(item_counts[ingredient_key][:required_count])
        self.repo.remove_items_by_ids(user_id, all_ids_to_remove)

        # Grant the crafted item
        if recipe.result_key in COMBAT_ITEMS:
            # Combat equipment → user_equipment table
            self.repo.set_equipment(user_id, recipe.result_key, 1)
        elif recipe.result_key in STAMINA_RECOVERY:
            # Consumable potion → user_inventory_items table
            self.repo.add_item(user_id, recipe.result_key, category="consumable")
        else:
            # Generic item
            self.repo.add_item(user_id, recipe.result_key, category="consumable")

        return CraftResult(
            success=True,
            message=f"Crafted **{recipe.result_name}** {recipe.result_emoji}!",
            item_name=recipe.result_name,
            item_emoji=recipe.result_emoji,
        )

    def get_recipes(self, user_id: int) -> list[RecipeInfo]:
        """Get all recipes with availability info. Hides T6+ if Aetherdepths not unlocked."""
        # Check aether unlock once for filtering
        aether = self.repo.get_aether_stats(user_id)
        has_aether = aether["aether_level"] >= 1

        inv_items = self.repo.get_inventory_items(user_id)
        item_counts: dict[str, int] = {}
        for item in inv_items:
            key = item["item_key"]
            item_counts[key] = item_counts.get(key, 0) + 1

        recipes = []
        for key, recipe in CRAFT_RECIPES.items():
            # Hide T6+ recipes until Aetherdepths is unlocked
            if not has_aether and _is_t6_plus(recipe.result_key):
                continue

            can_craft = True
            for ingredient_key, required_count in recipe.ingredients:
                if item_counts.get(ingredient_key, 0) < required_count:
                    can_craft = False
                    break

            recipes.append(RecipeInfo(
                name=recipe.result_name,
                emoji=recipe.result_emoji,
                ingredients=[(k, c) for k, c in recipe.ingredients],
                description=recipe.description,
                can_craft=can_craft,
            ))

        return recipes

    def get_recipe(self, recipe_key: str, user_id: int = None) -> RecipeInfo | None:
        """Get info for a single recipe. Returns None for T6+ if Aetherdepths not unlocked."""
        recipe = CRAFT_RECIPES.get(recipe_key)
        if not recipe:
            return None

        # Hide T6+ until Aetherdepths unlocked
        if _is_t6_plus(recipe.result_key) and user_id:
            aether = self.repo.get_aether_stats(user_id)
            if aether["aether_level"] < 1:
                return None

        can_craft = False
        if user_id:
            inv_items = self.repo.get_inventory_items(user_id)
            item_counts: dict[str, int] = {}
            for item in inv_items:
                key = item["item_key"]
                item_counts[key] = item_counts.get(key, 0) + 1

            can_craft = True
            for ingredient_key, required_count in recipe.ingredients:
                if item_counts.get(ingredient_key, 0) < required_count:
                    can_craft = False
                    break

        return RecipeInfo(
            name=recipe.result_name,
            emoji=recipe.result_emoji,
            ingredients=[(k, c) for k, c in recipe.ingredients],
            description=recipe.description,
            can_craft=can_craft,
        )

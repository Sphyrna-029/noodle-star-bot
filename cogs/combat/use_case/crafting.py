"""Crafting use cases — craft combat items and potions from resources."""

from cogs.combat.constants import COMBAT_ITEMS, CRAFT_RECIPES, STAMINA_RECOVERY
from cogs.combat.dto import CraftResult, RecipeInfo
from database.repository import UserRepository


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
                missing.append(f"**{ingredient_key}** ({available}/{required_count})")

        if missing:
            return CraftResult(
                success=False,
                message=f"Missing ingredients:\n" + "\n".join(missing),
            )

        # Consume ingredients
        for ingredient_key, required_count in recipe.ingredients:
            ids = item_counts[ingredient_key][:required_count]
            for item_id in ids:
                self.repo.remove_items_by_ids(user_id, [item_id])

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
        """Get all recipes with availability info."""
        inv_items = self.repo.get_inventory_items(user_id)
        item_counts: dict[str, int] = {}
        for item in inv_items:
            key = item["item_key"]
            item_counts[key] = item_counts.get(key, 0) + 1

        recipes = []
        for key, recipe in CRAFT_RECIPES.items():
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
        """Get info for a single recipe."""
        recipe = CRAFT_RECIPES.get(recipe_key)
        if not recipe:
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

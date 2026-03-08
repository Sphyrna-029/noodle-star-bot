"""Pet use-cases for Tamagotchi-style companion gameplay."""

from __future__ import annotations

from cogs.pets.constants import (
    CLEAN_AMOUNT,
    CLEANLINESS_DECAY_PER_HOUR,
    FEED_AMOUNT,
    HAPPINESS_DECAY_PER_HOUR,
    HUNGER_DECAY_PER_HOUR,
    MAX_NEED,
    MIN_NEED,
    PET_CATALOG,
    PET_SPRITE_DIR,
    PLAY_AMOUNT,
    get_pet_by_alias,
)
from cogs.pets.dto import ActionResult, BuyPetResult, PetListResult, PetStatus
from database.repository import UserRepository


class PetUseCases:
    """Handles pet purchasing and care interactions."""

    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()

    def get_pet_shop_items(self):
        """Return all pets available for purchase."""
        return list(PET_CATALOG.values())

    def buy_pet(self, user_id: int, username: str, pet_query: str) -> BuyPetResult:
        """Buy a pet from the catalog."""
        pet = get_pet_by_alias(pet_query)
        if pet is None:
            return BuyPetResult(False, "That pet doesn't exist. Use `!petshop`.")

        if self.repo.user_owns_pet(user_id, pet.key):
            return BuyPetResult(
                False,
                f"You already own {pet.emoji} **{pet.display_name}**.",
            )

        stars = self.repo.get_user_stars(user_id, username)
        if stars < pet.price:
            return BuyPetResult(
                False,
                (
                    f"You need **{pet.price}** stars for {pet.emoji} **{pet.display_name}**, "
                    f"but you only have **{stars}**."
                ),
            )

        self.repo.update_user_stars(user_id, username, stars - pet.price)

        should_activate = not self.repo.user_has_active_pet(user_id)
        self.repo.create_user_pet(
            user_id=user_id,
            pet_key=pet.key,
            pet_name=pet.display_name,
            is_active=should_activate,
        )

        status = self.get_pet_status(user_id)
        return BuyPetResult(
            True,
            f"Adopted {pet.emoji} **{pet.display_name}**!",
            pet=status,
            price=pet.price,
            new_balance=stars - pet.price,
        )

    def get_pet_status(self, user_id: int) -> PetStatus | None:
        """Get active pet status for a user."""
        self.repo.apply_pet_decay(
            user_id,
            hunger_decay_per_hour=HUNGER_DECAY_PER_HOUR,
            cleanliness_decay_per_hour=CLEANLINESS_DECAY_PER_HOUR,
            happiness_decay_per_hour=HAPPINESS_DECAY_PER_HOUR,
        )
        row = self.repo.get_active_pet(user_id)
        if row is None:
            return None
        return self._to_pet_status(row)

    def list_owned_pets(self, user_id: int) -> PetListResult:
        """List all pets owned by the user."""
        self.repo.apply_pet_decay(
            user_id,
            hunger_decay_per_hour=HUNGER_DECAY_PER_HOUR,
            cleanliness_decay_per_hour=CLEANLINESS_DECAY_PER_HOUR,
            happiness_decay_per_hour=HAPPINESS_DECAY_PER_HOUR,
        )
        rows = self.repo.get_user_pets(user_id)
        return PetListResult([self._to_pet_status(row) for row in rows])

    def select_active_pet(self, user_id: int, pet_query: str) -> ActionResult:
        """Switch active pet to one the user owns."""
        pet = get_pet_by_alias(pet_query)
        if pet is None:
            return ActionResult(False, "Unknown pet. Use `!mypets`.")

        if not self.repo.user_owns_pet(user_id, pet.key):
            return ActionResult(False, "You don't own that pet yet.")

        self.repo.set_active_pet(user_id, pet.key)
        status = self.get_pet_status(user_id)
        return ActionResult(
            True,
            f"{pet.emoji} **{status.display_name}** is now your active pet.",
            pet=status,
        )

    def name_pet(self, user_id: int, pet_query: str, nickname: str) -> ActionResult:
        """Set or update a nickname for one owned pet."""
        pet = get_pet_by_alias(pet_query)
        if pet is None:
            return ActionResult(False, "Unknown pet. Use `!mypets`.")

        row = self.repo.get_user_pet(user_id, pet.key)
        if row is None:
            return ActionResult(False, "You don't own that pet.")

        clean_name = self._normalize_nickname(nickname)
        if clean_name is None:
            return ActionResult(False, "Nickname must be 1-24 characters.")

        self.repo.update_pet_nickname(user_id, pet.key, clean_name)
        updated = self.repo.get_user_pet(user_id, pet.key)
        if updated is None:
            return ActionResult(False, "Pet not found.")

        status = self._to_pet_status(updated)
        return ActionResult(
            True,
            f"Named {status.pet_emoji} **{status.pet_name}** as **{clean_name}**.",
            pet=status,
        )

    def rename_active_pet(self, user_id: int, nickname: str) -> ActionResult:
        """Rename the currently active pet."""
        row = self.repo.get_active_pet(user_id)
        if row is None:
            return ActionResult(False, "You don't have an active pet. Buy one with `!buypet`.")

        clean_name = self._normalize_nickname(nickname)
        if clean_name is None:
            return ActionResult(False, "Nickname must be 1-24 characters.")

        self.repo.update_pet_nickname(user_id, row["pet_key"], clean_name)
        updated = self.repo.get_active_pet(user_id)
        if updated is None:
            return ActionResult(False, "No active pet found.")

        status = self._to_pet_status(updated)
        return ActionResult(
            True,
            f"Renamed your active pet to **{clean_name}**.",
            pet=status,
        )

    def feed_pet(self, user_id: int) -> ActionResult:
        """Feed the active pet."""
        return self._update_need(user_id, "hunger", FEED_AMOUNT, "Fed")

    def clean_pet(self, user_id: int) -> ActionResult:
        """Clean the active pet."""
        return self._update_need(user_id, "cleanliness", CLEAN_AMOUNT, "Cleaned")

    def play_with_pet(self, user_id: int) -> ActionResult:
        """Play with the active pet."""
        return self._update_need(user_id, "happiness", PLAY_AMOUNT, "Played with")

    def _update_need(
        self,
        user_id: int,
        stat_name: str,
        increase_amount: int,
        verb: str,
    ) -> ActionResult:
        self.repo.apply_pet_decay(
            user_id,
            hunger_decay_per_hour=HUNGER_DECAY_PER_HOUR,
            cleanliness_decay_per_hour=CLEANLINESS_DECAY_PER_HOUR,
            happiness_decay_per_hour=HAPPINESS_DECAY_PER_HOUR,
        )
        row = self.repo.get_active_pet(user_id)
        if row is None:
            return ActionResult(False, "You don't have an active pet. Buy one with `!buypet`.")

        current = int(row[stat_name])
        new_value = min(MAX_NEED, max(MIN_NEED, current + increase_amount))

        self.repo.update_pet_need(user_id, row["pet_key"], stat_name, new_value)
        updated = self.repo.get_active_pet(user_id)
        if updated is None:
            return ActionResult(False, "No active pet found.")

        status = self._to_pet_status(updated)
        return ActionResult(
            True,
            f"{verb} {status.pet_emoji} **{status.display_name}**. {stat_name.title()}: **{new_value}%**",
            pet=status,
        )

    @staticmethod
    def _normalize_nickname(nickname: str) -> str | None:
        clean = " ".join(nickname.split()).strip()
        if not clean or len(clean) > 24:
            return None
        return clean

    @staticmethod
    def _derive_mood(hunger: int, cleanliness: int, happiness: int) -> tuple[str, str]:
        score = (hunger + cleanliness + happiness) / 3
        if score >= 75:
            return "happy", "happy"
        if score >= 35:
            return "idle", "default"
        return "sad", "sad"

    def _to_pet_status(self, row) -> PetStatus:
        hunger = int(row["hunger"])
        cleanliness = int(row["cleanliness"])
        happiness = int(row["happiness"])
        mood, sprite_state = self._derive_mood(hunger, cleanliness, happiness)

        catalog = PET_CATALOG.get(row["pet_key"])
        pet_emoji = catalog.emoji if catalog else "🐾"
        sprite_path = None
        if catalog is not None:
            candidate = PET_SPRITE_DIR / catalog.sprite_file
            if candidate.exists():
                sprite_path = str(candidate)

        return PetStatus(
            user_id=int(row["user_id"]),
            pet_key=row["pet_key"],
            pet_name=row["pet_name"],
            pet_nickname=row["pet_nickname"],
            pet_emoji=pet_emoji,
            is_active=bool(row["is_active"]),
            hunger=hunger,
            cleanliness=cleanliness,
            happiness=happiness,
            mood=mood,
            sprite_state=sprite_state,
            sprite_path=sprite_path,
        )

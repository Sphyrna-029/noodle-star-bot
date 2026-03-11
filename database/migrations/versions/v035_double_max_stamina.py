"""Double max_stamina from 50 to 100 for all existing players.

Also bumps current_stamina to 100 for anyone still at or below 50.
"""

DESCRIPTION = "Double max_stamina from 50 to 100 for existing players"


def upgrade(cursor) -> None:
    # Double max_stamina for anyone still at the old default of 50
    cursor.execute(
        "UPDATE user_progression SET max_stamina = 100 WHERE max_stamina = 50"
    )
    # Bump current_stamina to new max for anyone at or below old max
    # (so players don't log in with 50/100 stamina)
    cursor.execute(
        "UPDATE user_progression SET current_stamina = 100 WHERE current_stamina <= 50"
    )


def downgrade(cursor) -> None:
    cursor.execute(
        "UPDATE user_progression SET max_stamina = 50 WHERE max_stamina = 100"
    )
    cursor.execute(
        "UPDATE user_progression SET current_stamina = 50 WHERE current_stamina > 50"
    )

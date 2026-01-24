"""Formatting utilities for Noodle Star Bot."""

from datetime import timedelta


def format_time_remaining(time_remaining: timedelta) -> str:
    """
    Format a timedelta as "Xm Ys" string.

    Args:
        time_remaining: The time remaining as a timedelta

    Returns:
        Formatted string like "5m 30s"
    """
    total_seconds = int(time_remaining.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}m {seconds}s"


def format_stars_balance(wallet: int, bank: int) -> str:
    """
    Format a user's star balance for display.

    Args:
        wallet: Stars in wallet
        bank: Stars in bank

    Returns:
        Formatted multi-line string
    """
    total = wallet + bank
    return (
        f"💰 Wallet: **{wallet}** stars\n"
        f"🏦 Bank: **{bank}** stars\n"
        f"📊 Total: **{total}** stars"
    )

"""Gambling repository operations."""

from datetime import datetime
from typing import Optional


from database.repositories.base import BaseRepository


class GamblingRepository(BaseRepository):
    """Duel stamina and blackjack cooldown operations."""

    def _ensure_activity_row(self, cursor, user_id: int) -> None:
        cursor.execute(
            """
            INSERT INTO user_activity (
                user_id, stamina, stamina_last_updated, stamina_last_reset,
                last_duel_amount, last_duel_at, last_mine, last_deposit,
                last_withdraw, last_fish, last_blackjack
            ) VALUES (?, 100, NULL, NULL, 0, NULL, NULL, NULL, NULL, NULL, NULL)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )

    def get_duel_stamina_state(self, user_id: int) -> dict:
        """Get stamina state for duels."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                """
                SELECT stamina, stamina_last_updated, stamina_last_reset,
                       last_duel_amount, last_duel_at
                FROM user_activity WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "stamina": 0,
                    "stamina_last_updated": None,
                    "stamina_last_reset": None,
                    "last_duel_amount": 0,
                    "last_duel_at": None,
                }

            stamina_last_updated = (
                datetime.fromisoformat(row["stamina_last_updated"])
                if row["stamina_last_updated"]
                else None
            )
            stamina_last_reset = (
                datetime.fromisoformat(row["stamina_last_reset"])
                if row["stamina_last_reset"]
                else None
            )
            last_duel_at = (
                datetime.fromisoformat(row["last_duel_at"]) if row["last_duel_at"] else None
            )

            return {
                "stamina": row["stamina"] or 0,
                "stamina_last_updated": stamina_last_updated,
                "stamina_last_reset": stamina_last_reset,
                "last_duel_amount": row["last_duel_amount"] or 0,
                "last_duel_at": last_duel_at,
            }

    def update_duel_stamina_state(
        self,
        user_id: int,
        stamina: int,
        stamina_last_updated: datetime,
        stamina_last_reset: datetime,
        last_duel_amount: int,
        last_duel_at: datetime | None,
    ) -> None:
        """Update stamina state for duels."""
        with self.db.get_cursor() as cursor:
            self._ensure_activity_row(cursor, user_id)
            cursor.execute(
                """
                UPDATE user_activity
                SET stamina = ?,
                    stamina_last_updated = ?,
                    stamina_last_reset = ?,
                    last_duel_amount = ?,
                    last_duel_at = ?
                WHERE user_id = ?
                """,
                (
                    stamina,
                    stamina_last_updated.isoformat(),
                    stamina_last_reset.isoformat(),
                    last_duel_amount,
                    last_duel_at.isoformat() if last_duel_at else None,
                    user_id,
                ),
            )

    def get_last_blackjack(self, user_id: int) -> Optional[datetime]:
        """Get the user's last blackjack game timestamp."""
        with self.db.get_cursor() as cursor:
            try:
                self._ensure_activity_row(cursor, user_id)
                cursor.execute(
                    "SELECT last_blackjack FROM user_activity WHERE user_id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()

                if row is None or row["last_blackjack"] is None:
                    return None

                return datetime.fromisoformat(row["last_blackjack"])
            except Exception:
                return None

    def update_last_blackjack(self, user_id: int) -> None:
        """Update the user's last blackjack game timestamp to now."""
        with self.db.get_cursor() as cursor:
            try:
                self._ensure_activity_row(cursor, user_id)
                now = datetime.now().isoformat()
                cursor.execute(
                    "UPDATE user_activity SET last_blackjack = ? WHERE user_id = ?",
                    (now, user_id),
                )
            except Exception:
                pass

    def create_roulette_invite(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        amount: int,
        channel_id: int,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        """Create a pending roulette invite."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO game_invites (
                    game_type, challenger_id, challenger_name, opponent_id, opponent_name,
                    amount, channel_id, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "russian_roulette",
                    challenger_id,
                    challenger_name,
                    opponent_id,
                    opponent_name,
                    amount,
                    channel_id,
                    created_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def find_pending_roulette_invite_involving_user(
        self,
        user_id: int,
        challenger_id: int | None = None,
    ) -> Optional[dict]:
        """Find a pending invite where the user is challenger or opponent."""
        with self.db.get_cursor() as cursor:
            if challenger_id is not None:
                cursor.execute(
                    """
                    SELECT id, challenger_id, challenger_name, opponent_id, opponent_name,
                           amount, channel_id, created_at, expires_at
                    FROM game_invites
                    WHERE game_type = 'russian_roulette'
                      AND ((challenger_id = ? AND opponent_id = ?)
                        OR (challenger_id = ? AND opponent_id = ?)
                      )
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id, challenger_id, challenger_id, user_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, challenger_id, challenger_name, opponent_id, opponent_name,
                           amount, channel_id, created_at, expires_at
                    FROM game_invites
                    WHERE game_type = 'russian_roulette'
                      AND (challenger_id = ? OR opponent_id = ?)
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id, user_id),
                )
            row = cursor.fetchone()
            return dict(row) if row else None

    def find_pending_roulette_invite_for_opponent(
        self,
        opponent_id: int,
        challenger_id: int | None = None,
    ) -> Optional[dict]:
        """Find a pending invite addressed to an opponent."""
        with self.db.get_cursor() as cursor:
            if challenger_id is not None:
                cursor.execute(
                    """
                    SELECT id, challenger_id, challenger_name, opponent_id, opponent_name,
                           amount, channel_id, created_at, expires_at
                    FROM game_invites
                    WHERE game_type = 'russian_roulette'
                      AND opponent_id = ? AND challenger_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (opponent_id, challenger_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, challenger_id, challenger_name, opponent_id, opponent_name,
                           amount, channel_id, created_at, expires_at
                    FROM game_invites
                    WHERE game_type = 'russian_roulette'
                      AND opponent_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (opponent_id,),
                )
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_expired_roulette_invites(self, now: datetime) -> int:
        """Delete expired roulette invites and return number removed."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM game_invites WHERE game_type = ? AND expires_at <= ?",
                ("russian_roulette", now.isoformat()),
            )
            return cursor.rowcount

    def delete_roulette_invite(self, invite_id: int) -> None:
        """Delete a specific roulette invite."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM game_invites WHERE id = ? AND game_type = ?",
                (invite_id, "russian_roulette"),
            )

    def settle_roulette_pvp_bet(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        amount: int,
        winner_id: int,
    ) -> Optional[dict]:
        """
        Settle a PvP roulette wager atomically using wallet+bank for stakes.

        Returns updated balances dict, or None if either user can't cover the wager.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, stars, bank
                FROM noodle_stars
                WHERE user_id IN (?, ?)
                """,
                (challenger_id, opponent_id),
            )
            rows = cursor.fetchall()
            if len(rows) != 2:
                return None

            by_id = {row["user_id"]: row for row in rows}
            challenger = by_id.get(challenger_id)
            opponent = by_id.get(opponent_id)
            if challenger is None or opponent is None:
                return None

            challenger_wallet = challenger["stars"] or 0
            challenger_bank = challenger["bank"] or 0
            opponent_wallet = opponent["stars"] or 0
            opponent_bank = opponent["bank"] or 0

            if challenger_wallet + challenger_bank < amount:
                return None
            if opponent_wallet + opponent_bank < amount:
                return None

            challenger_wallet_take = min(challenger_wallet, amount)
            challenger_bank_take = amount - challenger_wallet_take
            challenger_wallet -= challenger_wallet_take
            challenger_bank -= challenger_bank_take

            opponent_wallet_take = min(opponent_wallet, amount)
            opponent_bank_take = amount - opponent_wallet_take
            opponent_wallet -= opponent_wallet_take
            opponent_bank -= opponent_bank_take

            pot = amount * 2
            if winner_id == challenger_id:
                challenger_wallet += pot
            elif winner_id == opponent_id:
                opponent_wallet += pot
            else:
                return None

            cursor.execute(
                """
                UPDATE noodle_stars
                SET stars = ?, bank = ?, username = ?
                WHERE user_id = ?
                """,
                (challenger_wallet, challenger_bank, challenger_name, challenger_id),
            )
            cursor.execute(
                """
                UPDATE noodle_stars
                SET stars = ?, bank = ?, username = ?
                WHERE user_id = ?
                """,
                (opponent_wallet, opponent_bank, opponent_name, opponent_id),
            )

            # Annotate latest star_ledger rows produced by this settlement.
            try:
                if challenger_wallet != (challenger["stars"] or 0):
                    cursor.execute(
                        """
                        UPDATE star_ledger
                        SET source = ?, reason = ?
                        WHERE id = (
                            SELECT id FROM star_ledger
                            WHERE user_id = ?
                            ORDER BY id DESC
                            LIMIT 1
                        )
                        """,
                        ("gambling", "russian_pvp_result", challenger_id),
                    )
                if opponent_wallet != (opponent["stars"] or 0):
                    cursor.execute(
                        """
                        UPDATE star_ledger
                        SET source = ?, reason = ?
                        WHERE id = (
                            SELECT id FROM star_ledger
                            WHERE user_id = ?
                            ORDER BY id DESC
                            LIMIT 1
                        )
                        """,
                        ("gambling", "russian_pvp_result", opponent_id),
                    )
            except Exception:
                pass

            return {
                "challenger_wallet": challenger_wallet,
                "challenger_bank": challenger_bank,
                "opponent_wallet": opponent_wallet,
                "opponent_bank": opponent_bank,
            }

    def lock_roulette_pvp_bet(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        amount: int,
    ) -> Optional[dict]:
        """Lock both players' stakes from wallet+bank at game start."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, stars, bank
                FROM noodle_stars
                WHERE user_id IN (?, ?)
                """,
                (challenger_id, opponent_id),
            )
            rows = cursor.fetchall()
            if len(rows) != 2:
                return None

            by_id = {row["user_id"]: row for row in rows}
            challenger = by_id.get(challenger_id)
            opponent = by_id.get(opponent_id)
            if challenger is None or opponent is None:
                return None

            challenger_wallet_before = challenger["stars"] or 0
            challenger_bank_before = challenger["bank"] or 0
            opponent_wallet_before = opponent["stars"] or 0
            opponent_bank_before = opponent["bank"] or 0

            if challenger_wallet_before + challenger_bank_before < amount:
                return None
            if opponent_wallet_before + opponent_bank_before < amount:
                return None

            challenger_wallet_take = min(challenger_wallet_before, amount)
            challenger_bank_take = amount - challenger_wallet_take
            challenger_wallet = challenger_wallet_before - challenger_wallet_take
            challenger_bank = challenger_bank_before - challenger_bank_take

            opponent_wallet_take = min(opponent_wallet_before, amount)
            opponent_bank_take = amount - opponent_wallet_take
            opponent_wallet = opponent_wallet_before - opponent_wallet_take
            opponent_bank = opponent_bank_before - opponent_bank_take

            cursor.execute(
                """
                UPDATE noodle_stars
                SET stars = ?, bank = ?, username = ?
                WHERE user_id = ?
                """,
                (challenger_wallet, challenger_bank, challenger_name, challenger_id),
            )
            cursor.execute(
                """
                UPDATE noodle_stars
                SET stars = ?, bank = ?, username = ?
                WHERE user_id = ?
                """,
                (opponent_wallet, opponent_bank, opponent_name, opponent_id),
            )

            # Annotate stake lock wallet deltas.
            try:
                if challenger_wallet != challenger_wallet_before:
                    cursor.execute(
                        """
                        UPDATE star_ledger
                        SET source = ?, reason = ?
                        WHERE id = (
                            SELECT id FROM star_ledger
                            WHERE user_id = ?
                            ORDER BY id DESC
                            LIMIT 1
                        )
                        """,
                        ("gambling", "russian_pvp_lock", challenger_id),
                    )
                if opponent_wallet != opponent_wallet_before:
                    cursor.execute(
                        """
                        UPDATE star_ledger
                        SET source = ?, reason = ?
                        WHERE id = (
                            SELECT id FROM star_ledger
                            WHERE user_id = ?
                            ORDER BY id DESC
                            LIMIT 1
                        )
                        """,
                        ("gambling", "russian_pvp_lock", opponent_id),
                    )
            except Exception:
                pass

            return {
                "challenger_wallet": challenger_wallet,
                "challenger_bank": challenger_bank,
                "opponent_wallet": opponent_wallet,
                "opponent_bank": opponent_bank,
            }

    def payout_roulette_pvp_winner(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        winner_id: int,
        pot_amount: int,
    ) -> Optional[dict]:
        """Pay the locked pot to the winner and return both balances."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, stars, bank
                FROM noodle_stars
                WHERE user_id IN (?, ?)
                """,
                (challenger_id, opponent_id),
            )
            rows = cursor.fetchall()
            if len(rows) != 2:
                return None

            by_id = {row["user_id"]: row for row in rows}
            challenger = by_id.get(challenger_id)
            opponent = by_id.get(opponent_id)
            if challenger is None or opponent is None:
                return None

            challenger_wallet = challenger["stars"] or 0
            challenger_bank = challenger["bank"] or 0
            opponent_wallet = opponent["stars"] or 0
            opponent_bank = opponent["bank"] or 0

            if winner_id == challenger_id:
                challenger_wallet_before = challenger_wallet
                challenger_wallet += pot_amount
                cursor.execute(
                    """
                    UPDATE noodle_stars
                    SET stars = ?, username = ?
                    WHERE user_id = ?
                    """,
                    (challenger_wallet, challenger_name, challenger_id),
                )
                cursor.execute(
                    "UPDATE noodle_stars SET username = ? WHERE user_id = ?",
                    (opponent_name, opponent_id),
                )
                winner_wallet_changed = challenger_wallet != challenger_wallet_before
                winner_user_id = challenger_id
            elif winner_id == opponent_id:
                opponent_wallet_before = opponent_wallet
                opponent_wallet += pot_amount
                cursor.execute(
                    """
                    UPDATE noodle_stars
                    SET stars = ?, username = ?
                    WHERE user_id = ?
                    """,
                    (opponent_wallet, opponent_name, opponent_id),
                )
                cursor.execute(
                    "UPDATE noodle_stars SET username = ? WHERE user_id = ?",
                    (challenger_name, challenger_id),
                )
                winner_wallet_changed = opponent_wallet != opponent_wallet_before
                winner_user_id = opponent_id
            else:
                return None

            try:
                if winner_wallet_changed:
                    cursor.execute(
                        """
                        UPDATE star_ledger
                        SET source = ?, reason = ?
                        WHERE id = (
                            SELECT id FROM star_ledger
                            WHERE user_id = ?
                            ORDER BY id DESC
                            LIMIT 1
                        )
                        """,
                        ("gambling", "russian_pvp_result", winner_user_id),
                    )
            except Exception:
                pass

            return {
                "challenger_wallet": challenger_wallet,
                "challenger_bank": challenger_bank,
                "opponent_wallet": opponent_wallet,
                "opponent_bank": opponent_bank,
            }

    # ------------------------------------------------------------------
    # PvP Duel — wallet-only wager locking & payout
    # ------------------------------------------------------------------

    def lock_duel_bet(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        amount: int,
    ) -> Optional[dict]:
        """Deduct wager from each player's wallet (wallet-only). Returns None if either can't afford."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, stars FROM noodle_stars WHERE user_id IN (?, ?)",
                (challenger_id, opponent_id),
            )
            rows = cursor.fetchall()
            if len(rows) != 2:
                return None

            by_id = {row["user_id"]: row for row in rows}
            challenger = by_id.get(challenger_id)
            opponent = by_id.get(opponent_id)
            if challenger is None or opponent is None:
                return None

            c_wallet = challenger["stars"] or 0
            o_wallet = opponent["stars"] or 0

            if c_wallet < amount or o_wallet < amount:
                return None

            c_wallet -= amount
            o_wallet -= amount

            cursor.execute(
                "UPDATE noodle_stars SET stars = ?, username = ? WHERE user_id = ?",
                (c_wallet, challenger_name, challenger_id),
            )
            cursor.execute(
                "UPDATE noodle_stars SET stars = ?, username = ? WHERE user_id = ?",
                (o_wallet, opponent_name, opponent_id),
            )

            try:
                for uid in (challenger_id, opponent_id):
                    cursor.execute(
                        """
                        UPDATE star_ledger
                        SET source = ?, reason = ?
                        WHERE id = (
                            SELECT id FROM star_ledger
                            WHERE user_id = ?
                            ORDER BY id DESC
                            LIMIT 1
                        )
                        """,
                        ("gambling", "duel_pvp_lock", uid),
                    )
            except Exception:
                pass

            return {
                "challenger_wallet": c_wallet,
                "opponent_wallet": o_wallet,
            }

    def payout_duel_winner(
        self,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        winner_id: int,
        pot_amount: int,
    ) -> Optional[dict]:
        """Pay the locked pot to the winner's wallet. Returns both balances."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, stars FROM noodle_stars WHERE user_id IN (?, ?)",
                (challenger_id, opponent_id),
            )
            rows = cursor.fetchall()
            if len(rows) != 2:
                return None

            by_id = {row["user_id"]: row for row in rows}
            challenger = by_id.get(challenger_id)
            opponent = by_id.get(opponent_id)
            if challenger is None or opponent is None:
                return None

            c_wallet = challenger["stars"] or 0
            o_wallet = opponent["stars"] or 0

            if winner_id == challenger_id:
                c_wallet += pot_amount
            elif winner_id == opponent_id:
                o_wallet += pot_amount
            else:
                return None

            cursor.execute(
                "UPDATE noodle_stars SET stars = ?, username = ? WHERE user_id = ?",
                (c_wallet, challenger_name, challenger_id),
            )
            cursor.execute(
                "UPDATE noodle_stars SET stars = ?, username = ? WHERE user_id = ?",
                (o_wallet, opponent_name, opponent_id),
            )

            try:
                cursor.execute(
                    """
                    UPDATE star_ledger
                    SET source = ?, reason = ?
                    WHERE id = (
                        SELECT id FROM star_ledger
                        WHERE user_id = ?
                        ORDER BY id DESC
                        LIMIT 1
                    )
                    """,
                    ("gambling", "duel_pvp_result", winner_id),
                )
            except Exception:
                pass

            return {
                "challenger_wallet": c_wallet,
                "opponent_wallet": o_wallet,
            }

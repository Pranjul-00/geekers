"""Expresso Storage Engine.

Persists player daily scores, streaks, channel subscriptions, and reminder settings via SQLite.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DB_PATH = Path(__file__).resolve().parent / "expresso.db"


@dataclass
class PlayerResult:
    guild_id: int
    channel_id: int
    user_id: int
    user_name: str
    game_id: int
    guesses_count: int
    solve_time_seconds: int
    hints_used: int
    solved: bool
    completed_at: str


@dataclass
class PlayerStats:
    user_id: int
    user_name: str
    total_played: int
    total_solved: int
    current_streak: int
    max_streak: int
    avg_guesses: float
    fastest_solve_seconds: int


class ExpressoStorage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    game_id INTEGER NOT NULL,
                    guesses_count INTEGER NOT NULL,
                    solve_time_seconds INTEGER NOT NULL,
                    hints_used INTEGER NOT NULL,
                    solved BOOLEAN NOT NULL,
                    completed_at TEXT NOT NULL,
                    UNIQUE(guild_id, channel_id, user_id, game_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    channel_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    reminder_hour_utc INTEGER DEFAULT 20, -- 8 PM UTC nudge before midnight
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def record_result(self, res: PlayerResult) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO results (
                    guild_id, channel_id, user_id, user_name, game_id,
                    guesses_count, solve_time_seconds, hints_used, solved, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    res.guild_id,
                    res.channel_id,
                    res.user_id,
                    res.user_name,
                    res.game_id,
                    res.guesses_count,
                    res.solve_time_seconds,
                    res.hints_used,
                    1 if res.solved else 0,
                    res.completed_at,
                ),
            )
            conn.commit()

    def get_channel_daily_results(self, channel_id: int, game_id: int) -> List[PlayerResult]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM results
                WHERE channel_id = ? AND game_id = ?
                ORDER BY solved DESC, guesses_count ASC, solve_time_seconds ASC
                """,
                (channel_id, game_id),
            ).fetchall()

            return [
                PlayerResult(
                    guild_id=r["guild_id"],
                    channel_id=r["channel_id"],
                    user_id=r["user_id"],
                    user_name=r["user_name"],
                    game_id=r["game_id"],
                    guesses_count=r["guesses_count"],
                    solve_time_seconds=r["solve_time_seconds"],
                    hints_used=r["hints_used"],
                    solved=bool(r["solved"]),
                    completed_at=r["completed_at"],
                )
                for r in rows
            ]

    def get_player_stats(self, guild_id: int, user_id: int) -> Optional[PlayerStats]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM results
                WHERE guild_id = ? AND user_id = ?
                ORDER BY game_id ASC
                """,
                (guild_id, user_id),
            ).fetchall()

            if not rows:
                return None

            user_name = rows[-1]["user_name"]
            total_played = len(rows)
            total_solved = sum(1 for r in rows if r["solved"])
            solved_rows = [r for r in rows if r["solved"]]
            avg_guesses = (
                sum(r["guesses_count"] for r in solved_rows) / len(solved_rows)
                if solved_rows
                else 0.0
            )
            fastest_solve = (
                min(r["solve_time_seconds"] for r in solved_rows)
                if solved_rows
                else 0
            )

            # Calculate current streak and max streak
            cur_streak = 0
            max_streak = 0
            temp_streak = 0
            for r in rows:
                if r["solved"]:
                    temp_streak += 1
                    max_streak = max(max_streak, temp_streak)
                else:
                    temp_streak = 0
            # Current streak is temp_streak if last played game was solved
            cur_streak = temp_streak if rows[-1]["solved"] else 0

            return PlayerStats(
                user_id=user_id,
                user_name=user_name,
                total_played=total_played,
                total_solved=total_solved,
                current_streak=cur_streak,
                max_streak=max_streak,
                avg_guesses=round(avg_guesses, 2),
                fastest_solve_seconds=fastest_solve,
            )

    def add_subscription(self, channel_id: int, guild_id: int) -> None:
        with self._get_connection() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO subscriptions (channel_id, guild_id, created_at)
                VALUES (?, ?, ?)
                """,
                (channel_id, guild_id, now),
            )
            conn.commit()

    def remove_subscription(self, channel_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM subscriptions WHERE channel_id = ?", (channel_id,))
            conn.commit()

    def get_subscriptions(self) -> List[Tuple[int, int, int]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT channel_id, guild_id, reminder_hour_utc FROM subscriptions").fetchall()
            return [(r["channel_id"], r["guild_id"], r["reminder_hour_utc"]) for r in rows]

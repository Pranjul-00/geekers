"""Expresso Game Engine.

Handles phrase guessing mechanics, daily game calculation, and feedback generation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Expresso epoch calibrated with official site: 2026-10-26 is Game #26
EXPRESSO_EPOCH = date(2026, 10, 1)
PHRASES_FILE = Path(__file__).resolve().parent / "phrases.json"


def clean_text(text: str) -> str:
    """Normalize text to uppercase letters and spaces."""
    return re.sub(r"[^A-Z ]", "", text.upper().strip())


@dataclass
class GuessFeedback:
    guess_text: str
    feedback_emojis: str  # e.g., 🟩🟩⬛ 🟨🟩
    is_correct: bool
    revealed_board: str


@dataclass
class ExpressoPuzzle:
    game_id: int
    phrase: str
    hint: str
    category: str


class ExpressoCatalog:
    _puzzles: List[ExpressoPuzzle] = []

    @classmethod
    def load(cls) -> None:
        if cls._puzzles:
            return
        if not PHRASES_FILE.exists():
            cls._puzzles = [
                ExpressoPuzzle(1, "PIECE OF CAKE", "Something very easy", "Idiom"),
                ExpressoPuzzle(2, "BREAK A LEG", "Wishing good luck", "Theater"),
            ]
            return

        with open(PHRASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            cls._puzzles = [
                ExpressoPuzzle(
                    game_id=item["id"],
                    phrase=clean_text(item["phrase"]),
                    hint=item.get("hint", "No hint available"),
                    category=item.get("category", "General"),
                )
                for item in data
            ]

    @classmethod
    def get_by_id(cls, game_id: int) -> ExpressoPuzzle:
        cls.load()
        idx = (game_id - 1) % len(cls._puzzles)
        p = cls._puzzles[idx]
        return ExpressoPuzzle(game_id, p.phrase, p.hint, p.category)

    @classmethod
    def get_for_date(cls, d: date) -> ExpressoPuzzle:
        game_id = max(1, (d - EXPRESSO_EPOCH).days + 1)
        return cls.get_by_id(game_id)

    @classmethod
    def get_today(cls) -> ExpressoPuzzle:
        return cls.get_for_date(date.today())


class ExpressoSession:
    def __init__(self, puzzle: ExpressoPuzzle, channel_id: int, user_id: int):
        self.puzzle = puzzle
        self.channel_id = channel_id
        self.user_id = user_id
        self.started_at = datetime.now(timezone.utc)
        self.finished_at: Optional[datetime] = None
        self.guesses: List[str] = []
        self.history: List[GuessFeedback] = []
        self.discovered_letters: set[str] = set()
        self.hints_used: int = 0
        self.solved: bool = False
        self.given_up: bool = False

    @property
    def target_phrase(self) -> str:
        return self.puzzle.phrase

    @property
    def target_words(self) -> List[str]:
        return self.puzzle.phrase.split()

    @property
    def elapsed_seconds(self) -> int:
        end = self.finished_at or datetime.now(timezone.utc)
        return int((end - self.started_at).total_seconds())

    @property
    def elapsed_formatted(self) -> str:
        sec = self.elapsed_seconds
        mins, s = divmod(sec, 60)
        return f"{mins}m {s:02d}s"

    def get_masked_board(self) -> str:
        """Render board showing revealed letters and underscores."""
        out = []
        for char in self.target_phrase:
            if char == " ":
                out.append("  ")
            elif char in self.discovered_letters:
                out.append(f"{char} ")
            else:
                out.append("_ ")
        return "".join(out).strip()

    def make_guess(self, raw_guess: str) -> GuessFeedback:
        cleaned = clean_text(raw_guess)
        if not cleaned:
            return GuessFeedback(raw_guess, "", False, self.get_masked_board())

        self.guesses.append(cleaned)
        is_exact = cleaned == self.target_phrase

        # Evaluation
        target = self.target_phrase
        emojis = []
        
        # Wordle-style matching against words or characters
        for i, char in enumerate(cleaned):
            if i < len(target) and target[i] == char:
                emojis.append("🟩")
                self.discovered_letters.add(char)
            elif char in target:
                emojis.append("🟨")
            else:
                emojis.append("⬛")

        if is_exact:
            self.solved = True
            self.finished_at = datetime.now(timezone.utc)
            for c in target:
                if c != " ":
                    self.discovered_letters.add(c)

        feedback = GuessFeedback(
            guess_text=cleaned,
            feedback_emojis="".join(emojis),
            is_correct=is_exact,
            revealed_board=self.get_masked_board(),
        )
        self.history.append(feedback)
        return feedback

    def give_up(self) -> str:
        self.given_up = True
        self.finished_at = datetime.now(timezone.utc)
        return self.target_phrase

    def use_hint(self) -> Tuple[int, str]:
        """Reveal one unrevealed letter or return category/hint."""
        self.hints_used += 1
        unrevealed = [c for c in self.target_phrase if c != " " and c not in self.discovered_letters]
        if unrevealed:
            chosen = unrevealed[0]
            self.discovered_letters.add(chosen)
            return self.hints_used, f"Revealed letter: **{chosen}**"
        return self.hints_used, f"Clue: *{self.puzzle.hint}* (Category: **{self.puzzle.category}**)"

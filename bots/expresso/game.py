"""Expresso Game Engine.

Handles phrase guessing mechanics, daily game calculation, and feedback generation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Expresso epoch calibrated with official site: 2026-10-26 is Game #26
EXPRESSO_EPOCH = date(2026, 10, 1)
PHRASES_FILE = Path(__file__).resolve().parent / "phrases.json"


def clean_text(text: str) -> str:
    """Normalize text to uppercase letters and spaces."""
    return re.sub(r"[^A-Z ]", "", text.upper().strip())


@dataclass
class LetterEvaluation:
    char: str
    status: str  # "green", "yellow", "gray"
    emoji: str   # 🟩, 🟨, ⬛


@dataclass
class GuessFeedback:
    guess_text: str
    letter_evaluations: List[LetterEvaluation]
    feedback_line: str
    explanation: str
    is_correct: bool
    revealed_board: str
    word_lengths_info: str
    found_letters: List[str]
    eliminated_letters: List[str]


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
        self.discovered_letters: Set[str] = set()
        self.eliminated_letters: Set[str] = set()
        self.revealed_indices: Set[int] = set()  # Absolute char indices in target_phrase
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

    def get_word_lengths_info(self) -> str:
        parts = [f"({len(w)} letters)" for w in self.target_words]
        return "   ".join(parts)

    def get_masked_board(self) -> str:
        """Render board showing revealed letters and underscores grouped by word."""
        word_renders = []
        for word in self.target_words:
            chars = []
            for c in word:
                if c in self.discovered_letters:
                    chars.append(f"`{c}`")
                else:
                    chars.append("`_`")
            word_renders.append(" ".join(chars))
        return "    ".join(word_renders)

    def make_guess(self, raw_guess: str) -> GuessFeedback:
        cleaned = clean_text(raw_guess)
        if not cleaned:
            return GuessFeedback(
                guess_text=raw_guess,
                letter_evaluations=[],
                feedback_line="",
                explanation="Empty guess.",
                is_correct=False,
                revealed_board=self.get_masked_board(),
                word_lengths_info=self.get_word_lengths_info(),
                found_letters=sorted(list(self.discovered_letters)),
                eliminated_letters=sorted(list(self.eliminated_letters)),
            )

        self.guesses.append(cleaned)
        is_exact = cleaned == self.target_phrase
        target = self.target_phrase
        target_words = self.target_words
        guess_words = cleaned.split()

        evaluations: List[LetterEvaluation] = []
        green_chars = set()
        yellow_chars = set()
        gray_chars = set()

        if is_exact:
            self.solved = True
            self.finished_at = datetime.now(timezone.utc)
            for char in cleaned:
                if char != " ":
                    self.discovered_letters.add(char)
                    evaluations.append(LetterEvaluation(char, "green", "🟩"))
                    green_chars.add(char)
        else:
            # Word-by-word or character-by-character evaluation
            if len(guess_words) == len(target_words):
                # Matched word for word
                for g_word, t_word in zip(guess_words, target_words):
                    for i, char in enumerate(g_word):
                        if i < len(t_word) and t_word[i] == char:
                            evaluations.append(LetterEvaluation(char, "green", "🟩"))
                            green_chars.add(char)
                            self.discovered_letters.add(char)
                        elif char in target:
                            evaluations.append(LetterEvaluation(char, "yellow", "🟨"))
                            yellow_chars.add(char)
                            self.discovered_letters.add(char)
                        else:
                            evaluations.append(LetterEvaluation(char, "gray", "⬛"))
                            gray_chars.add(char)
                            self.eliminated_letters.add(char)
            elif len(guess_words) == 1:
                # Single word guess: find best matching target word by length/overlap
                g_word = guess_words[0]
                best_t_word = target_words[0]
                for tw in target_words:
                    if len(tw) == len(g_word):
                        best_t_word = tw
                        break
                
                for i, char in enumerate(g_word):
                    if i < len(best_t_word) and best_t_word[i] == char:
                        evaluations.append(LetterEvaluation(char, "green", "🟩"))
                        green_chars.add(char)
                        self.discovered_letters.add(char)
                    elif char in target:
                        evaluations.append(LetterEvaluation(char, "yellow", "🟨"))
                        yellow_chars.add(char)
                        self.discovered_letters.add(char)
                    else:
                        evaluations.append(LetterEvaluation(char, "gray", "⬛"))
                        gray_chars.add(char)
                        self.eliminated_letters.add(char)
            else:
                # Multiple words of different length than target
                for i, char in enumerate(cleaned.replace(" ", "")):
                    clean_target_no_space = target.replace(" ", "")
                    if i < len(clean_target_no_space) and clean_target_no_space[i] == char:
                        evaluations.append(LetterEvaluation(char, "green", "🟩"))
                        green_chars.add(char)
                        self.discovered_letters.add(char)
                    elif char in target:
                        evaluations.append(LetterEvaluation(char, "yellow", "🟨"))
                        yellow_chars.add(char)
                        self.discovered_letters.add(char)
                    else:
                        evaluations.append(LetterEvaluation(char, "gray", "⬛"))
                        gray_chars.add(char)
                        self.eliminated_letters.add(char)

        # Build clean visual line
        feedback_line = "  ".join(f"`{e.char}` {e.emoji}" for e in evaluations)

        # Build clear explanation
        expl_parts = []
        if green_chars:
            expl_parts.append(f"🟩 **Correct Spot:** {', '.join(sorted(green_chars))}")
        if yellow_chars - green_chars:
            expl_parts.append(f"🟨 **In Phrase, Wrong Spot:** {', '.join(sorted(yellow_chars - green_chars))}")
        if gray_chars:
            expl_parts.append(f"⬛ **Not in Phrase:** {', '.join(sorted(gray_chars))}")
        
        explanation = "\n".join(expl_parts) if expl_parts else "All letters evaluated."

        feedback = GuessFeedback(
            guess_text=cleaned,
            letter_evaluations=evaluations,
            feedback_line=feedback_line,
            explanation=explanation,
            is_correct=is_exact,
            revealed_board=self.get_masked_board(),
            word_lengths_info=self.get_word_lengths_info(),
            found_letters=sorted(list(self.discovered_letters)),
            eliminated_letters=sorted(list(self.eliminated_letters)),
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

# Wordle Discord Bot

Discord bot for playing the daily Wordle game.

## Status
- In integration (existing bot code being consolidated into `bots/wordle/`).

## Architecture Plan
- Daily word sync with NYT / custom wordlists
- Interactive 5-letter grid representation using Discord custom embeds or image generation
- Color coding: 🟩 Green (correct), 🟨 Yellow (present), ⬛ Gray (absent)
- Per-channel and direct message session support
- Hard mode and guess history tracking

# contexto-bot

A Discord bot that brings the [Contexto](https://contexto.me) word-guessing game to your server!

## Features
- Daily Contexto game synced with the official site
- Per-channel game sessions
- Guess ranking with emoji color feedback
- Hint system (shows your closest guess so far)
- Give up to reveal the answer
- Leaderboard tracking guesses per session

## Setup

1. **Clone / download** this repo
2. **Create a `.env` file** (copy from `.env.example`):
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```
3. **Install dependencies** (uses `uv`):
   ```bash
   uv sync
   ```
4. **Run the bot:**
   ```bash
   uv run bot.py
   ```

## Commands

| Command | Description |
|---|---|
| `/contexto start` | Start today's Contexto game in this channel |
| `/contexto guess <word>` | Guess a word and see its rank |
| `/contexto hint` | Show your closest guess so far |
| `/contexto guesses` | List all your guesses this session, sorted by rank |
| `/contexto giveup` | Reveal the answer and end the game |

## Rank Color Guide

| Emoji | Rank Range | Meaning |
|---|---|---|
| 🟩 | 1–500 | Very close! |
| 🟨 | 501–1500 | Getting warmer |
| 🟧 | 1501–3000 | Far away |
| 🟥 | 3000+ | Cold |

## Notes
- This bot uses Contexto's unofficial API for personal/educational use.
- One game session per channel at a time.

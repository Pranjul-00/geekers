# Contexto Discord Bot

Brings the [Contexto](https://contexto.me) word-guessing game to Discord.
Powered by the unofficial Contexto API (`api.contexto.me`).

## Features
- **Daily Contexto synced** with the official site (epoch: 2022-09-18)
- **Historical Games**: Play any past game by number (`/contexto start game:<num>`)
- **Per-Channel Game Sessions**: Independent state and guess history per channel
- **Auto-Guess Mode**: Players can type guesses directly without slash command invocations
- **Rank Feedback & Emojis**:
  - 🟩 `1–500`: Very close!
  - 🟨 `501–1500`: Getting warmer...
  - 🟧 `1501–3000`: Still pretty far...
  - 🟥 `3000+`: Ice cold!
- **Hints & Leaderboard**: Inspect closest guesses, history, or surrender to reveal
- **Daily Channel Subscriptions**: Automated daily announcement with subscription persistence in `subscriptions.json`

## Commands

### Slash Commands (`/contexto`)
- `/contexto start [game]` — Start today's game or a specific game number
- `/contexto guess <word>` — Guess a word and see its ranking
- `/contexto hint` — Show the closest guess made so far
- `/contexto guesses` — View all guesses sorted by closeness
- `/contexto giveup` — End the game and reveal the target word
- `/contexto today` — View info on today's game
- `/contexto subscribe` — Subscribe channel to daily announcements
- `/contexto unsubscribe` — Unsubscribe channel from daily announcements

### Prefix Commands (Default prefix: `c!`)
- `c!start [game]`
- `c!giveup`
- `c!hint`
- `c!guesses`
- `c!today`
- `c!chelp`

## Configuration
Environment variables can be placed in `bots/contexto/.env` or repository root `.env`:
```env
DISCORD_TOKEN=your_bot_token_here
# Optional per-bot overrides:
CONTEXTO_DISCORD_TOKEN=your_bot_token_here
CONTEXTO_COMMAND_PREFIX=c!
```

## Running
From project root:
```bash
uv run python -m bots.contexto.bot
# or
uv run contexto-bot
```
From inside `bots/contexto`:
```bash
python bot.py
```

# Expresso Discord Bot

A daily phrase and idiom guessing bot for Discord servers, designed for group competition, daily comparison charts, and automated streak reminders.

---

## Features

- **Daily Phrase Puzzles**: Synchronizes with a curated archive of idioms, common expressions, and contextual hints.
- **Side-by-Side Comparison Charts**:
  - `e!chart` displays daily group standings, relative guess performance, solve times, and medals (1st, 2nd, 3rd) for friends in the channel.
  - Daily superlatives: MVP (fewest guesses), Speed Demon (fastest solve time), and Decaf Struggle (perseverance award).
- **Head-to-Head Compare**:
  - `e!compare @friend` provides a comparative stat breakdown (win rate, average guesses, current streak, fastest solve) with automated commentary.
- **Automated Drops & Evening Reminders**:
  - Broadcasts new puzzles at midnight UTC to subscribed channels.
  - Sends an evening reminder 4 hours before daily reset, pinging friends who have not yet completed today's puzzle.
- **Chat Auto-Guessing**: Once a game starts, users can type single words or entire phrases directly in chat to submit guesses.
- **Dual Command Interfaces**: Supports slash commands (`/expresso start`) and prefix commands (`e!start`, configurable).
- **SQLite Persistence**: Stores player records, streaks, and channel subscription preferences locally in `expresso.db`.

---

## Command Reference

| Slash Command | Prefix Command | Description |
|---|---|---|
| `/expresso start [game]` | `e!start [game]` | Start today's puzzle or replay a past game by number |
| `/expresso chart` | `e!chart` | View the daily side-by-side group standings |
| `/expresso compare @friend` | `e!compare @friend` | Compare stats head-to-head with a friend |
| `/expresso hint` | `e!hint` | Reveal an unrevealed letter or contextual category clue |
| `/expresso giveup` | `e!giveup` | Surrender and reveal the answer |
| `/expresso subscribe` | `e!subscribe` | Subscribe channel to daily puzzle drops and reminder pings |
| `/expresso unsubscribe` | `e!unsubscribe` | Unsubscribe channel from notifications |

---

## Running Expresso

### Configuration
Set variables in `bots/expresso/.env` or repository root `.env`:
```env
DISCORD_TOKEN=your_bot_token_here
COMMAND_PREFIX=e!

# Optional overrides:
EXPRESSO_DISCORD_TOKEN=your_bot_token_here
EXPRESSO_COMMAND_PREFIX=e!
```

### Execution
From the repository root:
```bash
uv run expresso-bot
# or
uv run python -m bots.expresso.bot
```

Ensure **Message Content Intent** is enabled under the **Bot** tab in the Discord Developer Portal for chat auto-guessing.

# Expresso Discord Bot ☕

A daily phrase & idiom guessing bot for Discord servers, designed specifically for friend groups who love friendly competition!

---

## ⚡ Highlights
- **Daily Phrase Puzzles:** Syncs with daily idiom and expression puzzles.
- **Side-by-Side Comparison Charts:**
  - `e!chart` displays daily group standings with Unicode progress bars, solve times, and medals (🥇, 🥈, 🥉).
  - Daily superlatives and awards: 🏆 **Espresso Doppio (MVP)**, ⚡ **Speed Demon**, ☕ **Decaf Struggle**.
- **Head-to-Head Compare:**
  - `e!compare @friend` gives a side-by-side metric breakdown (Win Rate %, Avg Guesses, Streaks, Fastest Solve) with automated roast commentary.
- **Automated Drops & Reminders:**
  - Broadcasts new puzzles at midnight UTC.
  - Sends an evening reminder (4h before reset) pinging friends who haven't completed today's puzzle yet so their streaks don't die!
- **Chat Auto-Guessing:** Type words or phrases directly into the channel once a game begins.
- **Dual Commands:** Slash (`/expresso start`) and prefix (`e!start`, configurable).

---

## 📜 Commands

| Slash Command | Prefix Command | Description |
|---|---|---|
| `/expresso start [game]` | `e!start [game]` | Start today's puzzle or replay a past game |
| `/expresso chart` | `e!chart` | View the daily side-by-side group standings |
| `/expresso compare @friend` | `e!compare @friend` | Compare stats head-to-head with a friend |
| `/expresso hint` | `e!hint` | Reveal a letter or category clue |
| `/expresso giveup` | `e!giveup` | Surrender and reveal the answer |
| `/expresso subscribe` | `e!subscribe` | Subscribe channel to daily drops and reminder pings |
| `/expresso unsubscribe` | `e!unsubscribe` | Unsubscribe channel from notifications |

---

## 🚀 Running

### Configuration
In `.env` or `bots/expresso/.env`:
```env
DISCORD_TOKEN=your_token_here
# Or bot-specific override:
EXPRESSO_DISCORD_TOKEN=your_token_here
EXPRESSO_COMMAND_PREFIX=e!
```

### Execution
From project root:
```bash
uv run expresso-bot
# or
uv run python -m bots.expresso.bot
```

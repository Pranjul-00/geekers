# Contexto Discord Bot

Brings the [Contexto](https://contexto.me) word-guessing game to Discord. Includes both a high-performance Rust engine (using Poise and Serenity) and a Python edition (using discord.py).

---

## Features

- **Rank #0 Secret Word Handling**: Properly identifies the target word at rank #0 with an embed, summary statistics, and victory confirmation.
- **Chat Auto-Guessing**: Start a game with `c!start` or `/start`, then type single words directly into the channel to submit guesses without repeated command invocations.
- **In-Memory Cache (Rust Engine)**: Caches queried words in memory and maintains connection pooling for sub-millisecond guess resolution.
- **Daily and Historical Games**: Automatically syncs with the official daily Contexto game or allows selecting any historical game number (`c!start 500`).
- **Channel Subscriptions**: Broadcasts new daily puzzles at midnight UTC to subscribed Discord channels.
- **Dual Command Interfaces**: Full parity between slash commands (`/start`, `/hint`, `/guess`) and prefix commands (`c!start`, `c!hint`, `c!guess`).

---

## Rank Proximity Guide

| Rank Range | Proximity Category | Feedback Meaning |
|:---:|:---:|---|
| **#0** | Winner | Secret word identified |
| **1 - 500** | Top Tier | Very close |
| **501 - 1,500** | Warm Tier | Getting warmer |
| **1,501 - 3,000** | Far Tier | Still pretty far |
| **3,000+** | Cold Tier | Cold |

---

## Command Reference

Commands are available via slash commands (`/start`, `/contexto start`) or message prefixes (default `c!`):

| Prefix Command | Aliases | Description |
|---|---|---|
| `c!start [game]` | `c!play`, `c!begin` | Start today's puzzle or load a past game by number |
| `c!guess <word>` | — | Explicitly submit a word guess (or type directly in chat) |
| `c!hint` | — | Display the closest guess made so far in this session |
| `c!guesses` | `c!list`, `c!history` | Display top guesses sorted by proximity rank |
| `c!giveup` | `c!quit` | End the current session and reveal the secret word |
| `c!today` | — | Check today's game number and current channel session status |
| `c!subscribe` | — | Subscribe the current channel to automated daily puzzle drops |
| `c!unsubscribe` | — | Unsubscribe the channel from daily announcements |
| `c!chelp` | `c!help`, `c!commands` | Show help menu and proximity guide |

---

## Running Contexto

### Option A: Rust Engine (Recommended)
Prerequisites: Rust toolchain (`cargo` / `rustup`).

From the repository root:
```bash
cargo run --package contexto-bot --release
```

Or from `bots/contexto`:
```bash
cargo run --release
```

### Option B: Python Edition
Prerequisites: Python 3.11+ and `uv`.

From the repository root:
```bash
uv run contexto-bot
# or
uv run python -m bots.contexto.bot
```

### Configuration
Set variables in `bots/contexto/.env` or repository root `.env`:
```env
DISCORD_TOKEN=your_bot_token_here
COMMAND_PREFIX=c!

# Optional overrides:
CONTEXTO_DISCORD_TOKEN=your_bot_token_here
CONTEXTO_COMMAND_PREFIX=c!
```

Ensure **Message Content Intent** is enabled under the **Bot** tab in the Discord Developer Portal so the bot can read words in chat for auto-guessing.

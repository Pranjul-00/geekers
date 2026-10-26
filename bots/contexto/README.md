# Contexto Discord Bot 🦀 / 🐍

Brings the [Contexto](https://contexto.me) word-guessing game to Discord.
Features a high-performance **Rust engine** (poise/serenity) alongside the **Python/uv** edition.

---

## ⚡ Highlights
- **🏆 Winning Embed:** Correctly identifies the secret word at rank `#0` with a celebratory gold embed, stats, and victory message.
- **💡 Chat Auto-Guessing:** Start a game with `c!start` or `/start`, then simply type your word guesses directly in chat! No command syntax required.
- **⚡ Blazing Fast Engine (Rust):** In-memory word cache and keep-alive HTTP connection pooling for sub-millisecond guess responses.
- **🔁 24h Daily Puzzles & Historical Games:** Syncs with the official Contexto daily game or lets you replay any past game number (`c!start 500`).
- **🔔 Channel Subscriptions:** Automatically broadcasts new puzzles at midnight UTC to subscribed channels.
- **🎯 Dual Command System:** Full support for both modern Slash commands (`/start`, `/hint`) and Prefix commands (`c!start`, `c!giveup`, configurable via `.env`).

---

## 🎮 Rank Color Guide

| Emoji | Rank Range | Meaning |
|:---:|:---:|---|
| 🏆 | **#0** | **Secret Word Found (Winner!)** |
| 🟩 | **1 – 500** | Very close! |
| 🟨 | **501 – 1,500** | Getting warmer... |
| 🟧 | **1,501 – 3,000** | Still pretty far... |
| 🟥 | **3,000+** | Ice cold! |

---

## 📜 Commands

Commands work as both **Slash commands** (e.g. `/start` or `/contexto start`) and **Prefix commands** (e.g. `c!start`):

| Command | Aliases | Description |
|---|---|---|
| `c!start [game]` | `c!play`, `c!begin` | Start today's puzzle or pick a past game number |
| `c!guess <word>` | — | Guess a word manually (or just type the word!) |
| `c!hint` | — | Reveal your closest guess so far |
| `c!guesses` | `c!list`, `c!history` | Show top guesses sorted by closeness |
| `c!giveup` | `c!quit` | End the current game and reveal the answer |
| `c!today` | — | Check today's game number and channel status |
| `c!subscribe` | — | Subscribe the channel to automatic 24h puzzle drops |
| `c!unsubscribe` | — | Stop automatic daily announcements |
| `c!chelp` | `c!help`, `c!commands` | Show help and color guide |

---

## 🚀 Setup & Running

### Option A: Rust Engine (Recommended for Performance)
Requires Rust toolchain (`rustup` / `cargo`).
```bash
# From workspace root:
cargo run --package contexto-bot

# Or inside bots/contexto:
cargo run --release
```

### Option B: Python Edition
Requires Python 3.11+ and `uv`.
```bash
# From workspace root:
uv run python -m bots.contexto.bot
# or
uv run contexto-bot
```

### Configuration
Set environment variables in `.env` (or `bots/contexto/.env`):
```env
DISCORD_TOKEN=your_bot_token_here
COMMAND_PREFIX=c!
# Optional override:
CONTEXTO_DISCORD_TOKEN=your_bot_token_here
CONTEXTO_COMMAND_PREFIX=c!
```
> **Note:** Ensure **Message Content Intent** is enabled under the **Bot** tab in the Discord Developer Portal so the bot can read words in chat for auto-guessing!

# Contexto Discord Bot (High-Performance Rust Engine) 🦀

A blazing fast Discord bot that brings the [Contexto](https://contexto.me) word-guessing game to your server!

Engineered in **Rust** using `serenity` and `poise` with keep-alive HTTP connection pooling and sub-millisecond in-memory word caching.

---

## ⚡ Highlights

- **🏆 Proper Winning Embed:** Correctly identifies secret word at rank `#0` with celebratory gold embed, stats, and victory message.
- **💡 Chat Auto-Guessing:** Start a game with `c!start` or `/start`, and then **simply type your word guesses directly in chat!** No commands needed.
- **⚡ Blazing Fast:** Built with an in-memory word cache and connection pooling so repeat guesses return instantly (0ms network roundtrip) and new guesses resolve in milliseconds.
- **🔁 24h Daily Puzzles & Historical Games:** Syncs with the official Contexto daily game or lets you play any past game number (`c!start 500`).
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

Commands work as both **Slash commands** (e.g. `/start`) and **Prefix commands** (e.g. `c!start`):

| Command | Aliases | Description |
|---|---|---|
| `c!start [game]` | `c!play`, `c!begin` | Start today's puzzle or pick a past game number |
| `c!guess <word>` | — | Guess a word manually (or just type the word!) |
| `c!hint` | — | Reveal your closest guess so far |
| `c!guesses` | `c!list`, `c!history` | Show top 25 guesses sorted by closeness |
| `c!giveup` | `c!quit` | End the current game and reveal your best guess |
| `c!today` | — | Check today's game number and channel status |
| `c!subscribe` | — | Subscribe the channel to automatic 24h puzzle drops |
| `c!unsubscribe` | — | Stop automatic daily announcements |
| `c!chelp` | `c!help`, `c!commands` | Show help and color guide |

---

## 🚀 Setup & Running

### 1. Requirements
- Rust toolchain (`rustup` / `cargo`)

### 2. Configure `.env`
Create `.env` based on `.env.example`:
```bash
DISCORD_TOKEN=your_bot_token_here
COMMAND_PREFIX=c!
```

> **Note:** Make sure **Message Content Intent** is enabled under the **Bot** tab in the [Discord Developer Portal](https://discord.com/developers/applications) so the bot can read words in chat for auto-guessing!

### 3. Build & Run
```bash
# Debug run:
cargo run

# Optimized production build:
cargo run --release
```

# Geekers

A modular monorepo for Discord bots bringing popular daily web games directly into Discord servers.

---

## Overview

The Geekers repository hosts a collection of independent Discord bots designed for cooperative and competitive daily puzzle games. Each bot operates as an isolated package with its own command set, runtime configuration, and persistence layer, while sharing common infrastructure, environment management, and workspace tooling.

### Available and Planned Bots

| Game / Bot | Directory | Runtime | Description | Status |
|---|---|---|---|---|
| **Contexto** | `bots/contexto/` | Rust (poise/serenity) + Python (discord.py) | Semantic distance word guessing game based on Contexto.me. | Active |
| **Expresso** | `bots/expresso/` | Python (discord.py) | Daily idiom and phrase deduction with group standings and reminders. | Active |
| **Wordle** | `bots/wordle/` | Python (discord.py) | Classic 5-letter word puzzle with per-user and per-channel sessions. | Integration |
| **Conexo** | `bots/conexo/` | Python (discord.py) | 4x4 grouping deduction game based on Conexo.ws. | Planned |
| **Letresso** | `bots/letresso/` | Python (discord.py) | Daily letter placement and word construction game. | Planned |

---

## Repository Architecture

```
geekers/
├── .agents/                    # Tooling rules and workflows
│   ├── rules/
│   └── workflows/
├── .context/                   # Project memory matrix (architecture, tasks, decisions)
├── bots/                       # Isolated bot applications
│   ├── contexto/               # Contexto bot (Rust high-performance engine & Python edition)
│   │   ├── Cargo.toml
│   │   ├── src/main.rs
│   │   ├── bot.py
│   │   ├── README.md
│   │   └── .env.example
│   ├── expresso/               # Expresso bot (daily phrases, comparison charts, reminders)
│   │   ├── bot.py
│   │   ├── game.py
│   │   ├── charts.py
│   │   ├── reminders.py
│   │   ├── storage.py
│   │   ├── phrases.json
│   │   ├── README.md
│   │   └── .env.example
│   ├── conexo/                 # Conexo bot specifications and assets
│   ├── letresso/               # Letresso bot specifications and assets
│   └── wordle/                 # Wordle bot specifications and assets
├── shared/                     # Shared utilities (configuration, formatting, HTTP helpers)
│   ├── __init__.py
│   └── config.py
├── Cargo.toml                  # Root Cargo workspace manifest
├── pyproject.toml              # Monorepo Python dependencies and CLI entrypoints
├── uv.lock                     # Python dependency lockfile
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python**: Version 3.11 or newer. We recommend using [`uv`](https://docs.astral.sh/uv/) for deterministic dependency management.
- **Rust Toolchain**: `cargo` and `rustup` (required for running the Rust edition of Contexto).

### Environment Configuration

1. Copy the example environment template:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and set your Discord bot credentials:
   ```env
   # Unified Discord Bot Token (used by default across all bots)
   DISCORD_TOKEN=your_discord_bot_token_here

   # Optional per-bot overrides
   CONTEXTO_DISCORD_TOKEN=your_contexto_token
   EXPRESSO_DISCORD_TOKEN=your_expresso_token

   # Optional command prefix overrides
   CONTEXTO_COMMAND_PREFIX=c!
   EXPRESSO_COMMAND_PREFIX=e!
   ```

3. Ensure **Message Content Intent** is enabled under the **Bot** tab in the [Discord Developer Portal](https://discord.com/developers/applications) for chat auto-guessing functionality.

### Installing Dependencies

#### Python (using uv):
```bash
uv sync
```

#### Python (using standard pip):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Running the Bots

### 1. Unified Geekers Bot (Recommended)

Run all bots together under a single process with the unified `/geekers` dropdown menu and slash command suite:

```bash
uv run geekers
```

Once online in your Discord server:
- Type `/geekers` (or `g!menu`) to open the interactive dropdown game hub.
- Select **Expresso** or **Contexto** to view your personalized daily stats.
- Click **Start Game** to launch the puzzle directly in the channel.
- Auto-guess is active: simply type words in chat once any game has started!

---

### 2. Standalone Bot Execution

If you prefer to run individual bots independently:

#### Contexto Bot

- **Rust Engine (High Performance):**
  ```bash
  cargo run --package contexto-bot --release
  ```
- **Python Edition:**
  ```bash
  uv run contexto-bot
  ```

#### Expresso Bot

```bash
uv run expresso-bot
```

For complete command lists and rules, see [`bots/expresso/README.md`](bots/expresso/README.md).

---

## Development & Contribution Guidelines

- **Branch Strategy**: Active feature branches should be based off `main`.
- **Bot Isolation**: Keep bot-specific business logic, storage files, and assets inside `bots/<game_name>/`.
- **Shared Code**: Code reused across two or more bots belongs in `shared/`.
- **State Persistence**: Avoid committing runtime data files (`subscriptions.json`, `*.db`). These are covered by `.gitignore`.
- **Verification**: Run `uv sync` and compile checks before submitting changes.

# Geekers

A monorepo for Discord bots bringing our favorite daily web games directly to Discord servers!

## Games & Bots

| Bot / Game | Directory | Engine / Language | Description & Source | Status |
|---|---|---|---|---|
| **Contexto** | [`bots/contexto`](bots/contexto/) | Rust (poise/serenity) + Python (discord.py) | Word proximity / semantic distance guessing game ([contexto.me](https://contexto.me)) | 🟢 Live / Ready |
| **Expresso** | [`bots/expresso`](bots/expresso/) | Python (discord.py) | Fast-paced daily word puzzle & group comparison charts | 🟡 In Development |
| **Wordle** | [`bots/wordle`](bots/wordle/) | Python (discord.py) | Classic 5-letter word puzzle | 🟡 In Integration |
| **Conexo** | [`bots/conexo`](bots/conexo/) | Python (discord.py) | 4x4 group puzzle ([conexo.ws](https://conexo.ws)) | 🟡 Planned |
| **Letresso** | [`bots/letresso`](bots/letresso/) | Python (discord.py) | Daily letter placement and word creation game | 🟡 Planned |

---

## Directory Structure

```
geekers/
├── .context/               # Autonomous Project Architect memory matrix
├── bots/                   # Individual game bots
│   ├── contexto/           # Contexto Discord bot (Rust & Python engines)
│   │   ├── Cargo.toml
│   │   ├── src/main.rs
│   │   ├── bot.py
│   │   ├── README.md
│   │   └── .env.example
│   ├── expresso/           # Expresso Discord bot
│   │   ├── README.md
│   │   └── ...
│   ├── conexo/             # Conexo bot (planned)
│   ├── letresso/           # Letresso bot (planned)
│   └── wordle/             # Wordle bot (in integration)
├── shared/                 # Common helpers, config loaders, and Discord UI modules
├── Cargo.toml              # Root Rust workspace
├── pyproject.toml          # Monorepo Python dependencies & entrypoints
├── uv.lock
└── README.md
```

---

## Getting Started

### 1. Requirements
- Python 3.11+ with [`uv`](https://docs.astral.sh/uv/)
- Rust toolchain (`cargo` / `rustup`) for Rust engines

### 2. Configure Environment
```bash
git clone https://github.com/Pranjul-00/geekers.git
cd geekers

cp .env.example .env
```
Fill in your `DISCORD_TOKEN` in `.env`.

### 3. Running Bots

#### Contexto Bot
- **Rust Engine:**
  ```bash
  cargo run --package contexto-bot
  # Or with release optimizations:
  cargo run --package contexto-bot --release
  ```
- **Python Edition:**
  ```bash
  uv run contexto-bot
  # or
  uv run python -m bots.contexto.bot
  ```

#### Expresso Bot
```bash
uv run expresso-bot
# or
uv run python -m bots.expresso.bot
```

See individual bot directories in `bots/` for gameplay rules, commands, and options.

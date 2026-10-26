# Geekers

A monorepo for Discord bots bringing our favorite daily web games directly to Discord servers!

## Games & Bots

| Bot / Game | Directory | Description & Source | Status |
|---|---|---|---|
| **Contexto** | [`bots/contexto`](bots/contexto/) | Word proximity / semantic distance guessing game ([contexto.me](https://contexto.me)) | 🟢 Live / Ready |
| **Wordle** | [`bots/wordle`](bots/wordle/) | Classic 5-letter word puzzle | 🟡 In Integration |
| **Conexo** | [`bots/conexo`](bots/conexo/) | 4x4 group puzzle ([conexo.ws](https://conexo.ws)) | 🟡 Planned |
| **Letresso** | [`bots/letresso`](bots/letresso/) | Daily letter placement and word creation game | 🟡 Planned |
| **Expresso** | [`bots/expresso`](bots/expresso/) | Fast-paced daily word puzzle | 🟡 Planned |

---

## Directory Structure

```
geekers/
├── .context/               # Autonomous Project Architect memory matrix
├── bots/                   # Individual game bots
│   ├── contexto/           # Contexto Discord bot
│   │   ├── bot.py
│   │   ├── README.md
│   │   └── .env.example
│   ├── conexo/             # Conexo bot (planned)
│   ├── letresso/           # Letresso bot (planned)
│   ├── expresso/           # Expresso bot (planned)
│   └── wordle/             # Wordle bot (in integration)
├── shared/                 # Common helpers, config loaders, and Discord UI modules
├── pyproject.toml          # Monorepo dependencies & entrypoints
├── uv.lock
└── README.md
```

---

## Getting Started

### 1. Requirements
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`

### 2. Setup Environment
```bash
git clone https://github.com/Pranjul-00/geekers.git
cd geekers

# Create root or bot-specific .env
cp .env.example .env
```
Fill in your `DISCORD_TOKEN` in `.env`.

### 3. Install Dependencies
```bash
uv sync
```

### 4. Running a Bot

#### Contexto Bot:
```bash
# Using CLI script entrypoint
uv run contexto-bot

# Or via Python module
uv run python -m bots.contexto.bot
```

See [`bots/contexto/README.md`](bots/contexto/README.md) for full commands list and configuration details.

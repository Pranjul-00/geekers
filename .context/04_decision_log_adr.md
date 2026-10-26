# Architectural Decision Records (ADR Log)

## ADR 0001: Monorepo Restructuring for Multi-Bot Scalability
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: The repository originally contained a single `bot.py` at root implementing the Contexto bot. The project vision is to host bots for multiple daily web games (`contexto.me`, `conexo.ws`, `letresso`, `expresso`, `wordle`, and future additions) within this repository.
- **Decision**: Restructure into a modular monorepo under `bots/<game_name>/` with a `shared/` package for common code, while keeping root `pyproject.toml` managing shared dependencies and console script entrypoints.
- **Consequences**: Enables parallel bot development, prevents codebase clutter, keeps each bot's docs and assets self-contained, and preserves clean imports.

## ADR 0002: Hierarchical Environment Configuration
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: Different developers or host environments may run bots using either a single Discord bot application or individual bot applications per game with separate tokens and command prefixes.
- **Decision**: Implement a two-tier configuration lookup:
  1. Check bot-specific variables (e.g. `CONTEXTO_DISCORD_TOKEN`, `bots/contexto/.env`).
  2. Fall back to global repository environment (e.g. `DISCORD_TOKEN`, root `.env`).
- **Consequences**: Maximizes flexibility without breaking existing single-token setups.

## ADR 0003: Bot-Scoped Subscriptions and State Persistence
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: Contexto saves channel subscription IDs to `subscriptions.json`. If stored in root, running multiple bots could cause collisions or clutter.
- **Decision**: Scope persistent runtime files to `BASE_DIR = Path(__file__).resolve().parent`, saving `subscriptions.json` directly inside `bots/contexto/`.
- **Consequences**: Complete state isolation between bots; `.gitignore` ignores `bots/**/subscriptions.json`.


## ADR 0004: Polyglot Monorepo Workspace (Rust & Python) and Expresso Bot Architecture
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: Upstream introduced a high-performance Rust engine for Contexto (`serenity` + `poise`). Concurrently, Bot 2 (Expresso) is implemented in Python for fast feature iteration, chart generation, and reminder scheduling for a 5-6 player friend group.
- **Decision**: 
  1. Organize upstream Rust files inside `bots/contexto/` with a root `Cargo.toml` workspace declaring `members = ["bots/contexto"]`. This allows `cargo run --package contexto-bot` from repo root while keeping the root clean.
  2. Implement Expresso Bot (`bots/expresso/`) using `discord.py` with modular separation:
     - `game.py`: Wordle-style phrase feedback and daily puzzle calculations.
     - `storage.py`: SQLite persistence for results, streaks, and reminder configs.
     - `charts.py`: Unicode side-by-side group standings and head-to-head friend comparisons.
     - `reminders.py`: Automated midnight drop notifications and evening nudge reminders.
- **Consequences**: Both Rust and Python toolchains function seamlessly. Expresso bot is production-ready for friend-group competition.

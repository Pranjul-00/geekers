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

# Project Manifest & Mission Objectives

## Core Mission
To build and maintain a modular, scalable monorepo of Discord bots that bring popular daily web games directly to Discord communities. Supported and planned games include:
- **Contexto** (`contexto.me`): Semantic word proximity guessing game.
- **Wordle**: Daily 5-letter word puzzle.
- **Conexo** (`conexo.ws`): 4x4 group puzzle (find 4 groups of 4 words).
- **Letresso**: Daily letter arrangement & word construction challenge.
- **Expresso**: Fast-paced daily word / connection challenge.
- Additional future daily games.

## Acceptance Criteria & KPIs
- [x] Clear monorepo folder structure with each game bot residing in `bots/<game>/`.
- [x] Contexto bot cleanly relocated from root to `bots/contexto/` without loss of functionality.
- [x] Multi-tier configuration support: Root `.env` fallback + bot-specific local `.env` overrides.
- [x] Safe Discord interaction handling (deferrals, 10062 expired interaction guardrails).
- [ ] Wordle bot integration into `bots/wordle/`.
- [ ] Conexo bot implementation in `bots/conexo/`.
- [ ] Letresso bot implementation in `bots/letresso/`.
- [ ] Expresso bot implementation in `bots/expresso/`.
- [ ] Centralized shared library in `shared/` for rate limits, common Discord UI elements, and API wrappers.

## Non-Negotiable Domain Rules
1. **Isolated Channel State**: Game sessions must be keyed strictly by channel ID to prevent cross-channel / cross-server state bleed.
2. **Spoiler Protection**: Never reveal answers in public responses unless explicitly triggered by give-up commands (`/giveup` or `c!giveup`) or game termination.
3. **Resilient Network I/O**: All external game API requests (e.g. `api.contexto.me`) must use timeouts, session reuse via `aiohttp.ClientSession`, and graceful error messaging on failure.
4. **Independent Executability**: Every bot must be runnable independently via `uv run python -m bots.<game>.bot` or root CLI entrypoints.

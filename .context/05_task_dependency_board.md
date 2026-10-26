# Unified Task Matrix

## Epics & Subtasks

### Epic 1: Repository Architecture & Context Matrix (Completed)
- [x] Fork `woeter69/geekers` to `Pranjul-00/geekers` and clone to `/home/pranjul/bruh/geekers`.
- [x] Configure git remotes (`origin` -> fork, `upstream` -> original repo).
- [x] Restructure root into modular `bots/` and `shared/` directories.
- [x] Move `bot.py` into `bots/contexto/` with updated path resolution and entrypoint `main()`.
- [x] Add READMEs and initializers for `wordle`, `conexo`, `letresso`, `expresso`.
- [x] Set up `.context/` memory matrix scoped strictly to `geekers`.
- [x] Set up and run Graphify on `geekers` codebase.

### Epic 2: Wordle Bot Migration & Integration
- [ ] Migrate existing Wordle bot source files into `bots/wordle/`.
- [ ] Align configuration to use `shared.config` and `WORDLE_DISCORD_TOKEN`.
- [ ] Test channel-isolated gameplay sessions and output formatting.
- [ ] Register CLI script entrypoint in `pyproject.toml`.

### Epic 3: Conexo Bot Implementation (`conexo.ws`)
- [ ] Analyze `conexo.ws` daily payload / API structure or puzzle scraper.
- [ ] Implement game engine logic for 4x4 word grid and mistake tracking.
- [ ] Build Discord interactive view using Buttons/Select components for word selection.
- [ ] Add `/conexo` slash and prefix command suite.

### Epic 4: Letresso & Expresso Bots Implementation
- [ ] Implement Letresso daily puzzle scraper and submission engine.
- [ ] Implement Expresso timer-based puzzle mechanics.
- [ ] Integrate channel leaderboards.

### Epic 5: Shared Infrastructure & Multi-Bot Runner
- [ ] Implement shared Discord error handler in `shared/discord_utils.py`.
- [ ] Implement rate limiting and exponential backoff utility in `shared/http.py`.
- [ ] Optional: Create a multi-bot unified launcher (`all_bots.py` or Discord cogs runner).

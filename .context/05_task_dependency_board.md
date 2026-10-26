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

### Epic 2: Upstream Integration & Branch Management (Completed)
- [x] Fetch `upstream` updates (commit `fcfd67c` - Rust Contexto engine rewrite).
- [x] Create branch `main` on both `Pranjul-00/geekers` (origin) and `woeter69/geekers` (upstream).
- [x] Resolve merge conflicts cleanly:
  - Preserved multi-bot monorepo layout.
  - Relocated upstream Rust `Cargo.toml` and `src/main.rs` into `bots/contexto/`.
  - Configured root `Cargo.toml` workspace referencing `"bots/contexto"`.
  - Kept Python Contexto bot alongside Rust engine.
  - Reconciled `.gitignore` and `README.md`.
- [ ] PR and merge to upstream `master` (on hold until user approves).

### Epic 3: Expresso Bot Implementation (Completed)
- [x] Create daily phrases catalog (`bots/expresso/phrases.json`).
- [x] Implement phrase guessing game engine (`bots/expresso/game.py`) with Wordle-style feedback.
- [x] Implement SQLite persistence for scores, streaks, and subscriptions (`bots/expresso/storage.py`).
- [x] Build side-by-side comparison charts & head-to-head friend stats (`bots/expresso/charts.py`).
- [x] Build automated daily midnight drop and evening reminder scheduler (`bots/expresso/reminders.py`).
- [x] Implement dual command router (Slash `/expresso` + Prefix `e!`) and auto-guess in `bots/expresso/bot.py`.
- [x] Register `expresso-bot` CLI entrypoint in `pyproject.toml` and verify `uv sync`.

### Epic 4: Wordle Bot Migration & Integration
- [ ] Migrate existing Wordle bot source files into `bots/wordle/`.
- [ ] Align configuration to use `shared.config` and `WORDLE_DISCORD_TOKEN`.
- [ ] Test channel-isolated gameplay sessions and output formatting.
- [ ] Register CLI script entrypoint in `pyproject.toml`.

### Epic 5: Conexo Bot Implementation (`conexo.ws`)
- [ ] Analyze `conexo.ws` daily payload / API structure or puzzle scraper.
- [ ] Implement game engine logic for 4x4 word grid and mistake tracking.
- [ ] Build Discord interactive view using Buttons/Select components for word selection.
- [ ] Add `/conexo` slash and prefix command suite.

### Epic 6: Letresso Bot Implementation
- [ ] Implement Letresso daily puzzle scraper and submission engine.
- [ ] Implement interactive Discord letter-tile interface.
- [ ] Channel leaderboards and streak tracking.

### Epic 7: Shared Infrastructure & Multi-Bot Runner
- [ ] Implement shared Discord error handler in `shared/discord_utils.py`.
- [ ] Implement rate limiting and exponential backoff utility in `shared/http.py`.
- [ ] Optional: Create a multi-bot unified launcher (`all_bots.py` or Discord cogs runner).

# Repository Map

## Living Repository Map

```
geekers/
├── .agents/
│   ├── rules/
│   │   └── graphify.md                 # Antigravity rule for Graphify knowledge graph lookups
│   └── workflows/
│       └── graphify.md                 # Antigravity workflow for Graphify updates & queries
├── .context/                           # Autonomous Project Architect living memory matrix
│   ├── 00_project_manifest.md          # Core goals, scope, domain rules, and KPIs
│   ├── 01_architecture_contracts.md    # Component boundaries, contracts, and data flows
│   ├── 02_tech_stack_and_env.md        # Runtimes, package management, and .env schemas
│   ├── 03_repository_map.md            # Living directory and module map
│   ├── 04_decision_log_adr.md          # Architectural Decision Records
│   ├── 05_task_dependency_board.md     # Epics, subtasks, and roadmap matrix
│   ├── 06_error_and_edge_case_log.md   # Bug ledger and edge-case handling rules
│   └── 07_session_handoff.md           # Snapshot of session state and immediate next actions
├── bots/                               # Multi-bot application root
│   ├── __init__.py                     # Root package definition for bots
│   ├── contexto/                       # Contexto Discord bot package (Rust & Python)
│   │   ├── __init__.py                 # Exports bot instance and main() runner
│   │   ├── Cargo.toml                  # Rust package manifest (poise/serenity engine)
│   │   ├── src/main.rs                 # Rust high-performance engine implementation
│   │   ├── bot.py                      # Python Contexto bot implementation
│   │   ├── README.md                   # Bot documentation, command reference, and usage
│   │   └── .env.example                # Example environment file for Contexto bot
│   ├── expresso/                       # Expresso Discord bot package
│   │   ├── __init__.py                 # Exports bot and main()
│   │   ├── bot.py                      # Discord bot command router, slash groups, auto-guess
│   │   ├── game.py                     # Daily puzzle engine, date sync, Wordle-style feedback
│   │   ├── storage.py                  # SQLite persistence (results, player stats, subscriptions)
│   │   ├── charts.py                   # Side-by-side group standings & head-to-head compare
│   │   ├── reminders.py                # Automated midnight drop and evening nudge scheduler
│   │   ├── phrases.json                # Archive of phrases, categories, and hints
│   │   └── README.md                   # Expresso bot guide & command manual
│   ├── conexo/                         # Conexo.ws daily 4x4 grouping bot (planned)
│   │   ├── __init__.py                 # Package initializer
│   │   └── README.md                   # Architecture plan and rules for Conexo bot
│   ├── letresso/                       # Letresso daily word puzzle bot (planned)
│   │   ├── __init__.py                 # Package initializer
│   │   └── README.md                   # Architecture plan and rules for Letresso bot
│   └── wordle/                         # Wordle daily 5-letter word bot (in integration)
│       ├── __init__.py                 # Package initializer
│       └── README.md                   # Architecture plan and integration steps for Wordle bot
├── shared/                             # Cross-bot utilities and shared components
│   ├── __init__.py                     # Shared package initializer
│   ├── config.py                       # Hierarchical environment loader (bot-local -> root)
│   └── hub.py                          # Unified /geekers dropdown menu & personalized game hub
├── geekers.py                          # Unified bot runner executing all daily games under one process
├── Cargo.toml                          # Root Rust Cargo workspace
├── pyproject.toml                      # Monorepo Python dependencies, build-system, and scripts
├── .env.example                        # Template for repository-wide and per-bot environment variables
├── .gitignore                          # Git ignore rules for virtual environments, .env, and state
├── README.md                           # Repository overview, architecture, and setup instructions
└── uv.lock                             # Locked dependency graph for reproducible installs
```

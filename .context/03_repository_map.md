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
│   ├── contexto/                       # Contexto Discord bot package
│   │   ├── __init__.py                 # Exports bot instance and main() runner
│   │   ├── bot.py                      # Core Contexto bot logic, session tracking, and handlers
│   │   ├── README.md                   # Bot documentation, command reference, and usage
│   │   └── .env.example                # Example environment file for Contexto bot
│   ├── conexo/                         # Conexo.ws daily 4x4 grouping bot (planned)
│   │   ├── __init__.py                 # Package initializer
│   │   └── README.md                   # Architecture plan and rules for Conexo bot
│   ├── letresso/                       # Letresso daily word puzzle bot (planned)
│   │   ├── __init__.py                 # Package initializer
│   │   └── README.md                   # Architecture plan and rules for Letresso bot
│   ├── expresso/                       # Expresso daily speed word puzzle bot (planned)
│   │   ├── __init__.py                 # Package initializer
│   │   └── README.md                   # Architecture plan and rules for Expresso bot
│   └── wordle/                         # Wordle daily 5-letter word bot (in integration)
│       ├── __init__.py                 # Package initializer
│       └── README.md                   # Architecture plan and integration steps for Wordle bot
├── shared/                             # Cross-bot utilities and shared components
│   ├── __init__.py                     # Shared package initializer
│   └── config.py                       # Hierarchical environment loader (bot-local -> root)
├── .env.example                        # Template for repository-wide and per-bot environment variables
├── .gitignore                          # Git ignore rules for virtual environments, .env, and state
├── pyproject.toml                      # Monorepo project specification, dependencies, and CLI scripts
├── README.md                           # Repository overview, architecture, and setup instructions
└── uv.lock                             # Locked dependency graph for reproducible installs
```

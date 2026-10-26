# Architecture Contracts & System Diagrams

## Component Boundaries
The `geekers` repository follows a modular monorepo pattern:

1. **Bot Applications (`bots/<game_name>/`)**:
   - Each bot owns its Discord command handlers, event listeners (`on_message`, `on_interaction`), local persistent state (e.g. `subscriptions.json`), and game session cache.
   - Entry point: `bot.py` with standard `main()` function.

2. **Shared Modules (`shared/`)**:
   - `shared/config.py`: Environment loader resolving both bot-local and root `.env` files.
   - Future UI / View helpers: Standardized embed styling, button grids for games like Conexo and Wordle.

3. **External Game Integrations**:
   - Unofficial or public REST APIs / scrapers providing daily game numbers, words, and proximity / validation endpoints.

## Data Flow Pipeline

```mermaid
flowchart TD
    User([Discord User / Channel]) -->|Slash Command or Prefix / Message| DiscordGW[Discord Gateway]
    DiscordGW --> BotHandler[Bot Command Handler bots/<game>/bot.py]
    
    subgraph Bot Session Runtime
        BotHandler --> SessionManager[GameSession Manager (Channel Keyed)]
        BotHandler --> SubManager[Channel Subscription Store]
    end
    
    SessionManager -->|Fetch Distance / Rank / Solution| GameAPI[Game External API / Engine]
    SubManager -->|Persist Subscriptions| JSONStore[subscriptions.json]
    
    GameAPI -->|Rank / Validation Result| BotHandler
    BotHandler -->|Formatted Discord Embed| User
```

## Contracts & Invariants
- **Session Lifecycle**: A channel can only have 1 active game session at a time.
- **Prefix & Slash Parity**: All critical gameplay actions (start, guess, hint, giveup, today) must be exposed via both slash commands (`app_commands`) and message prefix commands.
- **Auto-Guess Sniffing**: If auto-guess is enabled for a channel game (e.g. Contexto single-word detection), `message_content` intent must be enabled and ignore bot messages / prefixed commands.

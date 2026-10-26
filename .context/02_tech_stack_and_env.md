# Tech Stack & Runtime Environment

## Runtimes & Dependencies
- **Language**: Python >= 3.11 (tested with Python 3.11 - 3.13)
- **Discord Framework**: `discord.py >= 2.3.0` (utilizing `discord.ext.commands`, `discord.app_commands`, and `discord.ext.tasks`)
- **HTTP Client**: `aiohttp >= 3.10.0` (asynchronous client sessions)
- **Environment Management**: `python-dotenv >= 1.0.0`
- **Build / Packaging Tool**: `uv` with `uv_build` backend (`pyproject.toml`)

## Environment Variables (.env Schema)

### Root / Shared `.env`:
- `DISCORD_TOKEN` *(required if bot-specific token missing)*: Global Discord bot application token.
- `COMMAND_PREFIX` *(optional, default `c!`)*: Global default prefix.

### Bot-Specific Overrides (in `bots/<game>/.env` or root):
| Variable | Bot Target | Default | Description |
|---|---|---|---|
| `CONTEXTO_DISCORD_TOKEN` | Contexto | Fallback to `DISCORD_TOKEN` | Discord bot token for Contexto bot |
| `CONTEXTO_COMMAND_PREFIX`| Contexto | `c!` | Prefix for Contexto text commands |
| `WORDLE_DISCORD_TOKEN`   | Wordle   | Fallback to `DISCORD_TOKEN` | Discord bot token for Wordle bot |
| `WORDLE_COMMAND_PREFIX`  | Wordle   | `w!` | Prefix for Wordle text commands |
| `CONEXO_DISCORD_TOKEN`   | Conexo   | Fallback to `DISCORD_TOKEN` | Discord bot token for Conexo bot |
| `CONEXO_COMMAND_PREFIX`  | Conexo   | `x!` | Prefix for Conexo text commands |
| `LETRESSO_DISCORD_TOKEN` | Letresso | Fallback to `DISCORD_TOKEN` | Discord bot token for Letresso bot |
| `EXPRESSO_DISCORD_TOKEN` | Expresso | Fallback to `DISCORD_TOKEN` | Discord bot token for Expresso bot |

## Execution Commands
```bash
# Sync environment
uv sync

# Run individual bots
uv run python -m bots.contexto.bot
# or
uv run contexto-bot
```

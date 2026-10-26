import os
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_environment(bot_name: str | None = None) -> None:
    """Load environment variables with fallback from bot-specific dir to root."""
    if bot_name:
        bot_env = REPO_ROOT / "bots" / bot_name / ".env"
        if bot_env.exists():
            load_dotenv(bot_env)
    root_env = REPO_ROOT / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    load_dotenv()

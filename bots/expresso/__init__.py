"""Expresso Discord Bot package."""

def __getattr__(name: str):
    if name in ("bot", "main"):
        from .bot import bot, main
        return bot if name == "bot" else main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["bot", "main"]

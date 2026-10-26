"""
Contexto Discord Bot
--------------------
Brings the Contexto word-guessing game to Discord.
Uses the unofficial Contexto API at api.contexto.me.

Features:
  - Daily game auto-announced every 24h in subscribed channels
  - Play today's game OR any historical game by number
  - Per-channel game sessions with full guess tracking

Usage:
    uv run bot.py
"""

import os
import json
import asyncio
import logging
from datetime import date, datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config & Logging
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
# Load environment from bot directory first, then root / current working dir
load_dotenv(BASE_DIR / ".env")
load_dotenv()

TOKEN = os.getenv("CONTEXTO_DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("CONTEXTO_COMMAND_PREFIX") or os.getenv("COMMAND_PREFIX", "c!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("contexto-bot")

# Contexto game started on approximately 2022-09-18 (game #1)
CONTEXTO_EPOCH = date(2022, 9, 18)
BASE_API = "https://api.contexto.me/machado/en/game"

# File to persist subscribed channels across restarts (saved in bot directory)
SUBSCRIPTIONS_FILE = BASE_DIR / "subscriptions.json"

# Rank → emoji thresholds
RANK_THRESHOLDS = [
    (500,  "🟩", "Very close!"),
    (1500, "🟨", "Getting warmer..."),
    (3000, "🟧", "Still pretty far..."),
]
RANK_COLD = ("🟥", "Ice cold!")

# How long to wait (seconds) before giving up on an expired interaction
INTERACTION_TIMEOUT = 2.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_game_id_for_date(d: date) -> int:
    """Calculate the Contexto game number for a given date."""
    return max(1, (d - CONTEXTO_EPOCH).days)


def get_todays_game_id() -> int:
    return get_game_id_for_date(date.today())


def get_max_game_id() -> int:
    """The highest valid game number (today's)."""
    return get_todays_game_id()


def rank_emoji_and_label(rank: int) -> tuple[str, str]:
    for threshold, emoji, label in RANK_THRESHOLDS:
        if rank <= threshold:
            return emoji, label
    return RANK_COLD


def load_subscriptions() -> set[int]:
    """Load persisted channel subscription IDs from disk."""
    try:
        with open(SUBSCRIPTIONS_FILE, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_subscriptions(subs: set[int]) -> None:
    """Persist channel subscription IDs to disk."""
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(list(subs), f)


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------

@dataclass
class GuessEntry:
    word: str
    rank: int


@dataclass
class GameSession:
    game_id: int
    channel_id: int
    started_by: int
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    guesses: list[GuessEntry] = field(default_factory=list)
    solved: bool = False
    given_up: bool = False

    @property
    def is_daily(self) -> bool:
        return self.game_id == get_todays_game_id()

    def best_guess(self) -> Optional[GuessEntry]:
        if not self.guesses:
            return None
        return min(self.guesses, key=lambda g: g.rank)

    def already_guessed(self, word: str) -> Optional[GuessEntry]:
        word_lower = word.lower()
        return next((g for g in self.guesses if g.word.lower() == word_lower), None)

    def sorted_guesses(self) -> list[GuessEntry]:
        return sorted(self.guesses, key=lambda g: g.rank)

    def guess_count(self) -> int:
        return len(self.guesses)


# ---------------------------------------------------------------------------
# Contexto API
# ---------------------------------------------------------------------------

async def fetch_rank(
    http: aiohttp.ClientSession, game_id: int, word: str
) -> Optional[int]:
    """
    Query the Contexto API for the rank of `word` in `game_id`.
    Returns the rank (int) or None if word is unknown / request fails.
    """
    url = f"{BASE_API}/{game_id}/{word.lower().strip()}"
    try:
        async with http.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("distance")
            elif resp.status == 404:
                return None  # Word not in vocabulary
            else:
                log.warning("Unexpected API status %d for word '%s'", resp.status, word)
                return None
    except asyncio.TimeoutError:
        log.error("Timeout fetching rank for '%s'", word)
        return None
    except Exception as e:
        log.error("Error fetching rank for '%s': %s", word, e)
        return None


async def verify_game_exists(http: aiohttp.ClientSession, game_id: int) -> bool:
    """
    Check if a game ID is valid by probing it with a known-good word.
    We use 'water' — confirmed to rank in every Contexto game.
    Avoid stop words like 'the' which are NOT in Contexto's vocabulary.
    """
    rank = await fetch_rank(http, game_id, "water")
    return rank is not None


# ---------------------------------------------------------------------------
# Embeds
# ---------------------------------------------------------------------------

def make_start_embed(game_id: int, is_daily: bool) -> discord.Embed:
    label = f"🗓️ Today's Game — #{game_id}" if is_daily else f"📂 Game #{game_id}"
    embed = discord.Embed(
        title=f"🧠 Contexto — {label}",
        description=(
            "A secret word has been chosen. Try to guess it!\n\n"
            "Each guess is ranked by **semantic similarity** to the answer.\n"
            "**Rank #1 = the answer!**\n\n"
            "**Rank colors:**\n"
            "🟩 Top 500 — Very close!\n"
            "🟨 Top 1,500 — Getting warmer...\n"
            "🟧 Top 3,000 — Still pretty far...\n"
            "🟥 3,000+ — Ice cold!"
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Game #", value=str(game_id))
    embed.add_field(name="How to guess", value="`/contexto guess <word>`")
    embed.set_footer(text="Synced with contexto.me • Good luck!")
    return embed


def make_guess_embed(
    word: str, rank: int, guess_count: int, game_id: int, is_repeat: bool = False
) -> discord.Embed:
    emoji, label = rank_emoji_and_label(rank)

    if rank == 1:
        embed = discord.Embed(
            title="🎉 YOU GOT IT!",
            description=f"**`{word}`** is the secret word for game #{game_id}!",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Guesses taken", value=str(guess_count))
        return embed

    color_map = {
        "🟩": discord.Color.green(),
        "🟨": discord.Color.yellow(),
        "🟧": discord.Color.orange(),
        "🟥": discord.Color.red(),
    }
    repeat_note = " *(already guessed)*" if is_repeat else ""

    embed = discord.Embed(
        title=f"{emoji}  `{word}`{repeat_note}",
        color=color_map.get(emoji, discord.Color.blurple()),
    )
    embed.add_field(name="Rank", value=f"**#{rank:,}**", inline=True)
    embed.add_field(name="Status", value=label, inline=True)
    embed.add_field(name="Total Guesses", value=str(guess_count), inline=True)
    embed.set_footer(text=f"Contexto Game #{game_id}")
    return embed


def make_hint_embed(session: GameSession) -> discord.Embed:
    best = session.best_guess()
    if not best:
        return discord.Embed(
            title="💡 Hint",
            description="No guesses yet! Use `/contexto guess <word>` to start.",
            color=discord.Color.blurple(),
        )
    emoji, label = rank_emoji_and_label(best.rank)
    embed = discord.Embed(title="💡 Your Best Guess So Far", color=discord.Color.blurple())
    embed.add_field(name="Word", value=f"**`{best.word}`**", inline=True)
    embed.add_field(name="Rank", value=f"**#{best.rank:,}** {emoji}", inline=True)
    embed.add_field(name="Status", value=label, inline=True)
    embed.add_field(name="Total Guesses", value=str(session.guess_count()), inline=False)
    embed.set_footer(text=f"Game #{session.game_id}")
    return embed


def make_guesses_embed(session: GameSession) -> discord.Embed:
    sorted_g = session.sorted_guesses()
    if not sorted_g:
        return discord.Embed(
            title="📋 Your Guesses",
            description="No guesses yet! Use `/contexto guess <word>` to start.",
            color=discord.Color.blurple(),
        )
    lines = []
    for i, entry in enumerate(sorted_g[:25], 1):
        emoji, _ = rank_emoji_and_label(entry.rank)
        lines.append(f"`{i:>2}.` {emoji} **{entry.word}** — #{entry.rank:,}")

    remaining = len(sorted_g) - 25
    description = "\n".join(lines)
    if remaining > 0:
        description += f"\n*... and {remaining} more guesses*"

    embed = discord.Embed(
        title=f"📋 Guesses for Game #{session.game_id}",
        description=description,
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"{len(sorted_g)} total guesses")
    return embed


def make_giveup_embed(session: GameSession) -> discord.Embed:
    best = session.best_guess()
    embed = discord.Embed(
        title="🏳️ Game Over",
        description=(
            "You gave up! Contexto's API doesn't expose the answer directly.\n"
            f"Check the answer at **[contexto.me](https://contexto.me)**."
        ),
        color=discord.Color.dark_gray(),
    )
    embed.add_field(name="Game #", value=str(session.game_id), inline=True)
    embed.add_field(name="Total Guesses", value=str(session.guess_count()), inline=True)
    if best:
        emoji, _ = rank_emoji_and_label(best.rank)
        embed.add_field(
            name="Your Best Guess",
            value=f"**`{best.word}`** — Rank #{best.rank:,} {emoji}",
            inline=False,
        )
    embed.set_footer(text="Start a new game with /contexto start")
    return embed


def make_daily_announce_embed(game_id: int) -> discord.Embed:
    embed = discord.Embed(
        title="🌅 New Contexto Puzzle Available!",
        description=(
            f"Today's **Game #{game_id}** is ready to play!\n\n"
            "Use `/contexto start` to begin, or `/contexto start game:<number>` "
            "to play any past game."
        ),
        color=discord.Color.og_blurple(),
    )
    embed.set_footer(text="contexto.me • A new puzzle drops every day!")
    return embed


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

class ContextoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required for prefix commands + auto-guess
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)

        # channel_id → GameSession (one active session per channel)
        self.sessions: dict[int, GameSession] = {}

        # channel_ids that want daily announcements
        self.subscribed_channels: set[int] = load_subscriptions()

        self.http_session: Optional[aiohttp.ClientSession] = None

        # Track the last announced game ID to avoid double-posting
        self._last_announced_game_id: int = get_todays_game_id()

    async def setup_hook(self):
        await self.tree.sync()
        log.info("Slash commands synced.")
        self.http_session = aiohttp.ClientSession(
            headers={"User-Agent": "ContextoDiscordBot/1.0"}
        )
        self.daily_game_loop.start()

    async def close(self):
        self.daily_game_loop.cancel()
        if self.http_session:
            await self.http_session.close()
        await super().close()

    async def on_ready(self):
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Game(name=f"Contexto | {COMMAND_PREFIX}start")
        )

    async def on_message(self, message: discord.Message):
        # Always process prefix commands first
        await self.process_commands(message)

        # Ignore bots and messages that start with the prefix (already handled above)
        if message.author.bot:
            return
        if message.content.startswith(COMMAND_PREFIX):
            return

        # Auto-guess: if there's an active game in this channel, treat single words as guesses
        session = self.sessions.get(message.channel.id)
        if not session or session.solved or session.given_up:
            return

        word = message.content.strip().lower()

        # Must be a single alphabetic word
        if not word or not word.isalpha() or " " in word:
            return

        # Duplicate guess — reply with the cached rank immediately
        existing = session.already_guessed(word)
        if existing:
            emoji, label = rank_emoji_and_label(existing.rank)
            await message.reply(
                embed=make_guess_embed(
                    existing.word, existing.rank,
                    session.guess_count(), session.game_id, is_repeat=True,
                ),
                mention_author=False,
            )
            return

        # Fetch from Contexto API
        async with message.channel.typing():
            rank = await fetch_rank(self.http_session, session.game_id, word)

        if rank is None:
            await message.reply(
                f"❓ **`{word}`** isn't in Contexto's vocabulary — try another word!",
                mention_author=False,
            )
            return

        entry = GuessEntry(word=word, rank=rank)
        session.guesses.append(entry)

        if rank == 1:
            session.solved = True

        await message.reply(
            embed=make_guess_embed(word, rank, session.guess_count(), session.game_id),
            mention_author=False,
        )

    # ------------------------------------------------------------------
    # Daily loop — fires every 60 seconds, announces when day rolls over
    # ------------------------------------------------------------------
    @tasks.loop(minutes=1)
    async def daily_game_loop(self):
        today_id = get_todays_game_id()
        if today_id <= self._last_announced_game_id:
            return  # Not a new day yet

        log.info("New day detected! Game #%d is live. Announcing to %d channels.",
                 today_id, len(self.subscribed_channels))

        self._last_announced_game_id = today_id

        # Clear sessions from the previous day (daily games only)
        expired = [
            cid for cid, s in self.sessions.items()
            if s.is_daily and not s.solved
        ]
        for cid in expired:
            del self.sessions[cid]

        # Announce to all subscribed channels
        embed = make_daily_announce_embed(today_id)
        dead_channels: list[int] = []

        for channel_id in list(self.subscribed_channels):
            channel = self.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.fetch_channel(channel_id)
                except discord.NotFound:
                    log.warning("Channel %d not found, removing from subscriptions.", channel_id)
                    dead_channels.append(channel_id)
                    continue
                except discord.Forbidden:
                    log.warning("No access to channel %d, removing.", channel_id)
                    dead_channels.append(channel_id)
                    continue

            try:
                await channel.send(embed=embed)
                log.info("Announced Game #%d to channel %d", today_id, channel_id)
            except discord.Forbidden:
                log.warning("Cannot send to channel %d, removing.", channel_id)
                dead_channels.append(channel_id)
            except Exception as e:
                log.error("Failed to announce to channel %d: %s", channel_id, e)

        # Prune dead channels
        if dead_channels:
            for cid in dead_channels:
                self.subscribed_channels.discard(cid)
            save_subscriptions(self.subscribed_channels)

    @daily_game_loop.before_loop
    async def before_daily_loop(self):
        await self.wait_until_ready()


bot = ContextoBot()


# ---------------------------------------------------------------------------
# Safe response helpers
# Interaction tokens expire after 3 seconds if not acknowledged.
# These helpers catch the NotFound (10062) error gracefully instead of
# letting it bubble up and spam the logs with a full traceback.
# ---------------------------------------------------------------------------

async def safe_send(
    interaction: discord.Interaction,
    *args,
    ephemeral: bool = False,
    **kwargs,
) -> bool:
    """
    Send an interaction response safely.
    Returns True on success, False if the interaction already expired.
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(*args, ephemeral=ephemeral, **kwargs)
        else:
            await interaction.response.send_message(*args, ephemeral=ephemeral, **kwargs)
        return True
    except discord.NotFound:
        log.warning(
            "Interaction expired before we could respond (command: %s, user: %s).",
            interaction.command.name if interaction.command else "unknown",
            interaction.user,
        )
        return False
    except discord.HTTPException as e:
        log.error("HTTP error sending interaction response: %s", e)
        return False


async def safe_defer(interaction: discord.Interaction) -> bool:
    """Defer an interaction safely. Returns True on success."""
    try:
        await interaction.response.defer()
        return True
    except discord.NotFound:
        log.warning("Interaction expired before defer (command: %s).",
                    interaction.command.name if interaction.command else "unknown")
        return False


# ---------------------------------------------------------------------------
# Global app-command error handler — catches anything not handled per-command
# ---------------------------------------------------------------------------

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    # Unwrap the inner exception if it's wrapped in CommandInvokeError
    original = getattr(error, "original", error)

    if isinstance(original, discord.NotFound) and getattr(original, "code", None) == 10062:
        # Interaction expired — harmless, just log it quietly
        log.warning(
            "Stale interaction ignored (10062) — command '%s' by %s.",
            interaction.command.name if interaction.command else "?",
            interaction.user,
        )
        return

    if isinstance(error, app_commands.MissingPermissions):
        await safe_send(
            interaction,
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )
        return

    # Unexpected error — log the full traceback and tell the user
    log.exception("Unhandled app command error in '%s':",
                  interaction.command.name if interaction.command else "?",
                  exc_info=original)
    await safe_send(
        interaction,
        "⚠️ Something went wrong. Please try again in a moment.",
        ephemeral=True,
    )


# ---------------------------------------------------------------------------
# Slash Command Group
# ---------------------------------------------------------------------------

contexto_group = app_commands.Group(
    name="contexto", description="Play Contexto on Discord!"
)


# /contexto start [game]
@contexto_group.command(
    name="start",
    description="Start today's Contexto game, or pick a specific game number.",
)
@app_commands.describe(game="Game number to play (leave blank for today's game)")
async def contexto_start(interaction: discord.Interaction, game: Optional[int] = None):
    channel_id = interaction.channel_id

    # Resolve the game ID
    if game is not None:
        max_id = get_max_game_id()
        if game < 1 or game > max_id:
            await safe_send(
                interaction,
                f"❌ Invalid game number. Pick a number between **1** and **{max_id}** "
                f"(today's game is #{max_id}).",
                ephemeral=True,
            )
            return
        game_id = game
    else:
        game_id = get_todays_game_id()

    # Check for an already-active session
    existing = bot.sessions.get(channel_id)
    if existing and not existing.solved and not existing.given_up:
        await safe_send(
            interaction,
            f"⚠️ A game is already running in this channel! (Game #{existing.game_id})\n"
            f"Use `/contexto guess <word>` to keep playing, or `/contexto giveup` to end it.",
            ephemeral=True,
        )
        return

    if not await safe_defer(interaction):
        return  # Interaction already expired, bail out

    # Only verify custom game numbers — today's game is always valid
    if game is not None and not await verify_game_exists(bot.http_session, game_id):
        await interaction.followup.send(
            f"❌ Game #{game_id} doesn't seem to exist on Contexto yet. Try a lower number!",
            ephemeral=True,
        )
        return

    bot.sessions[channel_id] = GameSession(
        game_id=game_id,
        channel_id=channel_id,
        started_by=interaction.user.id,
    )
    log.info("Game #%d started in channel %d by %s", game_id, channel_id, interaction.user)
    await interaction.followup.send(embed=make_start_embed(game_id, is_daily=(game is None)))


# /contexto guess <word>
@contexto_group.command(name="guess", description="Guess a word and see its rank.")
@app_commands.describe(word="The word you want to guess")
async def contexto_guess(interaction: discord.Interaction, word: str):
    channel_id = interaction.channel_id

    if channel_id not in bot.sessions:
        await safe_send(
            interaction,
            "❌ No game is running! Start one with `/contexto start`.",
            ephemeral=True,
        )
        return

    session = bot.sessions[channel_id]

    if session.solved:
        await safe_send(
            interaction,
            "✅ This game is already solved! Start a new one with `/contexto start`.",
            ephemeral=True,
        )
        return

    if session.given_up:
        await safe_send(
            interaction,
            "🏳️ This game was ended. Start a new one with `/contexto start`.",
            ephemeral=True,
        )
        return

    word = word.strip().lower()
    if not word.isalpha():
        await safe_send(
            interaction,
            "❌ Please enter a single word with letters only.",
            ephemeral=True,
        )
        return

    # Repeat guess — respond immediately (no API call needed)
    existing = session.already_guessed(word)
    if existing:
        await safe_send(
            interaction,
            embed=make_guess_embed(
                existing.word, existing.rank,
                session.guess_count(), session.game_id, is_repeat=True,
            ),
        )
        return

    # Defer before hitting the API
    if not await safe_defer(interaction):
        return

    rank = await fetch_rank(bot.http_session, session.game_id, word)
    if rank is None:
        await interaction.followup.send(
            f"❓ **`{word}`** wasn't recognized — it might not be in Contexto's vocabulary. Try another word!"
        )
        return

    entry = GuessEntry(word=word, rank=rank)
    session.guesses.append(entry)

    if rank == 1:
        session.solved = True

    await interaction.followup.send(
        embed=make_guess_embed(word, rank, session.guess_count(), session.game_id)
    )


# /contexto hint
@contexto_group.command(name="hint", description="Show your closest guess so far.")
async def contexto_hint(interaction: discord.Interaction):
    session = bot.sessions.get(interaction.channel_id)
    if not session:
        await safe_send(
            interaction,
            "❌ No game is running! Start one with `/contexto start`.",
            ephemeral=True,
        )
        return
    await safe_send(interaction, embed=make_hint_embed(session))


# /contexto guesses
@contexto_group.command(
    name="guesses", description="List all your guesses this session, sorted by rank."
)
async def contexto_guesses(interaction: discord.Interaction):
    session = bot.sessions.get(interaction.channel_id)
    if not session:
        await safe_send(
            interaction,
            "❌ No game is running! Start one with `/contexto start`.",
            ephemeral=True,
        )
        return
    await safe_send(interaction, embed=make_guesses_embed(session))


# /contexto giveup
@contexto_group.command(name="giveup", description="Reveal stats and end the current game.")
async def contexto_giveup(interaction: discord.Interaction):
    session = bot.sessions.get(interaction.channel_id)
    if not session:
        await safe_send(
            interaction,
            "❌ No game is running! Start one with `/contexto start`.",
            ephemeral=True,
        )
        return
    if session.solved or session.given_up:
        await safe_send(
            interaction,
            "This game is already over. Start a new one with `/contexto start`.",
            ephemeral=True,
        )
        return

    session.given_up = True
    await safe_send(interaction, embed=make_giveup_embed(session))


# /contexto today
@contexto_group.command(name="today", description="Show info about today's game number.")
async def contexto_today(interaction: discord.Interaction):
    game_id = get_todays_game_id()
    session = bot.sessions.get(interaction.channel_id)
    embed = discord.Embed(
        title="🗓️ Today's Contexto",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Game #", value=str(game_id), inline=True)
    embed.add_field(name="Date", value=str(date.today()), inline=True)
    if session:
        status = "✅ Solved!" if session.solved else ("🏳️ Ended" if session.given_up else "🎮 In Progress")
        embed.add_field(name="This channel", value=f"Game #{session.game_id} — {status}", inline=False)
    else:
        embed.add_field(name="This channel", value="No active game. Use `/contexto start`!", inline=False)
    await safe_send(interaction, embed=embed)


# /contexto subscribe / unsubscribe
@contexto_group.command(
    name="subscribe",
    description="Subscribe this channel to daily Contexto game announcements.",
)
@app_commands.checks.has_permissions(manage_channels=True)
async def contexto_subscribe(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in bot.subscribed_channels:
        await safe_send(
            interaction,
            "✅ This channel is **already subscribed** to daily Contexto announcements.",
            ephemeral=True,
        )
        return
    bot.subscribed_channels.add(channel_id)
    save_subscriptions(bot.subscribed_channels)
    log.info("Channel %d subscribed to daily announcements.", channel_id)
    await safe_send(
        interaction,
        "🔔 **Subscribed!** I'll announce the new Contexto puzzle here every day.\n"
        "Use `/contexto unsubscribe` to stop.",
    )


@contexto_group.command(
    name="unsubscribe",
    description="Stop daily Contexto game announcements in this channel.",
)
@app_commands.checks.has_permissions(manage_channels=True)
async def contexto_unsubscribe(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id not in bot.subscribed_channels:
        await safe_send(
            interaction,
            "❌ This channel is **not subscribed** to daily announcements.",
            ephemeral=True,
        )
        return
    bot.subscribed_channels.discard(channel_id)
    save_subscriptions(bot.subscribed_channels)
    log.info("Channel %d unsubscribed.", channel_id)
    await safe_send(interaction, "🔕 **Unsubscribed.** No more daily announcements here.")


bot.tree.add_command(contexto_group)


# ---------------------------------------------------------------------------
# Prefix Commands  (c!start, c!giveup, c!hint, c!guesses, c!today, c!help)
# These mirror the slash commands so users have both options.
# ---------------------------------------------------------------------------

@bot.command(name="start", aliases=["play", "begin"])
async def prefix_start(ctx: commands.Context, game: Optional[int] = None):
    """Start today's game or a specific game number. Usage: c!start [game_number]"""
    channel_id = ctx.channel.id

    if game is not None:
        max_id = get_max_game_id()
        if game < 1 or game > max_id:
            await ctx.reply(
                f"❌ Invalid game number. Pick between **1** and **{max_id}**.",
                mention_author=False,
            )
            return
        game_id = game
    else:
        game_id = get_todays_game_id()

    existing = bot.sessions.get(channel_id)
    if existing and not existing.solved and not existing.given_up:
        await ctx.reply(
            f"⚠️ A game is already running! (Game #{existing.game_id})\n"
            f"Just type a word to guess, or use `{COMMAND_PREFIX}giveup` to end it.",
            mention_author=False,
        )
        return

    async with ctx.typing():
        if game is not None and not await verify_game_exists(bot.http_session, game_id):
            await ctx.reply(
                f"❌ Game #{game_id} doesn't exist yet. Try a lower number!",
                mention_author=False,
            )
            return

    bot.sessions[channel_id] = GameSession(
        game_id=game_id,
        channel_id=channel_id,
        started_by=ctx.author.id,
    )
    log.info("Game #%d started in channel %d by %s (prefix)", game_id, channel_id, ctx.author)
    await ctx.send(embed=make_start_embed(game_id, is_daily=(game is None)))


@bot.command(name="giveup", aliases=["quit", "give_up"])
async def prefix_giveup(ctx: commands.Context):
    """End the current game. Usage: c!giveup"""
    session = bot.sessions.get(ctx.channel.id)
    if not session:
        await ctx.reply(f"❌ No game is running! Use `{COMMAND_PREFIX}start` to begin.", mention_author=False)
        return
    if session.solved or session.given_up:
        await ctx.reply("This game is already over.", mention_author=False)
        return
    session.given_up = True
    await ctx.send(embed=make_giveup_embed(session))


@bot.command(name="hint")
async def prefix_hint(ctx: commands.Context):
    """Show your closest guess so far. Usage: c!hint"""
    session = bot.sessions.get(ctx.channel.id)
    if not session:
        await ctx.reply(f"❌ No game is running! Use `{COMMAND_PREFIX}start` to begin.", mention_author=False)
        return
    await ctx.send(embed=make_hint_embed(session))


@bot.command(name="guesses", aliases=["list", "history"])
async def prefix_guesses(ctx: commands.Context):
    """List all guesses sorted by rank. Usage: c!guesses"""
    session = bot.sessions.get(ctx.channel.id)
    if not session:
        await ctx.reply(f"❌ No game is running! Use `{COMMAND_PREFIX}start` to begin.", mention_author=False)
        return
    await ctx.send(embed=make_guesses_embed(session))


@bot.command(name="today")
async def prefix_today(ctx: commands.Context):
    """Show today's game number and status. Usage: c!today"""
    game_id = get_todays_game_id()
    session = bot.sessions.get(ctx.channel.id)
    embed = discord.Embed(title="🗓️ Today's Contexto", color=discord.Color.blurple())
    embed.add_field(name="Game #", value=str(game_id), inline=True)
    embed.add_field(name="Date", value=str(date.today()), inline=True)
    if session:
        status = "✅ Solved!" if session.solved else ("🏳️ Ended" if session.given_up else "🎮 In Progress")
        embed.add_field(name="This channel", value=f"Game #{session.game_id} — {status}", inline=False)
    else:
        embed.add_field(name="This channel", value=f"No active game. Use `{COMMAND_PREFIX}start`!", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="chelp", aliases=["commands"])
async def prefix_help(ctx: commands.Context):
    """Show all available commands. Usage: c!chelp"""
    embed = discord.Embed(
        title="🧠 Contexto Bot — Commands",
        description=(
            f"**Prefix commands** (prefix: `{COMMAND_PREFIX}`)\n"
            f"`{COMMAND_PREFIX}start [game]` — Start today's or a specific game\n"
            f"`{COMMAND_PREFIX}giveup` — End the current game\n"
            f"`{COMMAND_PREFIX}hint` — Show your best guess so far\n"
            f"`{COMMAND_PREFIX}guesses` — List all guesses sorted by rank\n"
            f"`{COMMAND_PREFIX}today` — Show today's game info\n\n"
            "**Slash commands** — same features, type `/contexto`\n\n"
            "💡 **Once a game starts, just type any word to guess!**\n"
            "No command needed — the bot auto-detects single words."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Rank colors",
        value="🟩 Top 500 · 🟨 Top 1,500 · 🟧 Top 3,000 · 🟥 3,000+",
        inline=False,
    )
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    if not TOKEN:
        log.error("DISCORD_TOKEN (or CONTEXTO_DISCORD_TOKEN) not found! Create a .env file with DISCORD_TOKEN=your_token")
        raise SystemExit(1)
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()

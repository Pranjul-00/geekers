"""Expresso Discord Bot.

A daily phrase-guessing puzzle bot with group comparison charts,
automated drop reminders, and friendly banter for close friend groups.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from .charts import generate_daily_comparison_embed, generate_head_to_head_embed
from .game import ExpressoCatalog, ExpressoSession
from .reminders import ExpressoScheduler
from .storage import ExpressoStorage, PlayerResult
from shared.hub import GeekersHubView

# ---------------------------------------------------------------------------
# Config & Setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

# Load local .env then root .env
load_dotenv(BASE_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")
load_dotenv()

TOKEN = os.getenv("EXPRESSO_DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("EXPRESSO_COMMAND_PREFIX") or os.getenv("COMMAND_PREFIX", "e!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("expresso-bot")

storage = ExpressoStorage(BASE_DIR / "expresso.db")

# Active per-channel game sessions
sessions: Dict[int, ExpressoSession] = {}


# ---------------------------------------------------------------------------
# Bot Client
# ---------------------------------------------------------------------------

class ExpressoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=COMMAND_PREFIX,
            intents=intents,
            help_command=None,
        )
        self.scheduler: Optional[ExpressoScheduler] = None

    async def setup_hook(self) -> None:
        self.scheduler = ExpressoScheduler(self, storage)
        self.scheduler.start()
        try:
            synced = await self.tree.sync()
            log.info("Synced %d slash commands.", len(synced))
        except Exception as e:
            log.error("Failed to sync slash commands: %s", e)

    async def close(self) -> None:
        if self.scheduler:
            self.scheduler.stop()
        await super().close()

    async def on_ready(self) -> None:
        log.info("Expresso Bot online as %s (ID: %s)", self.user, self.user.id)
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=f"Expresso | {COMMAND_PREFIX}start or /expresso",
        )
        await self.change_presence(activity=activity)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        # Auto-guess sniffing: if active game in channel and message doesn't start with prefix
        channel_id = message.channel.id
        if channel_id in sessions and not message.content.startswith(COMMAND_PREFIX):
            session = sessions[channel_id]
            if not session.solved and not session.given_up:
                # If message looks like a guess
                text = message.content.strip()
                if len(text) >= 2 and not text.startswith("/"):
                    feedback = session.make_guess(text)
                    await handle_guess_response(message.channel, message.author, session, feedback)
                    return

        await self.process_commands(message)


bot = ExpressoBot()


# ---------------------------------------------------------------------------
# Response Helpers
# ---------------------------------------------------------------------------

async def handle_guess_response(
    channel: discord.abc.Messageable,
    user: discord.User | discord.Member,
    session: ExpressoSession,
    feedback,
) -> None:
    if feedback.is_correct:
        # Player solved the puzzle!
        guild_id = channel.guild.id if hasattr(channel, "guild") and channel.guild else 0
        res = PlayerResult(
            guild_id=guild_id,
            channel_id=channel.id,
            user_id=user.id,
            user_name=user.display_name,
            game_id=session.puzzle.game_id,
            guesses_count=len(session.guesses),
            solve_time_seconds=session.elapsed_seconds,
            hints_used=session.hints_used,
            solved=True,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        storage.record_result(res)

        embed = discord.Embed(
            title="🎉 Espresso Doppio! Puzzle Solved!",
            description=(
                f"**{user.display_name}** cracked today's phrase in **{len(session.guesses)}** guesses!\n\n"
                f"🏆 Target: **{session.target_phrase}**\n"
                f"⏱️ Time: **{session.elapsed_formatted}**\n"
                f"💡 Hints used: **{session.hints_used}**\n\n"
                f"Use `{COMMAND_PREFIX}chart` to see how the group stacks up!"
            ),
            color=discord.Color.gold(),
        )
        del sessions[channel.id]
        await channel.send(embed=embed)
    else:
        # Provide detailed Wordle-style letter-by-letter feedback
        embed = discord.Embed(
            title=f"☕ Expresso — Guess #{len(session.guesses)}: {feedback.guess_text}",
            color=discord.Color.from_rgb(186, 110, 48),
        )
        embed.add_field(
            name="🔤 Tile Feedback",
            value=feedback.feedback_line if feedback.feedback_line else "`None`",
            inline=False,
        )
        embed.add_field(
            name="📋 Letter Breakdown",
            value=feedback.explanation,
            inline=False,
        )
        embed.add_field(
            name="🧩 Current Phrase Board",
            value=f"{feedback.revealed_board}\n*{feedback.word_lengths_info}*",
            inline=False,
        )

        found_str = ", ".join(feedback.found_letters) if feedback.found_letters else "None yet"
        elim_str = ", ".join(feedback.eliminated_letters) if feedback.eliminated_letters else "None yet"
        embed.add_field(
            name="🔠 Letter Tracker",
            value=f"• **Found in Phrase:** {found_str}\n• **Not in Phrase:** {elim_str}",
            inline=False,
        )
        embed.set_footer(text=f"Guessed by {user.display_name} · Keep typing words or use {COMMAND_PREFIX}hint")
        await channel.send(embed=embed)


# ---------------------------------------------------------------------------
# Slash Commands Group (/expresso)
# ---------------------------------------------------------------------------

expresso_group = app_commands.Group(name="expresso", description="Play daily Expresso phrase puzzles")


@expresso_group.command(name="start", description="Start today's Expresso phrase puzzle")
@app_commands.describe(game="Optional historical game number")
async def slash_start(interaction: discord.Interaction, game: Optional[int] = None):
    channel_id = interaction.channel_id
    if channel_id in sessions and not sessions[channel_id].solved:
        await interaction.response.send_message(
            f"⚠️ A game is already active in this channel! Board:\n`{sessions[channel_id].get_masked_board()}`",
            ephemeral=True,
        )
        return

    puzzle = ExpressoCatalog.get_by_id(game) if game else ExpressoCatalog.get_today()
    session = ExpressoSession(puzzle, channel_id, interaction.user.id)
    sessions[channel_id] = session

    embed = discord.Embed(
        title=f"☕ Expresso Daily #{puzzle.game_id}",
        description=(
            f"**Category:** {puzzle.category}\n"
            f"**Words:** {len(puzzle.phrase.split())} words\n\n"
            f"**Current Board:**\n{session.get_masked_board()}\n"
            f"*{session.get_word_lengths_info()}*\n\n"
            "💡 **Simply type guesses directly in chat!**\n"
            f"Or use `/expresso hint` or `{COMMAND_PREFIX}giveup` if stumped."
        ),
        color=discord.Color.from_rgb(212, 143, 56),
    )
    await interaction.response.send_message(embed=embed)


@expresso_group.command(name="hint", description="Reveal a letter or clue")
async def slash_hint(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id not in sessions:
        await interaction.response.send_message("No active game in this channel. Start one with `/expresso start`!", ephemeral=True)
        return

    session = sessions[channel_id]
    num, text = session.use_hint()
    embed = discord.Embed(
        title=f"💡 Hint #{num}",
        description=f"{text}\n\n**Updated Board:**\n`{session.get_masked_board()}`",
        color=discord.Color.blue(),
    )
    await interaction.response.send_message(embed=embed)


@expresso_group.command(name="chart", description="View group comparison standings for today")
async def slash_chart(interaction: discord.Interaction):
    puzzle = ExpressoCatalog.get_today()
    results = storage.get_channel_daily_results(interaction.channel_id, puzzle.game_id)
    embed = generate_daily_comparison_embed(puzzle.game_id, results)
    await interaction.response.send_message(embed=embed)


@expresso_group.command(name="compare", description="Compare stats head-to-head with a friend")
@app_commands.describe(friend="The friend to compare stats with")
async def slash_compare(interaction: discord.Interaction, friend: discord.Member):
    guild_id = interaction.guild_id or 0
    p1 = storage.get_player_stats(guild_id, interaction.user.id)
    p2 = storage.get_player_stats(guild_id, friend.id)

    if not p1 or not p2:
        await interaction.response.send_message(
            "Both players must have finished at least one Expresso game to compare stats!",
            ephemeral=True,
        )
        return

    embed = generate_head_to_head_embed(p1, p2)
    await interaction.response.send_message(embed=embed)


@expresso_group.command(name="giveup", description="Surrender and reveal today's phrase")
async def slash_giveup(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id not in sessions:
        await interaction.response.send_message("No active game in this channel.", ephemeral=True)
        return

    session = sessions[channel_id]
    ans = session.give_up()
    guild_id = interaction.guild_id or 0
    res = PlayerResult(
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=interaction.user.id,
        user_name=interaction.user.display_name,
        game_id=session.puzzle.game_id,
        guesses_count=len(session.guesses),
        solve_time_seconds=session.elapsed_seconds,
        hints_used=session.hints_used,
        solved=False,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )
    storage.record_result(res)
    del sessions[channel_id]

    embed = discord.Embed(
        title="🏳️ Game Over — Phrase Revealed",
        description=f"The answer was: **{ans}**\nBetter luck tomorrow! ☕",
        color=discord.Color.red(),
    )
    await interaction.response.send_message(embed=embed)


@expresso_group.command(name="subscribe", description="Subscribe channel to daily puzzle drops and reminders")
async def slash_subscribe(interaction: discord.Interaction):
    storage.add_subscription(interaction.channel_id, interaction.guild_id or 0)
    await interaction.response.send_message("✅ This channel will receive daily Expresso drops and evening reminders! ☕")


@expresso_group.command(name="unsubscribe", description="Unsubscribe from daily announcements")
async def slash_unsubscribe(interaction: discord.Interaction):
    storage.remove_subscription(interaction.channel_id)
    await interaction.response.send_message("🔕 Channel unsubscribed from Expresso notifications.")


bot.tree.add_command(expresso_group)


@bot.tree.command(name="geekers", description="Open the Geekers Game Hub to select games and view stats")
async def slash_geekers(interaction: discord.Interaction):
    guild_id = interaction.guild_id or 0
    view = GeekersHubView(interaction.user, guild_id, interaction.channel_id, storage, sessions)
    embed = view.render_embed()
    await interaction.response.send_message(embed=embed, view=view)


# ---------------------------------------------------------------------------
# Prefix Commands (Default: e!)
# ---------------------------------------------------------------------------

@bot.command(name="geekers", aliases=["menu", "hub", "games"])
async def prefix_geekers(ctx: commands.Context):
    guild_id = ctx.guild.id if ctx.guild else 0
    view = GeekersHubView(ctx.author, guild_id, ctx.channel.id, storage, sessions)
    embed = view.render_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name="start", aliases=["play", "begin"])
async def prefix_start(ctx: commands.Context, game: Optional[int] = None):
    channel_id = ctx.channel.id
    if channel_id in sessions and not sessions[channel_id].solved:
        await ctx.send(f"⚠️ Game already active! Board:\n`{sessions[channel_id].get_masked_board()}`")
        return

    puzzle = ExpressoCatalog.get_by_id(game) if game else ExpressoCatalog.get_today()
    session = ExpressoSession(puzzle, channel_id, ctx.author.id)
    sessions[channel_id] = session

    embed = discord.Embed(
        title=f"☕ Expresso Daily #{puzzle.game_id}",
        description=(
            f"**Category:** {puzzle.category}\n"
            f"**Words:** {len(puzzle.phrase.split())} words\n\n"
            f"**Current Board:**\n{session.get_masked_board()}\n"
            f"*{session.get_word_lengths_info()}*\n\n"
            "💡 **Type any word or phrase in chat to guess!**\n"
            f"Or use `{COMMAND_PREFIX}hint` or `{COMMAND_PREFIX}giveup`."
        ),
        color=discord.Color.from_rgb(212, 143, 56),
    )
    await ctx.send(embed=embed)


@bot.command(name="chart", aliases=["standings", "leaderboard"])
async def prefix_chart(ctx: commands.Context):
    puzzle = ExpressoCatalog.get_today()
    results = storage.get_channel_daily_results(ctx.channel.id, puzzle.game_id)
    embed = generate_daily_comparison_embed(puzzle.game_id, results)
    await ctx.send(embed=embed)


@bot.command(name="compare", aliases=["vs"])
async def prefix_compare(ctx: commands.Context, friend: discord.Member):
    guild_id = ctx.guild.id if ctx.guild else 0
    p1 = storage.get_player_stats(guild_id, ctx.author.id)
    p2 = storage.get_player_stats(guild_id, friend.id)

    if not p1 or not p2:
        await ctx.send("Both players must have finished at least one game to compare stats!")
        return

    embed = generate_head_to_head_embed(p1, p2)
    await ctx.send(embed=embed)


@bot.command(name="hint")
async def prefix_hint(ctx: commands.Context):
    channel_id = ctx.channel.id
    if channel_id not in sessions:
        await ctx.send(f"No active game! Start one with `{COMMAND_PREFIX}start`.")
        return

    session = sessions[channel_id]
    num, text = session.use_hint()
    embed = discord.Embed(
        title=f"💡 Hint #{num}",
        description=f"{text}\n\n**Board:**\n`{session.get_masked_board()}`",
        color=discord.Color.blue(),
    )
    await ctx.send(embed=embed)


@bot.command(name="giveup", aliases=["surrender"])
async def prefix_giveup(ctx: commands.Context):
    channel_id = ctx.channel.id
    if channel_id not in sessions:
        await ctx.send("No active game in this channel.")
        return

    session = sessions[channel_id]
    ans = session.give_up()
    guild_id = ctx.guild.id if ctx.guild else 0
    res = PlayerResult(
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=ctx.author.id,
        user_name=ctx.author.display_name,
        game_id=session.puzzle.game_id,
        guesses_count=len(session.guesses),
        solve_time_seconds=session.elapsed_seconds,
        hints_used=session.hints_used,
        solved=False,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )
    storage.record_result(res)
    del sessions[channel_id]

    embed = discord.Embed(
        title="🏳️ Game Over — Phrase Revealed",
        description=f"The answer was: **{ans}**\nBetter luck tomorrow! ☕",
        color=discord.Color.red(),
    )
    await ctx.send(embed=embed)


@bot.command(name="subscribe")
async def prefix_subscribe(ctx: commands.Context):
    storage.add_subscription(ctx.channel.id, ctx.guild.id if ctx.guild else 0)
    await ctx.send("✅ This channel will receive daily Expresso drops and evening reminders! ☕")


@bot.command(name="unsubscribe")
async def prefix_unsubscribe(ctx: commands.Context):
    storage.remove_subscription(ctx.channel.id)
    await ctx.send("🔕 Channel unsubscribed from Expresso notifications.")


@bot.command(name="help", aliases=["ehelp", "commands"])
async def prefix_help(ctx: commands.Context):
    embed = discord.Embed(
        title="☕ Expresso Bot — Commands",
        description=(
            f"**Prefix commands** (prefix: `{COMMAND_PREFIX}`)\n"
            f"`{COMMAND_PREFIX}start [game]` — Start today's phrase or pick game #\n"
            f"`{COMMAND_PREFIX}chart` — Side-by-side daily standings & comparison\n"
            f"`{COMMAND_PREFIX}compare @friend` — Head-to-head stats comparison\n"
            f"`{COMMAND_PREFIX}hint` — Reveal a letter or contextual clue\n"
            f"`{COMMAND_PREFIX}giveup` — Surrender and reveal phrase\n"
            f"`{COMMAND_PREFIX}subscribe` — Enable daily drops and reminder pings\n\n"
            "💡 **Once started, just type words or phrases in chat!**"
        ),
        color=discord.Color.from_rgb(212, 143, 56),
    )
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    if not TOKEN:
        log.error("DISCORD_TOKEN (or EXPRESSO_DISCORD_TOKEN) not found in .env!")
        raise SystemExit(1)
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()

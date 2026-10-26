"""Geekers Unified Discord Bot.

A single unified bot hosting all daily game bots (Contexto, Expresso, Wordle, etc.)
with interactive dropdown game hubs, comparison charts, and automated reminders.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from bots.contexto.bot import (
    bot as contexto_bot,
    contexto_group,
    get_todays_game_id,
    make_guess_embed,
    rank_emoji_and_label,
    fetch_rank,
    safe_send,
)
from bots.expresso.bot import (
    bot as expresso_bot,
    expresso_group,
    handle_guess_response as handle_expresso_guess,
    sessions as expresso_sessions,
    storage as expresso_storage,
)
from bots.expresso.reminders import ExpressoScheduler
from shared.hub import GeekersHubView

# ---------------------------------------------------------------------------
# Config & Setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("EXPRESSO_DISCORD_TOKEN") or os.getenv("CONTEXTO_DISCORD_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("geekers")


class GeekersBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        try:
            intents.members = True
        except Exception:
            pass

        super().__init__(
            command_prefix=["g!", "c!", "e!", "!"],
            intents=intents,
            help_command=None,
        )
        self.expresso_scheduler: Optional[ExpressoScheduler] = None

    async def setup_hook(self) -> None:
        # 1. Setup Contexto engine session and background loops
        if not contexto_bot.http_session or contexto_bot.http_session.closed:
            contexto_bot.http_session = aiohttp.ClientSession(
                headers={"User-Agent": "GeekersBot/1.0 (Contexto Engine)"}
            )
        if not contexto_bot.daily_game_loop.is_running():
            contexto_bot.daily_game_loop.start()

        # 2. Setup Expresso scheduler (midnight drops & evening reminders)
        self.expresso_scheduler = ExpressoScheduler(self, expresso_storage)
        self.expresso_scheduler.start()

        # 3. Mount slash command groups to the unified bot tree
        try:
            self.tree.add_command(expresso_group)
        except Exception as e:
            log.debug("expresso_group already registered: %s", e)

        try:
            self.tree.add_command(contexto_group)
        except Exception as e:
            log.debug("contexto_group already registered: %s", e)

        # 4. Sync commands with Discord Gateway
        try:
            synced = await self.tree.sync()
            log.info("Geekers Unified Bot synced %d slash commands globally.", len(synced))
        except Exception as e:
            log.error("Failed syncing Geekers slash commands: %s", e)

    async def close(self) -> None:
        if self.expresso_scheduler:
            self.expresso_scheduler.stop()
        if contexto_bot.daily_game_loop.is_running():
            contexto_bot.daily_game_loop.cancel()
        if contexto_bot.http_session and not contexto_bot.http_session.closed:
            await contexto_bot.http_session.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info("🎮 Geekers Unified Bot online as %s (ID: %s)", self.user, self.user.id)
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Daily Games | /geekers or g!menu",
        )
        await self.change_presence(activity=activity)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        # Always evaluate prefix commands first
        ctx = await self.get_context(message)
        if ctx.valid:
            await self.invoke(ctx)
            return

        channel_id = message.channel.id
        content = message.content.strip()

        # 1. Expresso Auto-Guessing: active game in this channel
        if channel_id in expresso_sessions:
            e_session = expresso_sessions[channel_id]
            if not e_session.solved and not e_session.given_up and len(content) >= 2 and not content.startswith("/"):
                feedback = e_session.make_guess(content)
                await handle_expresso_guess(message.channel, message.author, e_session, feedback)
                return

        # 2. Contexto Auto-Guessing: active game in this channel
        if channel_id in contexto_bot.sessions:
            c_session = contexto_bot.sessions[channel_id]
            if not c_session.solved and not c_session.given_up and content.isalpha() and " " not in content:
                word = content.lower()
                existing = c_session.already_guessed(word)
                if existing:
                    await message.reply(
                        embed=make_guess_embed(
                            existing.word, existing.rank,
                            c_session.guess_count(), c_session.game_id, is_repeat=True,
                        ),
                        mention_author=False,
                    )
                    return

                try:
                    rank = await fetch_rank(contexto_bot.http_session, c_session.game_id, word)
                except Exception as e:
                    log.warning("Contexto fetch rank error: %s", e)
                    return

                if rank is None:
                    await message.reply("❌ Unknown word. Try another guess!", mention_author=False)
                    return

                c_session.add_guess(word, rank)
                if rank == 0:
                    c_session.solved = True

                await message.reply(
                    embed=make_guess_embed(word, rank, c_session.guess_count(), c_session.game_id),
                    mention_author=False,
                )
                return


bot = GeekersBot()


# ---------------------------------------------------------------------------
# Unified /geekers Command & Interactive Hub
# ---------------------------------------------------------------------------

@bot.tree.command(name="geekers", description="Open the Geekers Game Hub to select games and view personalized stats")
async def slash_geekers(interaction: discord.Interaction):
    guild_id = interaction.guild_id or 0
    view = GeekersHubView(interaction.user, guild_id, interaction.channel_id, expresso_storage, expresso_sessions)
    embed = view.render_embed()
    await interaction.response.send_message(embed=embed, view=view)


@bot.command(name="geekers", aliases=["menu", "hub", "games", "play"])
async def prefix_geekers(ctx: commands.Context):
    guild_id = ctx.guild.id if ctx.guild else 0
    view = GeekersHubView(ctx.author, guild_id, ctx.channel.id, expresso_storage, expresso_sessions)
    embed = view.render_embed()
    await ctx.send(embed=embed, view=view)


# ---------------------------------------------------------------------------
# Mirror Contexto Prefix Commands onto Unified Bot
# ---------------------------------------------------------------------------

@bot.command(name="cstart", aliases=["c!start"])
async def unified_cstart(ctx: commands.Context, game: Optional[int] = None):
    # Delegate to Contexto's prefix start
    from bots.contexto.bot import prefix_start
    await prefix_start(ctx, game)


@bot.command(name="chint", aliases=["c!hint"])
async def unified_chint(ctx: commands.Context):
    from bots.contexto.bot import prefix_hint
    await prefix_hint(ctx)


@bot.command(name="cguesses", aliases=["c!guesses"])
async def unified_cguesses(ctx: commands.Context):
    from bots.contexto.bot import prefix_guesses
    await prefix_guesses(ctx)


@bot.command(name="cgiveup", aliases=["c!giveup"])
async def unified_cgiveup(ctx: commands.Context):
    from bots.contexto.bot import prefix_giveup
    await prefix_giveup(ctx)


@bot.command(name="chelp", aliases=["c!help"])
async def unified_chelp(ctx: commands.Context):
    from bots.contexto.bot import prefix_help
    await prefix_help(ctx)


# ---------------------------------------------------------------------------
# Mirror Expresso Prefix Commands onto Unified Bot
# ---------------------------------------------------------------------------

@bot.command(name="estart", aliases=["e!start"])
async def unified_estart(ctx: commands.Context, game: Optional[int] = None):
    from bots.expresso.bot import prefix_start
    await prefix_start(ctx, game)


@bot.command(name="echart", aliases=["e!chart", "chart"])
async def unified_echart(ctx: commands.Context):
    from bots.expresso.bot import prefix_chart
    await prefix_chart(ctx)


@bot.command(name="ecompare", aliases=["e!compare", "compare"])
async def unified_ecompare(ctx: commands.Context, friend: discord.Member):
    from bots.expresso.bot import prefix_compare
    await prefix_compare(ctx, friend)


@bot.command(name="ehint", aliases=["e!hint"])
async def unified_ehint(ctx: commands.Context):
    from bots.expresso.bot import prefix_hint
    await prefix_hint(ctx)


@bot.command(name="egiveup", aliases=["e!giveup"])
async def unified_egiveup(ctx: commands.Context):
    from bots.expresso.bot import prefix_giveup
    await prefix_giveup(ctx)


@bot.command(name="ehelp", aliases=["e!help"])
async def unified_ehelp(ctx: commands.Context):
    from bots.expresso.bot import prefix_help
    await prefix_help(ctx)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    if not TOKEN:
        log.error("DISCORD_TOKEN not found in environment or .env! Create a .env file with DISCORD_TOKEN=your_token")
        raise SystemExit(1)
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()

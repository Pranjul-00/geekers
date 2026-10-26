"""Geekers Unified Game Hub.

Provides a unified `/geekers` command with an interactive personalized dropdown menu
allowing players to select games, view their stats, and launch daily puzzles.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from bots.expresso.charts import generate_daily_comparison_embed
from bots.expresso.game import ExpressoCatalog, ExpressoSession
from bots.expresso.storage import ExpressoStorage, PlayerResult, PlayerStats

log = logging.getLogger("geekers-hub")


class GameSelectionDropdown(discord.ui.Select):
    def __init__(self, user: discord.User | discord.Member, guild_id: int, channel_id: int, storage: ExpressoStorage, expresso_sessions: dict):
        self.target_user = user
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.storage = storage
        self.expresso_sessions = expresso_sessions

        # Personalized status check for Expresso
        today_expresso = ExpressoCatalog.get_today()
        results = storage.get_channel_daily_results(channel_id, today_expresso.game_id)
        user_result = next((r for r in results if r.user_id == user.id), None)
        if user_result:
            if user_result.solved:
                expresso_status = f"✅ Solved ({user_result.guesses_count} guesses)"
            else:
                expresso_status = f"❌ Surrendered ({user_result.guesses_count} guesses)"
        elif channel_id in expresso_sessions and not expresso_sessions[channel_id].solved:
            expresso_status = "⏳ In Progress in channel"
        else:
            expresso_status = "⚪ Not played today"

        # Check Contexto session status in channel
        try:
            from bots.contexto.bot import bot as contexto_bot, get_todays_game_id
            c_today_id = get_todays_game_id()
            c_session = contexto_bot.sessions.get(channel_id)
            if c_session:
                if c_session.solved:
                    contexto_status = f"✅ Solved Game #{c_session.game_id}"
                elif c_session.given_up:
                    contexto_status = f"❌ Surrendered Game #{c_session.game_id}"
                else:
                    contexto_status = f"⏳ Game #{c_session.game_id} in progress"
            else:
                contexto_status = f"⚪ Game #{c_today_id} ready to play"
        except Exception:
            contexto_status = "Active · c!start or /start"

        options = [
            discord.SelectOption(
                label=f"☕ Expresso (Daily #{today_expresso.game_id})",
                value="expresso",
                description=f"Status: {expresso_status[:40]}",
                default=True,
            ),
            discord.SelectOption(
                label="🧠 Contexto (Proximity Guesser)",
                value="contexto",
                description=f"Status: {contexto_status[:40]}",
            ),
            discord.SelectOption(
                label="🟩 Wordle (5-Letter Daily)",
                value="wordle",
                description="Status: In Integration",
            ),
            discord.SelectOption(
                label="🔗 Conexo (4x4 Grouping)",
                value="conexo",
                description="Status: Planned",
            ),
            discord.SelectOption(
                label="🔤 Letresso (Letter Placement)",
                value="letresso",
                description="Status: Planned",
            ),
        ]
        super().__init__(
            placeholder="Choose a game to inspect stats or play...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("This interactive menu was opened for someone else. Run `/geekers` to open your own!", ephemeral=True)
            return

        selected = self.values[0]
        # Update view's selected game
        if isinstance(self.view, GeekersHubView):
            self.view.current_game = selected
            embed = self.view.render_embed()
            await interaction.response.edit_message(embed=embed, view=self.view)


class PlayNowButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="▶️ Start Game", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view: GeekersHubView = self.view  # type: ignore
        if interaction.user.id != view.user.id:
            await interaction.response.send_message("Run `/geekers` to start your own session!", ephemeral=True)
            return

        if view.current_game == "expresso":
            channel_id = interaction.channel_id
            if channel_id in view.expresso_sessions and not view.expresso_sessions[channel_id].solved:
                session = view.expresso_sessions[channel_id]
                await interaction.response.send_message(
                    f"⚠️ An Expresso game is already active in this channel!\n**Current Board:**\n{session.get_masked_board()}\n*{session.get_word_lengths_info()}*\n\nType your guesses directly in chat!",
                )
                return

            puzzle = ExpressoCatalog.get_today()
            session = ExpressoSession(puzzle, channel_id, interaction.user.id)
            view.expresso_sessions[channel_id] = session

            embed = discord.Embed(
                title=f"☕ Expresso Daily #{puzzle.game_id} Started!",
                description=(
                    f"**Category:** {puzzle.category}\n"
                    f"**Words:** {len(puzzle.phrase.split())} words\n\n"
                    f"**Current Board:**\n{session.get_masked_board()}\n"
                    f"*{session.get_word_lengths_info()}*\n\n"
                    "💡 **Simply type guesses directly in chat!**\n"
                    "Or use `e!hint` or `e!giveup` if stumped."
                ),
                color=discord.Color.from_rgb(212, 143, 56),
            )
            await interaction.response.send_message(embed=embed)

        elif view.current_game == "contexto":
            from bots.contexto.bot import bot as contexto_bot, get_todays_game_id, make_start_embed, GameSession
            channel_id = interaction.channel_id
            if channel_id in contexto_bot.sessions and not contexto_bot.sessions[channel_id].solved:
                session = contexto_bot.sessions[channel_id]
                best = session.best_guess()
                best_str = f"Best guess: `{best.word}` (Rank #{best.rank})" if best else "No guesses yet"
                await interaction.response.send_message(
                    f"⚠️ A Contexto game (#{session.game_id}) is already active in this channel!\n{best_str}\n\nType any word in chat to submit a guess!",
                )
                return

            game_id = get_todays_game_id()
            session = GameSession(game_id=game_id, channel_id=channel_id, started_by=interaction.user.id)
            contexto_bot.sessions[channel_id] = session
            embed = make_start_embed(game_id)
            await interaction.response.send_message(embed=embed)

        else:
            await interaction.response.send_message(
                f"ℹ️ **{view.current_game.title()}** is currently in development and will be playable soon!",
                ephemeral=True,
            )


class ViewChartButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="📊 Group Standings", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view: GeekersHubView = self.view  # type: ignore
        if view.current_game == "expresso":
            puzzle = ExpressoCatalog.get_today()
            results = view.storage.get_channel_daily_results(interaction.channel_id, puzzle.game_id)
            embed = generate_daily_comparison_embed(puzzle.game_id, results)
            await interaction.response.send_message(embed=embed)
        elif view.current_game == "contexto":
            from bots.contexto.bot import bot as contexto_bot, make_guesses_embed
            channel_id = interaction.channel_id
            session = contexto_bot.sessions.get(channel_id)
            if session and session.guesses:
                await interaction.response.send_message(embed=make_guesses_embed(session))
            else:
                await interaction.response.send_message(
                    "No active Contexto game or guesses in this channel yet! Click **▶️ Start Game** above.", ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"No standings yet for {view.current_game.title()}.", ephemeral=True
            )


class GeekersHubView(discord.ui.View):
    def __init__(
        self,
        user: discord.User | discord.Member,
        guild_id: int,
        channel_id: int,
        storage: ExpressoStorage,
        expresso_sessions: dict,
    ):
        super().__init__(timeout=180)
        self.user = user
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.storage = storage
        self.expresso_sessions = expresso_sessions
        self.current_game = "expresso"

        # Add dropdown and buttons
        self.add_item(GameSelectionDropdown(user, guild_id, channel_id, storage, expresso_sessions))
        self.add_item(PlayNowButton())
        self.add_item(ViewChartButton())

    def render_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Geekers Game Hub",
            description=f"Welcome, **{self.user.display_name}**! Choose a daily game below to see your stats and jump into today's challenge.",
            color=discord.Color.blurple(),
        )

        if self.current_game == "expresso":
            puzzle = ExpressoCatalog.get_today()
            stats = self.storage.get_player_stats(self.guild_id, self.user.id)
            results = self.storage.get_channel_daily_results(self.channel_id, puzzle.game_id)
            user_today = next((r for r in results if r.user_id == self.user.id), None)

            if user_today:
                if user_today.solved:
                    status_text = f"✅ **Completed!** Solved in **{user_today.guesses_count}** guesses ({user_today.solve_time_seconds}s)"
                else:
                    status_text = f"❌ **Surrendered** after {user_today.guesses_count} guesses"
            else:
                status_text = "⚪ **Not completed yet today.** Click **Start Game** below!"

            stats_text = (
                f"• **Games Played:** {stats.total_played if stats else 0}\n"
                f"• **Games Solved:** {stats.total_solved if stats else 0}\n"
                f"• **Current Streak:** {stats.current_streak if stats else 0} days 🔥\n"
                f"• **Avg Guesses:** {stats.avg_guesses if stats else 0.0}"
            )

            embed.add_field(
                name=f"☕ Expresso (Daily #{puzzle.game_id})",
                value=f"**Today's Status:** {status_text}\n\n**Your Personal Stats:**\n{stats_text}",
                inline=False,
            )
            embed.set_footer(text="Expresso: Uncover daily idioms and expressions with color-coded tile feedback.")

        elif self.current_game == "contexto":
            from bots.contexto.bot import bot as contexto_bot, get_todays_game_id
            today_id = get_todays_game_id()
            session = contexto_bot.sessions.get(self.channel_id)
            if session:
                best = session.best_guess()
                best_str = f"Best guess: `{best.word}` (Rank #{best.rank})" if best else "No guesses yet"
                channel_status = f"⏳ **Game #{session.game_id} in progress** ({session.guess_count()} guesses made · {best_str})"
            else:
                channel_status = f"⚪ **No game active.** Click **Start Game** to begin Game #{today_id}!"

            embed.add_field(
                name=f"🧠 Contexto (Daily #{today_id})",
                value=(
                    f"**Channel Status:** {channel_status}\n\n"
                    "**How It Works:** Find the secret word! The bot ranks every word by semantic closeness (1 = closest).\n\n"
                    "• **Start Game:** Click **Start Game** below or type `c!start`\n"
                    "• **Guessing:** Just type words directly in chat!\n"
                    "• **Help / Hints:** `c!hint`, `c!guesses`, `c!giveup`"
                ),
                inline=False,
            )
            embed.set_footer(text="Contexto: Word proximity guessing powered by unofficial Contexto API.")

        elif self.current_game == "wordle":
            embed.add_field(
                name="🟩 Wordle (Classic 5-Letter Word)",
                value="Guess the 5-letter word in 6 tries. Integration in progress!",
                inline=False,
            )
            embed.set_footer(text="Coming soon to Geekers.")

        elif self.current_game == "conexo":
            embed.add_field(
                name="🔗 Conexo (4x4 Grouping Puzzle)",
                value="Find 4 groups of 4 words that share a common connection without 4 strikes. In development!",
                inline=False,
            )
            embed.set_footer(text="Coming soon to Geekers.")

        elif self.current_game == "letresso":
            embed.add_field(
                name="🔤 Letresso (Letter Placement)",
                value="Daily letter placement and word creation game. In development!",
                inline=False,
            )
            embed.set_footer(text="Coming soon to Geekers.")

        return embed

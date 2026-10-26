"""Expresso Automated Reminders & Daily Broadcast Scheduler.

Sends new puzzle drops at midnight UTC and sends friendly evening nudges
to ensure the 5-6 friends don't let their daily streaks die.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Set

import discord
from discord.ext import tasks

from .game import ExpressoCatalog
from .storage import ExpressoStorage

if TYPE_CHECKING:
    from .bot import ExpressoBot

log = logging.getLogger("expresso-scheduler")


class ExpressoScheduler:
    def __init__(self, bot: discord.Client, storage: ExpressoStorage):
        self.bot = bot
        self.storage = storage
        self._last_announced_day: int = -1
        self._last_reminded_day: int = -1

    def start(self) -> None:
        if not self.check_schedule_loop.is_running():
            self.check_schedule_loop.start()
            log.info("Expresso scheduler loop started.")

    def stop(self) -> None:
        if self.check_schedule_loop.is_running():
            self.check_schedule_loop.cancel()
            log.info("Expresso scheduler loop stopped.")

    @tasks.loop(minutes=1)
    async def check_schedule_loop(self) -> None:
        now = datetime.now(timezone.utc)
        today_puzzle = ExpressoCatalog.get_today()
        today_id = today_puzzle.game_id

        # 1. Midnight UTC Puzzle Drop
        if now.hour == 0 and now.minute == 0 and self._last_announced_day != today_id:
            self._last_announced_day = today_id
            await self.broadcast_daily_puzzle(today_puzzle)

        # 2. Daily Afternoon/Evening Reminder (Default 20:00 UTC = 4h before midnight)
        if now.hour == 20 and now.minute == 0 and self._last_reminded_day != today_id:
            self._last_reminded_day = today_id
            await self.broadcast_evening_reminder(today_puzzle)

    @check_schedule_loop.before_loop
    async def before_loop(self) -> None:
        await self.bot.wait_until_ready()

    async def broadcast_daily_puzzle(self, puzzle) -> None:
        subscriptions = self.storage.get_subscriptions()
        embed = discord.Embed(
            title=f"☕ Fresh Expresso Daily #{puzzle.game_id} is Served!",
            description=(
                "A brand new phrase puzzle has dropped! 🌅\n\n"
                f"**Category**: {puzzle.category}\n"
                f"**Target Words**: {len(puzzle.phrase.split())} words\n\n"
                "Gather your friends and start guessing:\n"
                "`e!start` or `/expresso start`"
            ),
            color=discord.Color.from_rgb(186, 110, 48),
        )
        embed.set_footer(text="Who will claim today's Espresso Doppio MVP? 🏆")

        for channel_id, _, _ in subscriptions:
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    log.warning("Failed sending daily broadcast to %s: %s", channel_id, e)

    async def broadcast_evening_reminder(self, puzzle) -> None:
        subscriptions = self.storage.get_subscriptions()

        for channel_id, guild_id, _ in subscriptions:
            channel = self.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread)):
                continue

            results = self.storage.get_channel_daily_results(channel_id, puzzle.game_id)
            solved_user_ids = {r.user_id for r in results if r.solved}

            # Gather members in channel (filtering out bots)
            guild = self.bot.get_guild(guild_id)
            unsolved_pings: List[str] = []
            if guild:
                for member in channel.members:
                    if not member.bot and member.id not in solved_user_ids:
                        unsolved_pings.append(member.mention)

            embed = discord.Embed(
                title=f"⏰ Expresso Daily #{puzzle.game_id} — Last Call!",
                description=(
                    "Only **4 hours remaining** before the daily puzzle resets at midnight UTC! ⏳\n\n"
                    f"So far **{len(solved_user_ids)}** friend(s) have finished today's brew.\n"
                ),
                color=discord.Color.orange(),
            )

            if unsolved_pings:
                embed.description += (
                    "\n**Don't let your streak die!** 🔥\n"
                    + " ".join(unsolved_pings[:8])
                )
            else:
                embed.description += "\n🎉 **Incredible! All active friends have already solved today's puzzle!**"

            embed.set_footer(text="Check current standings with e!chart or /expresso chart")

            try:
                await channel.send(embed=embed)
            except Exception as e:
                log.warning("Failed sending evening reminder to %s: %s", channel_id, e)

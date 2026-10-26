"""Expresso Chart & Visualization Generator.

Generates side-by-side ASCII/Unicode bar charts, head-to-head friend comparisons,
and coffee-themed awards for Discord embeds.
"""

from __future__ import annotations

import discord
from typing import List, Optional, Tuple
from .storage import PlayerResult, PlayerStats


def make_bar(guesses: int, max_scale: int = 12, bar_len: int = 8) -> str:
    """Render a Unicode progress bar where fewer guesses give a fuller bar."""
    if guesses <= 0:
        return "▱" * bar_len
    # Inverse score: 1 guess = 100%, 12+ guesses = minimal bar
    ratio = max(0.1, 1.0 - ((guesses - 1) / max(max_scale, 1)))
    filled = int(round(ratio * bar_len))
    filled = max(1, min(bar_len, filled))
    return "▰" * filled + "▱" * (bar_len - filled)


def format_seconds(sec: int) -> str:
    m, s = divmod(sec, 60)
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def generate_daily_comparison_embed(
    game_id: int,
    results: List[PlayerResult],
    unsolved_members: Optional[List[str]] = None,
) -> discord.Embed:
    """Generate the side-by-side daily chart embed for the channel."""
    embed = discord.Embed(
        title=f"☕ Expresso Daily #{game_id} — Group Comparison",
        description="Daily standings for our caffeine crew!",
        color=discord.Color.from_rgb(212, 143, 56),  # Warm amber espresso color
    )

    if not results:
        embed.description = "No one has completed today's Expresso puzzle yet. Be the first to brew! ☕"
        return embed

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    lines = []

    mvp: Optional[PlayerResult] = None
    fastest: Optional[PlayerResult] = None
    max_guesses_player: Optional[PlayerResult] = None

    for i, res in enumerate(results):
        rank_icon = medals[i] if i < len(medals) else f"{i+1}."
        bar = make_bar(res.guesses_count)
        time_str = format_seconds(res.solve_time_seconds)
        hints_str = f" · 💡{res.hints_used}" if res.hints_used > 0 else ""

        if res.solved:
            status = f"{bar} **{res.guesses_count}** guesses ({time_str}{hints_str})"
            if mvp is None:
                mvp = res
            if fastest is None or res.solve_time_seconds < fastest.solve_time_seconds:
                fastest = res
            if max_guesses_player is None or res.guesses_count > max_guesses_player.guesses_count:
                max_guesses_player = res
        else:
            status = f"❌ Surrendered after {res.guesses_count} attempts"

        lines.append(f"{rank_icon} **{res.user_name}**\n   {status}")

    if unsolved_members:
        lines.append("\n**⏳ Still Brewing (Pending):**")
        for member_name in unsolved_members:
            lines.append(f"   ☕ {member_name}")

    embed.add_field(
        name="📊 Side-by-Side Standings",
        value="\n".join(lines),
        inline=False,
    )

    # Coffee Fun Awards
    awards = []
    if mvp and mvp.solved:
        awards.append(f"🏆 **Espresso Doppio (MVP)**: **{mvp.user_name}** ({mvp.guesses_count} guesses)")
    if fastest and fastest.solved and fastest != mvp:
        awards.append(f"⚡ **Speed Demon**: **{fastest.user_name}** ({format_seconds(fastest.solve_time_seconds)})")
    if max_guesses_player and max_guesses_player.guesses_count >= 8:
        awards.append(f"☕ **Decaf Struggle**: **{max_guesses_player.user_name}** ({max_guesses_player.guesses_count} guesses, but never gave up!)")

    if awards:
        embed.add_field(
            name="🎖️ Daily Superlatives",
            value="\n".join(awards),
            inline=False,
        )

    embed.set_footer(text="Play today's puzzle with e!start or /expresso start")
    return embed


def generate_head_to_head_embed(
    p1: PlayerStats,
    p2: PlayerStats,
) -> discord.Embed:
    """Generate a head-to-head comparison chart between two players."""
    embed = discord.Embed(
        title=f"⚔️ Head-to-Head: {p1.user_name} vs {p2.user_name}",
        description="Who holds the ultimate Expresso bragging rights?",
        color=discord.Color.gold(),
    )

    p1_winrate = round((p1.total_solved / max(1, p1.total_played)) * 100, 1)
    p2_winrate = round((p2.total_solved / max(1, p2.total_played)) * 100, 1)

    chart = (
        "```\n"
        f"Metric             {p1.user_name[:10]:<12} {p2.user_name[:10]:<12}\n"
        "────────────────────────────────────────────\n"
        f"Games Played       {p1.total_played:<12} {p2.total_played:<12}\n"
        f"Games Solved       {p1.total_solved:<12} {p2.total_solved:<12}\n"
        f"Win Rate           {f'{p1_winrate}%':<12} {f'{p2_winrate}%':<12}\n"
        f"Avg Guesses        {p1.avg_guesses:<12} {p2.avg_guesses:<12}\n"
        f"Current Streak     {f'{p1.current_streak} days':<12} {f'{p2.current_streak} days':<12}\n"
        f"Max Streak         {f'{p1.max_streak} days':<12} {f'{p2.max_streak} days':<12}\n"
        f"Fastest Solve      {format_seconds(p1.fastest_solve_seconds):<12} {format_seconds(p2.fastest_solve_seconds):<12}\n"
        "```"
    )

    embed.add_field(name="📈 Stat Breakdown", value=chart, inline=False)

    # Determine roast / verdict
    p1_score = (p1_winrate * 0.4) + (p1.current_streak * 10) - (p1.avg_guesses * 5)
    p2_score = (p2_winrate * 0.4) + (p2.current_streak * 10) - (p2.avg_guesses * 5)

    if p1_score > p2_score:
        verdict = f"☕ **{p1.user_name}** out-caffeinated **{p2.user_name}** with sharper guesses and consistent streaks!"
    elif p2_score > p1_score:
        verdict = f"☕ **{p2.user_name}** out-caffeinated **{p1.user_name}** with sharper guesses and consistent streaks!"
    else:
        verdict = f"☕ Perfect dead-heat! **{p1.user_name}** and **{p2.user_name}** are evenly matched espresso savants."

    embed.add_field(name="📢 The Verdict", value=verdict, inline=False)
    return embed

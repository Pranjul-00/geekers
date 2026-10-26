use std::collections::HashSet;
use std::sync::Arc;
use std::time::Duration;

use chrono::{NaiveDate, Utc};
use dashmap::DashMap;
use poise::serenity_prelude as serenity;
use poise::CreateReply;
use serde::{Deserialize, Serialize};
use serenity::all::{
    ChannelId, CreateEmbed, CreateEmbedFooter, CreateMessage, GatewayIntents, Message, UserId,
};
use tokio::sync::RwLock;
use tracing::{error, info, warn};

// ---------------------------------------------------------------------------
// Constants & Types
// ---------------------------------------------------------------------------

const CONTEXTO_API_BASE: &str = "https://api.contexto.me/machado/en/game";
const SUBSCRIPTIONS_FILE: &str = "subscriptions.json";

type Error = Box<dyn std::error::Error + Send + Sync>;
type Context<'a> = poise::Context<'a, Data, Error>;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GuessEntry {
    pub word: String,
    pub rank: i64,
}

#[derive(Debug, Clone)]
pub struct GameSession {
    pub game_id: u32,
    pub channel_id: ChannelId,
    pub started_by: UserId,
    pub started_at: chrono::DateTime<Utc>,
    pub guesses: Vec<GuessEntry>,
    pub solved: bool,
    pub given_up: bool,
}

impl GameSession {
    pub fn new(game_id: u32, channel_id: ChannelId, started_by: UserId) -> Self {
        Self {
            game_id,
            channel_id,
            started_by,
            started_at: Utc::now(),
            guesses: Vec::new(),
            solved: false,
            given_up: false,
        }
    }

    pub fn best_guess(&self) -> Option<&GuessEntry> {
        self.guesses.iter().min_by_key(|g| g.rank)
    }

    pub fn already_guessed(&self, word: &str) -> Option<&GuessEntry> {
        let word_lower = word.to_lowercase();
        self.guesses.iter().find(|g| g.word.eq_ignore_ascii_case(&word_lower))
    }

    pub fn guess_count(&self) -> usize {
        self.guesses.len()
    }

    pub fn sorted_guesses(&self) -> Vec<&GuessEntry> {
        let mut list: Vec<&GuessEntry> = self.guesses.iter().collect();
        list.sort_by_key(|g| g.rank);
        list
    }
}

#[derive(Debug, Clone)]
pub enum WordStatus {
    Rank(i64),
    TooCommon,
    UnknownWord,
    Error(String),
}

#[derive(Debug, Deserialize)]
struct ContextoApiResponse {
    distance: Option<i64>,
    #[serde(default)]
    _lemma: Option<String>,
    #[serde(default)]
    _word: Option<String>,
    error: Option<String>,
}

#[derive(Clone)]
pub struct Data {
    pub sessions: Arc<DashMap<ChannelId, GameSession>>,
    pub word_cache: Arc<DashMap<(u32, String), WordStatus>>,
    pub subscriptions: Arc<RwLock<HashSet<ChannelId>>>,
    pub http_client: reqwest::Client,
    pub prefix: String,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

pub fn get_todays_game_id() -> u32 {
    let epoch = NaiveDate::from_ymd_opt(2022, 9, 18).unwrap();
    let today = Utc::now().date_naive();
    let diff = today.signed_duration_since(epoch).num_days();
    diff.max(1) as u32
}

pub async fn load_subscriptions() -> HashSet<ChannelId> {
    if let Ok(data) = tokio::fs::read_to_string(SUBSCRIPTIONS_FILE).await {
        if let Ok(ids) = serde_json::from_str::<Vec<u64>>(&data) {
            return ids.into_iter().map(ChannelId::new).collect();
        }
    }
    HashSet::new()
}

pub async fn save_subscriptions(subs: &HashSet<ChannelId>) {
    let ids: Vec<u64> = subs.iter().map(|id| id.get()).collect();
    if let Ok(json) = serde_json::to_string_pretty(&ids) {
        let _ = tokio::fs::write(SUBSCRIPTIONS_FILE, json).await;
    }
}

pub fn rank_info(rank: i64) -> (&'static str, &'static str, u32) {
    if rank == 0 {
        ("🏆", "Secret Word Found!", 0xF1C40F) // Gold
    } else if rank <= 500 {
        ("🟩", "Very close!", 0x2ECC71) // Green
    } else if rank <= 1500 {
        ("🟨", "Getting warmer...", 0xF39C12) // Yellow
    } else if rank <= 3000 {
        ("🟧", "Still pretty far...", 0xE67E22) // Orange
    } else {
        ("🟥", "Ice cold!", 0xE74C3C) // Red
    }
}

pub async fn fetch_word_rank(
    client: &reqwest::Client,
    cache: &DashMap<(u32, String), WordStatus>,
    game_id: u32,
    word: &str,
) -> WordStatus {
    let clean_word = word.trim().to_lowercase();
    let key = (game_id, clean_word.clone());

    if let Some(cached) = cache.get(&key) {
        return cached.clone();
    }

    let url = format!("{}/{}/{}", CONTEXTO_API_BASE, game_id, clean_word);
    let resp = match client.get(&url).send().await {
        Ok(r) => r,
        Err(e) => return WordStatus::Error(e.to_string()),
    };

    if resp.status().as_u16() == 404 {
        let status = WordStatus::UnknownWord;
        cache.insert(key, status.clone());
        return status;
    }

    let parsed: ContextoApiResponse = match resp.json().await {
        Ok(p) => p,
        Err(e) => return WordStatus::Error(e.to_string()),
    };

    let status = if let Some(dist) = parsed.distance {
        WordStatus::Rank(dist)
    } else if let Some(err) = parsed.error {
        let err_lower = err.to_lowercase();
        if err_lower.contains("too common") {
            WordStatus::TooCommon
        } else {
            WordStatus::UnknownWord
        }
    } else {
        WordStatus::UnknownWord
    };

    cache.insert(key, status.clone());
    status
}

pub async fn verify_game_exists(
    client: &reqwest::Client,
    cache: &DashMap<(u32, String), WordStatus>,
    game_id: u32,
) -> bool {
    matches!(fetch_word_rank(client, cache, game_id, "water").await, WordStatus::Rank(_))
}

// ---------------------------------------------------------------------------
// Embed Generators
// ---------------------------------------------------------------------------

pub fn make_start_embed(game_id: u32, is_daily: bool, prefix: &str) -> CreateEmbed {
    let title_prefix = if is_daily {
        format!("🗓️ Today's Game — #{}", game_id)
    } else {
        format!("📂 Historical Game — #{}", game_id)
    };

    CreateEmbed::new()
        .title(format!("🧠 Contexto — {}", title_prefix))
        .description(format!(
            "A secret word has been chosen! Try to guess it.\n\n\
            Words are ranked by **semantic similarity** to the secret word.\n\
            **Rank #0 = Secret Word!** 🏆\n\n\
            💡 **How to play:** Just type any word in chat! No command needed.\n\n\
            **Rank color guide:**\n\
            🟩 Top 500 — Very close!\n\
            🟨 Top 1,500 — Getting warmer...\n\
            🟧 Top 3,000 — Still pretty far...\n\
            🟥 3,000+ — Ice cold!\n\n\
            Commands: `{p}hint`, `{p}guesses`, `{p}giveup`",
            p = prefix
        ))
        .color(0x3498DB)
        .field("Game #", game_id.to_string(), true)
        .footer(CreateEmbedFooter::new("Synced with contexto.me • Good luck!"))
}

pub fn make_guess_embed(
    word: &str,
    rank: i64,
    guess_count: usize,
    game_id: u32,
    is_repeat: bool,
) -> CreateEmbed {
    if rank == 0 {
        // WINNER EMBED!
        return CreateEmbed::new()
            .title("🎉 YOU FOUND THE SECRET WORD!")
            .description(format!(
                "**`{}`** is the secret word for **Game #{}**!\n\n\
                🏆 **Congratulations, you solved the puzzle!**",
                word, game_id
            ))
            .color(0xF1C40F) // Vibrant Gold
            .field("Guesses Taken", guess_count.to_string(), true)
            .field("Rank", "#0 (Winner!)", true)
            .footer(CreateEmbedFooter::new(format!(
                "Contexto Game #{} • Solved in {} guesses",
                game_id, guess_count
            )));
    }

    let (emoji, label, color) = rank_info(rank);
    let repeat_tag = if is_repeat { " *(already guessed)*" } else { "" };

    CreateEmbed::new()
        .title(format!("{} `{}`{}", emoji, word, repeat_tag))
        .color(color)
        .field("Rank", format!("#{}", rank), true)
        .field("Status", label, true)
        .field("Total Guesses", guess_count.to_string(), true)
        .footer(CreateEmbedFooter::new(format!("Contexto Game #{}", game_id)))
}

pub fn make_hint_embed(session: &GameSession) -> CreateEmbed {
    let best = match session.best_guess() {
        Some(b) => b,
        None => {
            return CreateEmbed::new()
                .title("💡 Hint")
                .description("No guesses yet! Type any word in chat to start guessing.")
                .color(0x3498DB)
        }
    };

    let (emoji, label, color) = rank_info(best.rank);
    CreateEmbed::new()
        .title("💡 Your Closest Guess So Far")
        .color(color)
        .field("Word", format!("`{}`", best.word), true)
        .field("Rank", format!("#{} {}", best.rank, emoji), true)
        .field("Status", label, true)
        .field("Total Guesses", session.guess_count().to_string(), false)
        .footer(CreateEmbedFooter::new(format!("Contexto Game #{}", session.game_id)))
}

pub fn make_guesses_embed(session: &GameSession) -> CreateEmbed {
    let sorted = session.sorted_guesses();
    if sorted.is_empty() {
        return CreateEmbed::new()
            .title("📋 Your Guesses")
            .description("No guesses yet! Just type a word in chat to begin.")
            .color(0x3498DB);
    }

    let mut lines = Vec::new();
    for (i, entry) in sorted.iter().take(25).enumerate() {
        let (emoji, _, _) = rank_info(entry.rank);
        lines.push(format!("`{:>2}.` {} **{}** — #{}", i + 1, emoji, entry.word, entry.rank));
    }

    let remaining = sorted.len().saturating_sub(25);
    let mut desc = lines.join("\n");
    if remaining > 0 {
        desc.push_str(&format!("\n*... and {} more guesses*", remaining));
    }

    CreateEmbed::new()
        .title(format!("📋 Guesses for Game #{}", session.game_id))
        .description(desc)
        .color(0x3498DB)
        .footer(CreateEmbedFooter::new(format!("{} total guesses", sorted.len())))
}

pub fn make_giveup_embed(session: &GameSession) -> CreateEmbed {
    let mut embed = CreateEmbed::new()
        .title("🏳️ Game Over — You Gave Up")
        .description(
            "The game has ended! The secret word can be checked at **[contexto.me](https://contexto.me)**.\n\n\
            Use `/start` or `c!start` to begin a new puzzle anytime!",
        )
        .color(0x7F8C8D)
        .field("Game #", session.game_id.to_string(), true)
        .field("Total Guesses", session.guess_count().to_string(), true);

    if let Some(best) = session.best_guess() {
        let (emoji, _, _) = rank_info(best.rank);
        embed = embed.field(
            "Your Best Guess",
            format!("`{}` — #{} {}", best.word, best.rank, emoji),
            false,
        );
    }

    embed
}

pub fn make_daily_announce_embed(game_id: u32, prefix: &str) -> CreateEmbed {
    CreateEmbed::new()
        .title("🌅 New Daily Contexto Puzzle Live!")
        .description(format!(
            "Today's **Game #{}** is now available!\n\n\
            Type `{p}start` or `/start` to start playing.\n\
            Once started, just type your word guesses directly in chat!",
            game_id,
            p = prefix
        ))
        .color(0x9B59B6)
        .footer(CreateEmbedFooter::new("contexto.me • Daily word puzzle"))
}

// ---------------------------------------------------------------------------
// Commands (Dual Slash + Prefix)
// ---------------------------------------------------------------------------

#[poise::command(slash_command, prefix_command, aliases("play", "begin"))]
pub async fn start(
    ctx: Context<'_>,
    #[description = "Game number to play (leave blank for today's daily game)"] game: Option<u32>,
) -> Result<(), Error> {
    let channel_id = ctx.channel_id();
    let max_id = get_todays_game_id();

    let (game_id, is_daily) = match game {
        Some(g) => {
            if g < 1 || g > max_id {
                ctx.send(
                    CreateReply::default()
                        .content(format!("❌ Invalid game number. Please choose between **1** and **{}**.", max_id))
                        .ephemeral(true),
                )
                .await?;
                return Ok(());
            }
            (g, false)
        }
        None => (max_id, true),
    };

    // Check if game already running
    if let Some(existing) = ctx.data().sessions.get(&channel_id) {
        if !existing.solved && !existing.given_up {
            ctx.send(
                CreateReply::default()
                    .content(format!(
                        "⚠️ A game is already in progress in this channel! (Game #{})\n\
                        Just type words to guess, or use `{}giveup` to end it.",
                        existing.game_id, ctx.data().prefix
                    ))
                    .ephemeral(true),
            )
            .await?;
            return Ok(());
        }
    }

    ctx.defer().await?;

    if !is_daily && !verify_game_exists(&ctx.data().http_client, &ctx.data().word_cache, game_id).await {
        ctx.send(
            CreateReply::default()
                .content(format!("❌ Game #{} does not seem to exist on Contexto yet.", game_id))
                .ephemeral(true),
        )
        .await?;
        return Ok(());
    }

    let session = GameSession::new(game_id, channel_id, ctx.author().id);
    ctx.data().sessions.insert(channel_id, session);
    info!("Started game #{} in channel {}", game_id, channel_id);

    let embed = make_start_embed(game_id, is_daily, &ctx.data().prefix);
    ctx.send(CreateReply::default().embed(embed)).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command)]
pub async fn guess(
    ctx: Context<'_>,
    #[description = "The word to guess"] word: String,
) -> Result<(), Error> {
    let channel_id = ctx.channel_id();
    let mut session = match ctx.data().sessions.get_mut(&channel_id) {
        Some(s) => s,
        None => {
            ctx.send(
                CreateReply::default()
                    .content(format!("❌ No active game! Start one with `{}start` or `/start`.", ctx.data().prefix))
                    .ephemeral(true),
            )
            .await?;
            return Ok(());
        }
    };

    if session.solved {
        ctx.send(CreateReply::default().content("✅ This game was already solved! Start a new one with `/start`.").ephemeral(true)).await?;
        return Ok(());
    }
    if session.given_up {
        ctx.send(CreateReply::default().content("🏳️ This game ended! Start a new one with `/start`.").ephemeral(true)).await?;
        return Ok(());
    }

    let clean_word = word.trim().to_lowercase();
    if !clean_word.chars().all(|c| c.is_ascii_alphabetic()) {
        ctx.send(CreateReply::default().content("❌ Please guess a single word containing only letters.").ephemeral(true)).await?;
        return Ok(());
    }

    // Check repeat
    if let Some(existing) = session.already_guessed(&clean_word) {
        let embed = make_guess_embed(&existing.word, existing.rank, session.guess_count(), session.game_id, true);
        ctx.send(CreateReply::default().embed(embed)).await?;
        return Ok(());
    }

    ctx.defer().await?;

    let status = fetch_word_rank(&ctx.data().http_client, &ctx.data().word_cache, session.game_id, &clean_word).await;
    match status {
        WordStatus::Rank(rank) => {
            session.guesses.push(GuessEntry {
                word: clean_word.clone(),
                rank,
            });
            if rank == 0 {
                session.solved = true;
            }
            let embed = make_guess_embed(&clean_word, rank, session.guess_count(), session.game_id, false);
            ctx.send(CreateReply::default().embed(embed)).await?;
        }
        WordStatus::TooCommon => {
            ctx.send(CreateReply::default().content(format!("⚠️ **`{}`** doesn't count (it is too common) — try another word!", clean_word))).await?;
        }
        WordStatus::UnknownWord => {
            ctx.send(CreateReply::default().content(format!("❓ **`{}`** isn't in Contexto's vocabulary — try another word!", clean_word))).await?;
        }
        WordStatus::Error(e) => {
            error!("API error for word {}: {}", clean_word, e);
            ctx.send(CreateReply::default().content("⚠️ Failed to check word against Contexto API. Please try again.")).await?;
        }
    }

    Ok(())
}

#[poise::command(slash_command, prefix_command)]
pub async fn hint(ctx: Context<'_>) -> Result<(), Error> {
    let channel_id = ctx.channel_id();
    match ctx.data().sessions.get(&channel_id) {
        Some(s) => {
            let embed = make_hint_embed(&s);
            ctx.send(CreateReply::default().embed(embed)).await?;
        }
        None => {
            ctx.send(
                CreateReply::default()
                    .content(format!("❌ No active game! Start one with `{}start`.", ctx.data().prefix))
                    .ephemeral(true),
            )
            .await?;
        }
    }
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("list", "history"))]
pub async fn guesses(ctx: Context<'_>) -> Result<(), Error> {
    let channel_id = ctx.channel_id();
    match ctx.data().sessions.get(&channel_id) {
        Some(s) => {
            let embed = make_guesses_embed(&s);
            ctx.send(CreateReply::default().embed(embed)).await?;
        }
        None => {
            ctx.send(
                CreateReply::default()
                    .content(format!("❌ No active game! Start one with `{}start`.", ctx.data().prefix))
                    .ephemeral(true),
            )
            .await?;
        }
    }
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("quit", "give_up"))]
pub async fn giveup(ctx: Context<'_>) -> Result<(), Error> {
    let channel_id = ctx.channel_id();
    let mut session = match ctx.data().sessions.get_mut(&channel_id) {
        Some(s) => s,
        None => {
            ctx.send(
                CreateReply::default()
                    .content(format!("❌ No active game! Start one with `{}start`.", ctx.data().prefix))
                    .ephemeral(true),
            )
            .await?;
            return Ok(());
        }
    };

    if session.solved || session.given_up {
        ctx.send(CreateReply::default().content("This game is already completed.").ephemeral(true)).await?;
        return Ok(());
    }

    session.given_up = true;
    let embed = make_giveup_embed(&session);
    ctx.send(CreateReply::default().embed(embed)).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command)]
pub async fn today(ctx: Context<'_>) -> Result<(), Error> {
    let game_id = get_todays_game_id();
    let today_date = Utc::now().date_naive();
    let channel_id = ctx.channel_id();

    let mut embed = CreateEmbed::new()
        .title("🗓️ Today's Contexto Information")
        .color(0x3498DB)
        .field("Game #", game_id.to_string(), true)
        .field("Date (UTC)", today_date.to_string(), true);

    if let Some(session) = ctx.data().sessions.get(&channel_id) {
        let status = if session.solved {
            "✅ Solved!"
        } else if session.given_up {
            "🏳️ Ended"
        } else {
            "🎮 In Progress"
        };
        embed = embed.field(
            "This Channel",
            format!("Game #{} — {} ({} guesses)", session.game_id, status, session.guess_count()),
            false,
        );
    } else {
        embed = embed.field(
            "This Channel",
            format!("No active game. Use `{}start` or `/start` to begin!", ctx.data().prefix),
            false,
        );
    }

    ctx.send(CreateReply::default().embed(embed)).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command, required_permissions = "MANAGE_CHANNELS")]
pub async fn subscribe(ctx: Context<'_>) -> Result<(), Error> {
    let channel_id = ctx.channel_id();
    let mut subs = ctx.data().subscriptions.write().await;
    if subs.contains(&channel_id) {
        ctx.send(CreateReply::default().content("✅ This channel is already subscribed to daily Contexto games.").ephemeral(true)).await?;
        return Ok(());
    }

    subs.insert(channel_id);
    save_subscriptions(&subs).await;
    info!("Subscribed channel {} to daily games", channel_id);

    ctx.send(CreateReply::default().content(
        "🔔 **Subscribed!** This channel will automatically receive new daily Contexto games at midnight UTC!\n\
        Use `unsubscribe` to disable anytime."
    )).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command, required_permissions = "MANAGE_CHANNELS")]
pub async fn unsubscribe(ctx: Context<'_>) -> Result<(), Error> {
    let channel_id = ctx.channel_id();
    let mut subs = ctx.data().subscriptions.write().await;
    if !subs.remove(&channel_id) {
        ctx.send(CreateReply::default().content("❌ This channel is not subscribed to daily games.").ephemeral(true)).await?;
        return Ok(());
    }

    save_subscriptions(&subs).await;
    info!("Unsubscribed channel {}", channel_id);

    ctx.send(CreateReply::default().content("🔕 **Unsubscribed.** Daily announcements stopped for this channel.")).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("help", "commands"))]
pub async fn chelp(ctx: Context<'_>) -> Result<(), Error> {
    let p = &ctx.data().prefix;
    let embed = CreateEmbed::new()
        .title("🧠 Contexto Bot — Fast & Automatic")
        .description(format!(
            "**Dual Slash (`/`) and Prefix (`{p}`) Support**\n\n\
            💡 **Auto-Guessing Mode:** Once you start a game, **simply type any word directly in chat!**\n\
            No commands needed — the bot automatically ranks your word.\n\n\
            **Commands:**\n\
            • `{p}start [game]` / `/start` — Start today's game or choose a past game #\n\
            • `{p}guess <word>` / `/guess` — Submit a guess manually\n\
            • `{p}hint` / `/hint` — Show closest guess so far\n\
            • `{p}guesses` / `/guesses` — List all guesses sorted by closeness\n\
            • `{p}giveup` / `/giveup` — End the current game\n\
            • `{p}today` / `/today` — Check today's game number and channel status\n\
            • `{p}subscribe` / `/subscribe` — Receive new games automatically every 24h\n\
            • `{p}unsubscribe` / `/unsubscribe` — Stop daily announcements\n\n\
            **Color Ranks:**\n\
            🏆 Rank #0 — **Secret Word (Winner!)**\n\
            🟩 Top 500 — Very close!\n\
            🟨 Top 1,500 — Getting warmer...\n\
            🟧 Top 3,000 — Still pretty far...\n\
            🟥 3,000+ — Ice cold!"
        ))
        .color(0x3498DB);

    ctx.send(CreateReply::default().embed(embed)).await?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Event Handler (Auto-Guess in Chat)
// ---------------------------------------------------------------------------

async fn handle_auto_guess(
    ctx: &serenity::Context,
    data: &Data,
    msg: &Message,
) -> Result<(), Error> {
    if msg.author.bot {
        return Ok(());
    }

    let content = msg.content.trim();
    if content.starts_with(&data.prefix) || content.starts_with('/') {
        return Ok(());
    }

    // Must be a single alphabetical word
    if content.is_empty() || content.contains(' ') || !content.chars().all(|c| c.is_ascii_alphabetic()) {
        return Ok(());
    }

    // Check if channel has an active, unsolved game
    let mut session = match data.sessions.get_mut(&msg.channel_id) {
        Some(s) => s,
        None => return Ok(()),
    };

    if session.solved || session.given_up {
        return Ok(());
    }

    let word = content.to_lowercase();

    // Check duplicate
    if let Some(existing) = session.already_guessed(&word) {
        let embed = make_guess_embed(&existing.word, existing.rank, session.guess_count(), session.game_id, true);
        let _ = msg.channel_id.send_message(&ctx.http, CreateMessage::new().embed(embed).reference_message(msg)).await;
        return Ok(());
    }

    // Query API with shared cache
    let status = fetch_word_rank(&data.http_client, &data.word_cache, session.game_id, &word).await;
    match status {
        WordStatus::Rank(rank) => {
            session.guesses.push(GuessEntry {
                word: word.clone(),
                rank,
            });
            if rank == 0 {
                session.solved = true;
            }
            let embed = make_guess_embed(&word, rank, session.guess_count(), session.game_id, false);
            let _ = msg.channel_id.send_message(&ctx.http, CreateMessage::new().embed(embed).reference_message(msg)).await;
        }
        WordStatus::TooCommon => {
            let _ = msg.channel_id.send_message(
                &ctx.http,
                CreateMessage::new()
                    .content(format!("⚠️ **`{}`** doesn't count (too common) — try another word!", word))
                    .reference_message(msg),
            ).await;
        }
        WordStatus::UnknownWord => {
            let _ = msg.channel_id.send_message(
                &ctx.http,
                CreateMessage::new()
                    .content(format!("❓ **`{}`** isn't in Contexto's vocabulary — try another word!", word))
                    .reference_message(msg),
            ).await;
        }
        WordStatus::Error(e) => {
            warn!("Error checking word {}: {}", word, e);
        }
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// 24-Hour Daily Announcement Task
// ---------------------------------------------------------------------------

fn on_event<'a>(
    framework: poise::FrameworkContext<'a, Data, Error>,
    event: &'a serenity::FullEvent,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), Error>> + Send + 'a>> {
    Box::pin(async move {
        if let serenity::FullEvent::Message { new_message } = event {
            let data = framework.user_data().await;
            let _ = handle_auto_guess(framework.serenity_context, data, new_message).await;
        }
        Ok(())
    })
}

fn spawn_daily_announcer(
    http: Arc<serenity::Http>,
    data: Data,
) {
    tokio::spawn(async move {
        let mut last_announced = get_todays_game_id();
        info!("Daily loop active. Current Game #{}", last_announced);

        loop {
            tokio::time::sleep(Duration::from_secs(60)).await;
            let current_id = get_todays_game_id();
            if current_id <= last_announced {
                continue;
            }

            info!("New day detected! Announcing Game #{}", current_id);
            last_announced = current_id;

            // Clear expired daily sessions
            data.sessions.retain(|_, s| !s.solved && s.game_id == current_id);

            let subs = data.subscriptions.read().await.clone();
            let embed = make_daily_announce_embed(current_id, &data.prefix);

            let mut dead_channels = Vec::new();
            for channel_id in subs {
                let msg = CreateMessage::new().embed(embed.clone());
                if let Err(e) = channel_id.send_message(&http, msg).await {
                    warn!("Failed to announce to channel {}: {}", channel_id, e);
                    dead_channels.push(channel_id);
                }
            }

            if !dead_channels.is_empty() {
                let mut subs_write = data.subscriptions.write().await;
                for dead in dead_channels {
                    subs_write.remove(&dead);
                }
                save_subscriptions(&subs_write).await;
            }
        }
    });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() -> Result<(), Error> {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "contexto_bot=info,serenity=warn,poise=warn".into()),
        )
        .init();

    let token = std::env::var("DISCORD_TOKEN").expect("Expected DISCORD_TOKEN in environment or .env");
    let prefix = std::env::var("COMMAND_PREFIX").unwrap_or_else(|_| "c!".to_string());

    let initial_subscriptions = load_subscriptions().await;
    let http_client = reqwest::Client::builder()
        .user_agent("ContextoDiscordBot/2.0 (Rust)")
        .pool_idle_timeout(Duration::from_secs(90))
        .tcp_keepalive(Duration::from_secs(60))
        .build()?;

    let data = Data {
        sessions: Arc::new(DashMap::new()),
        word_cache: Arc::new(DashMap::new()),
        subscriptions: Arc::new(RwLock::new(initial_subscriptions)),
        http_client,
        prefix: prefix.clone(),
    };

    let data_for_setup = data.clone();

    let options = poise::FrameworkOptions {
        commands: vec![
            start(),
            guess(),
            hint(),
            guesses(),
            giveup(),
            today(),
            subscribe(),
            unsubscribe(),
            chelp(),
        ],
        prefix_options: poise::PrefixFrameworkOptions {
            prefix: Some(prefix.clone().into()),
            edit_tracker: None,
            ..Default::default()
        },
        event_handler: on_event,
        ..Default::default()
    };

    let framework = poise::Framework::builder()
        .options(options)
        .setup(move |ctx, ready, framework| {
            let data = data_for_setup.clone();
            Box::pin(async move {
                info!("Logged in as {} (ID: {})", ready.user.tag(), ready.user.id);
                ctx.set_activity(Some(serenity::ActivityData::playing(format!(
                    "Contexto | {}start or /start",
                    data.prefix
                ))));

                info!("Registering slash commands globally...");
                poise::builtins::register_globally(ctx, &framework.options().commands).await?;
                info!("Slash commands successfully registered!");

                spawn_daily_announcer(Arc::clone(&ctx.http), data.clone());

                Ok(data)
            })
        })
        .build();

    let intents = GatewayIntents::non_privileged() | GatewayIntents::MESSAGE_CONTENT;

    let mut client = serenity::ClientBuilder::new(token, intents)
        .framework(framework)
        .await?;

    info!("Starting Contexto Bot (Rust engine)...");
    client.start().await?;

    Ok(())
}

# Error & Edge Case Debugging Ledger

## Debugging Ledger & Defensive Patterns

### Issue 1: Discord 10062 (Unknown / Expired Interaction)
- **Symptom**: Calling `interaction.response.send_message()` on an interaction that took > 3 seconds fails with `discord.errors.NotFound: 10062 Unknown interaction`.
- **Root Cause**: Discord requires interactions to be acknowledged within 3000ms. External HTTP calls (like Contexto API rank checks) can introduce latency.
- **Guardrail**: Defer interactions promptly with `await interaction.response.defer(thinking=True)` for calls that touch external APIs or perform async I/O. Use `interaction.followup.send()` afterwards. In prefix commands, use `async with ctx.typing():`.

### Issue 2: External Game API Downtime / Non-200 Responses
- **Symptom**: `api.contexto.me` or target sites return 404, 502, or invalid JSON.
- **Root Cause**: Unofficial APIs may update routes, rate-limit, or encounter transient outages.
- **Guardrail**: Wrap external requests in `aiohttp.ClientResponseError` and JSON decode try/except blocks. Return friendly Discord messages (e.g., "⚠️ Could not reach Contexto servers. Please try again in a moment.") without crashing the bot process.

### Issue 3: Working Directory Dependency on File Paths
- **Symptom**: Running a bot via `uv run python -m bots.contexto.bot` from root created `subscriptions.json` in root, whereas running `cd bots/contexto && python bot.py` created it in the subfolder, causing split state.
- **Root Cause**: Hardcoded relative strings (`"subscriptions.json"`).
- **Guardrail**: Anchor all file paths relative to `Path(__file__).resolve().parent`.

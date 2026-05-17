# AGENTS.md

Notes for future Claude sessions working on boombot2. Read this before making changes.

## Project scope

A Discord bot for ~5 friends. It joins a voice channel on command, announces who joins, plays sound files, and TTS-speaks text. **Not a serious production service.** No tests, no CI, no scale concerns. Optimize for simplicity and the owner's ability to read/maintain the code casually. Prefer clear, conventional code over clever abstractions.

## Architecture decisions (don't relitigate without asking)

- **Slash commands only.** No `!!` prefix or message-command compatibility. Sync to a single guild via `DISCORD_GUILD_ID` for instant updates (global sync takes up to 1hr).
- **Sound files on disk.** Pushed manually via `rsync` or `scp`. Not in S3, not in git. `.mp3` only — the glob in `sounds.py` is intentional.
- **Aliases + per-user join sounds live in one JSON object in S3.** Keyed by Discord user ID (stable across username changes). Schema: `{user_id: {alias?: str, join_sound?: str}}`. Loaded once on startup, cached in memory, PUT on every mutation. No locking beyond an asyncio.Lock — 5 users, no concurrency concerns.
- **Anyone in the guild can edit any alias/sound.** Intentional, matches the friend-group vibe. Don't add permission checks.
- **Per-guild mode is in-memory only.** Resets on restart. Three modes: `default` (per-user sound if set, else TTS), `name` (always TTS), `sound` (always a sound — user's join_sound or fallback `boom.mp3`).
- **Trigger channel is matched by name, not ID.** `TRIGGER_CHANNEL_NAME` env var (default `boom-bot`). Keyword tokens in messages there play matching sound if bot is in voice. 3s per-guild cooldown.
- **Name precedence for TTS:** alias → server nickname → global display name → username.
- **`/leave` is the off switch.** All "make it stop" UX flows through disconnecting from voice. No mute toggles, no per-user opt-out.

## Stack

- Python 3.14 (pinned in `.python-version` and `pyproject.toml`).
- `uv` for env/deps. Package is non-installable (`[tool.uv] package = false` may or may not be set — current state has `[build-system] = hatchling` and builds a wheel; either is acceptable).
- `discord.py[voice]` 2.x with `app_commands` for slash commands.
- `gTTS` for text-to-speech (free, no API key, internet-dependent).
- `boto3` for S3.
- `python-dotenv` is **not** a dependency — `uv run` auto-loads `.env`, and systemd uses `EnvironmentFile=`.

## Layout

```
src/boombot/
  bot.py              entrypoint (asyncio.run + cog registration + slash sync)
  config.py           env → frozen dataclass
  logging_setup.py    rotating file (10MB × 5) + stdout
  aliases.py          S3-backed JSON, in-memory dict, asyncio.Lock
  sounds.py           SoundLibrary: glob *.mp3, lookup by stem
  tts.py              gTTS wrapper, returns temp file path
  state.py            ModeState (per-guild, in-memory)
  playback.py         play_file() helper — awaits previous playback, deletes temp file
  cogs/
    voice.py          /join /leave /mode /status + on_voice_state_update
    play.py           /play /sounds /say
    alias.py          /alias set|clear|list, /sound set|clear
    trigger.py        on_message keyword triggers
```

## Deploy target

- **Vultr VPS, Ubuntu 24.04, $5/mo tier (1GB RAM, 2GB swap).** systemd unit at `deploy/boombot.service`, full walkthrough in `deploy/README.md`.
- Runs as user `boombot`. Code in `/home/boombot/boombot2/`. Sounds in `./sounds/`, logs in `./logs/`, secrets in `./.env`.
- Updates flow: `rsync` from laptop → `uv sync` → `sudo systemctl restart boombot`. No git pull on the server (private code, no public repo).

## AWS scope

- Single IAM **user** (not role — VPS is outside AWS).
- Permissions: `s3:GetObject` + `s3:PutObject` on exactly `arn:aws:s3:::<bucket>/boombot/aliases.json`. No `ListBucket`, no `DeleteObject`. PUT overwrites in place; clearing all entries just PUTs `{}`.
- Credentials in `.env` as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. boto3 picks them up automatically.

## Discord setup gotchas

- **Privileged intents required:** `SERVER MEMBERS` and `MESSAGE CONTENT` must be toggled on in the developer portal. `PRESENCE` is not needed.
- Bot must be invited to the guild with scopes `bot` + `applications.commands` before slash sync will work (otherwise sync returns 403).
- Sound autocomplete is wired in `play.py` and `alias.py` — keep it working when adding sound-related commands.

## Things to NOT do

- Don't add tests, CI, type stubs, or Docker. Not the goal.
- Don't introduce a database. The S3 JSON is the database.
- Don't add per-user permission checks on alias/sound commands.
- Don't expand sound file format support without asking — the mp3-only choice is for predictability.
- Don't add features unprompted ("/random", "/queue", soundboards, voice recognition, etc.). Owner has explicitly opted for minimalism.
- Don't use `time.sleep` in async handlers (the old bot did this — it blocks the event loop). Use `asyncio.sleep` or chain via discord.py's `after=` callback (see `playback.py`).

## Where to look first

- New command? → relevant cog under `src/boombot/cogs/`.
- Audio bug? → `playback.py` (shared) or `voice.py` (`_announce`).
- S3 bug? → `aliases.py`.
- Config bug? → `config.py` + `.env.example`.
- Deploy issue? → `deploy/README.md`.

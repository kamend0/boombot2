# boombot2

A few years ago, I made a bot called boom-bot to make my friends laugh. One of 
those friends recently requested I bring it back from the dead. So here it is: 
the vibe-coded dopplegänger of that old bot. It's frankly a bit better, but the 
bar was not high.

Below is 98% vibe-written.

## Commands

- `/boomjoin` — join the caller's voice channel.
- `/boomkick` — disconnect from voice.
- `/play <sound>` — play a sound (or `any` for random).
- `/sounds` — list available sounds.
- `/say <text>` — speak text aloud.
- `/mode default|name|sound` — global override for this server's announcement style.
  - **default**: per-user join sound if set, else TTS name.
  - **name**: always TTS name.
  - **sound**: always play a sound (user's join sound, else `boom.mp3`).
- `/volume <0-200>` — set playback volume (percent) for everyone. Default 100.
- `/status` — show current mode, volume, and whether bot is in voice.
- `/alias set <alias> [user]` — set an alias (defaults to caller).
- `/alias clear [user]` — clear an alias.
- `/alias list` — show everyone's alias and join sound.
- `/sound set <sound> [user]` — set a per-user join sound.
- `/sound clear [user]` — clear it.

## Chat triggers

In the channel named by `TRIGGER_CHANNEL_NAME` (default `boom-bot`), any message containing a word that matches a sound filename will play that sound — *if* the bot is currently in a voice channel. 3-second cooldown per server.

## Name precedence (TTS)

Alias → server nickname → global display name → username.

## Discord setup

In the Developer Portal, enable the **Server Members** and **Message Content** privileged intents. Invite the bot with scopes `bot` + `applications.commands` and these permissions:

- View Channels
- Send Messages
- Read Message History (for chat triggers)
- Connect (voice)
- Speak (voice)
- Use Voice Activity

Here's the link with the above permissions:
`https://discord.com/oauth2/authorize?client_id=1505334133503819786&permissions=2184252416&integration_type=0&scope=bot+applications.commands`

## Local dev

```bash
uv sync
cp .env.example .env  # fill in
uv run python -m boombot.bot
```

`ffmpeg` must be on your PATH.

## Deploy

See [deploy/README.md](deploy/README.md).

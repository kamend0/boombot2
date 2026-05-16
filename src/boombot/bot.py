import asyncio
import logging

import discord
from discord.ext import commands

from boombot.aliases import AliasStore
from boombot.cogs.alias import AliasCog
from boombot.cogs.play import PlayCog
from boombot.cogs.trigger import TriggerCog
from boombot.cogs.voice import VoiceCog
from boombot.config import load_config
from boombot.logging_setup import setup_logging
from boombot.sounds import SoundLibrary
from boombot.state import ModeState

log = logging.getLogger(__name__)


async def main() -> None:
    cfg = load_config()
    setup_logging(cfg.log_level, cfg.log_dir)
    log.info("Starting boombot. sounds_dir=%s guild=%s", cfg.sounds_dir, cfg.discord_guild_id)

    aliases = AliasStore(cfg.s3_bucket, cfg.s3_aliases_key, cfg.aws_region)
    await aliases.load()

    sounds = SoundLibrary(cfg.sounds_dir)
    log.info("Loaded %d sounds: %s", len(sounds.names()), ", ".join(sounds.names()) or "(none)")

    modes = ModeState()

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.voice_states = True

    bot = commands.Bot(command_prefix="!!unused", intents=intents)

    @bot.event
    async def on_ready() -> None:
        log.info("Logged in as %s (id=%s)", bot.user, bot.user.id if bot.user else "?")
        try:
            if cfg.discord_guild_id:
                guild = discord.Object(id=cfg.discord_guild_id)
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                log.info("Synced %d slash commands to guild %s", len(synced), cfg.discord_guild_id)
            else:
                synced = await bot.tree.sync()
                log.info("Synced %d global slash commands", len(synced))
        except Exception as e:
            log.exception("Slash command sync failed: %s", e)

    await bot.add_cog(VoiceCog(bot, aliases, sounds, modes))
    await bot.add_cog(PlayCog(bot, sounds))
    await bot.add_cog(AliasCog(bot, aliases, sounds))
    await bot.add_cog(TriggerCog(bot, sounds, cfg.trigger_channel_name))

    async with bot:
        await bot.start(cfg.discord_token)


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down.")


if __name__ == "__main__":
    run()

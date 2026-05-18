import logging
import re
import time

import discord
from discord.ext import commands

from boombot.playback import play_file
from boombot.sounds import SoundLibrary
from boombot.state import VolumeState

log = logging.getLogger(__name__)

COOLDOWN_SECONDS = 3.0
TOKEN_RE = re.compile(r"[a-z0-9]+")


class TriggerCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        sounds: SoundLibrary,
        volumes: VolumeState,
        trigger_channel_name: str,
    ) -> None:
        self.bot = bot
        self.sounds = sounds
        self.volumes = volumes
        self.channel_name = trigger_channel_name
        self._last_played: dict[int, float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        if not isinstance(message.channel, discord.TextChannel):
            return
        if message.channel.name != self.channel_name:
            return

        vc = message.guild.voice_client
        if not isinstance(vc, discord.VoiceClient):
            return

        now = time.monotonic()
        last = self._last_played.get(message.guild.id, 0.0)
        if now - last < COOLDOWN_SECONDS:
            return

        for token in TOKEN_RE.findall(message.content.lower()):
            path = self.sounds.path(token)
            if path:
                self._last_played[message.guild.id] = now
                log.info(
                    "Trigger %s in #%s by %s",
                    token, message.channel.name, message.author,
                )
                await play_file(vc, path, volume=self.volumes.get(message.guild.id))
                return

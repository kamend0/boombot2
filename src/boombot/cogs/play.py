import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from boombot.playback import play_file
from boombot.sounds import SoundLibrary
from boombot.tts import synthesize

log = logging.getLogger(__name__)

MAX_SAY_CHARS = 240


class PlayCog(commands.Cog):
    def __init__(self, bot: commands.Bot, sounds: SoundLibrary) -> None:
        self.bot = bot
        self.sounds = sounds

    async def _sound_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        names = self.sounds.names()
        current = current.lower()
        matches = [n for n in names if current in n][:25]
        return [app_commands.Choice(name=n, value=n) for n in matches]

    @app_commands.command(name="play", description="Play a sound (must be in a voice channel).")
    @app_commands.describe(sound="Name of the sound, or 'any' for a random one.")
    @app_commands.autocomplete(sound=_sound_autocomplete)
    async def play(self, interaction: discord.Interaction, sound: str) -> None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if not isinstance(vc, discord.VoiceClient):
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
            return

        names = self.sounds.names()
        if sound.lower() == "any":
            if not names:
                await interaction.response.send_message("No sounds available.", ephemeral=True)
                return
            chosen = random.choice(names)
        else:
            chosen = sound.lower()
            if not self.sounds.has(chosen):
                await interaction.response.send_message(
                    f"No sound named '{chosen}'. Try /sounds.", ephemeral=True
                )
                return

        path = self.sounds.path(chosen)
        await interaction.response.send_message(f"Playing **{chosen}**.")
        log.info("Play %s in guild %s by %s", chosen, interaction.guild, interaction.user)
        await play_file(vc, path)

    @app_commands.command(name="sounds", description="List available sounds.")
    async def sounds_cmd(self, interaction: discord.Interaction) -> None:
        names = self.sounds.names()
        if not names:
            await interaction.response.send_message("No sounds available.", ephemeral=True)
            return
        await interaction.response.send_message("Available: " + ", ".join(names))

    @app_commands.command(name="say", description="Speak text aloud in voice.")
    @app_commands.describe(text=f"Up to {MAX_SAY_CHARS} characters.")
    async def say(self, interaction: discord.Interaction, text: str) -> None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if not isinstance(vc, discord.VoiceClient):
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
            return
        if len(text) > MAX_SAY_CHARS:
            await interaction.response.send_message(
                f"Too long ({len(text)} > {MAX_SAY_CHARS}).", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        try:
            path = await synthesize(text)
        except Exception as e:
            log.exception("TTS failed: %s", e)
            await interaction.followup.send("TTS failed.", ephemeral=True)
            return

        log.info("Say %r in guild %s by %s", text, interaction.guild, interaction.user)
        await interaction.followup.send("Speaking.")
        await play_file(vc, path, delete_after=True)

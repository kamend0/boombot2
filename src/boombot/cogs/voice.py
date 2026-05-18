import logging

import discord
from discord import app_commands
from discord.ext import commands

from boombot.aliases import AliasStore
from boombot.playback import play_file
from boombot.sounds import SoundLibrary
from boombot.state import DEFAULT_FALLBACK_SOUND, Mode, ModeState, VolumeState
from boombot.tts import synthesize

log = logging.getLogger(__name__)


def _best_name(member: discord.Member, alias: str | None) -> str:
    if alias:
        return alias
    return member.nick or member.display_name or member.name


class VoiceCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        aliases: AliasStore,
        sounds: SoundLibrary,
        modes: ModeState,
        volumes: VolumeState,
    ) -> None:
        self.bot = bot
        self.aliases = aliases
        self.sounds = sounds
        self.modes = modes
        self.volumes = volumes

    @app_commands.command(name="boomjoin", description="Join your current voice channel.")
    async def boomjoin(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await interaction.response.send_message("You need to be in a voice channel first.", ephemeral=True)
            return

        target = member.voice.channel
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.channel == target:
            await interaction.response.send_message("Already here.", ephemeral=True)
            return
        if vc:
            await vc.move_to(target)
        else:
            await target.connect()
        log.info("Joined voice channel %s in guild %s (by %s)", target.name, interaction.guild, member)
        await interaction.response.send_message(f"Joined **{target.name}**.")

    @app_commands.command(name="boomkick", description="Disconnect from voice.")
    async def boomkick(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
            return
        await vc.disconnect(force=False)
        log.info("Left voice in guild %s (by %s)", interaction.guild, interaction.user)
        await interaction.response.send_message("Left voice.")

    @app_commands.command(name="mode", description="Set announcement mode for this server.")
    @app_commands.describe(mode="default = per-user sound or TTS; name = always TTS; sound = always sound")
    @app_commands.choices(mode=[
        app_commands.Choice(name="default", value="default"),
        app_commands.Choice(name="name", value="name"),
        app_commands.Choice(name="sound", value="sound"),
    ])
    async def mode(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        self.modes.set(interaction.guild.id, Mode(mode.value))
        log.info("Mode set to %s in guild %s by %s", mode.value, interaction.guild, interaction.user)
        await interaction.response.send_message(f"Mode set to **{mode.value}**.")

    @app_commands.command(name="status", description="Show current mode and voice channel.")
    async def status(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        m = self.modes.get(interaction.guild.id)
        v = self.volumes.get(interaction.guild.id)
        vc = interaction.guild.voice_client
        where = f"in **{vc.channel.name}**" if vc else "not in voice"
        await interaction.response.send_message(
            f"Mode: **{m.value}**, volume: **{int(v * 100)}%**, {where}."
        )

    @app_commands.command(
        name="volume",
        description="Set playback volume for everyone (0-200%, default 100).",
    )
    @app_commands.describe(percent="Volume percentage, 0–200.")
    async def volume(self, interaction: discord.Interaction, percent: app_commands.Range[int, 0, 200]) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        applied = self.volumes.set(interaction.guild.id, percent / 100.0)
        log.info("Volume set to %.2f in guild %s by %s", applied, interaction.guild, interaction.user)
        await interaction.response.send_message(f"Volume set to **{int(applied * 100)}%**.")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return
        guild = member.guild
        vc = guild.voice_client
        if not isinstance(vc, discord.VoiceClient) or not vc.channel:
            return

        joined_bot_channel = (
            after.channel is not None
            and after.channel == vc.channel
            and before.channel != after.channel
        )
        if not joined_bot_channel:
            return

        await self._announce(vc, member)

    async def _announce(self, vc: discord.VoiceClient, member: discord.Member) -> None:
        entry = self.aliases.get(member.id)
        mode = self.modes.get(member.guild.id)

        if mode == Mode.NAME:
            await self._speak(vc, _best_name(member, entry.alias))
            return

        if mode == Mode.SOUND:
            sound = entry.join_sound or DEFAULT_FALLBACK_SOUND
            path = self.sounds.path(sound)
            if path:
                await play_file(vc, path, volume=self.volumes.get(member.guild.id))
            else:
                log.warning("Sound mode: no file for '%s'", sound)
            return

        # DEFAULT: per-user sound if set, else TTS
        if entry.join_sound:
            path = self.sounds.path(entry.join_sound)
            if path:
                await play_file(vc, path, volume=self.volumes.get(member.guild.id))
                return
            log.warning("User %s has join_sound=%s but file missing; falling back to TTS.", member, entry.join_sound)
        await self._speak(vc, _best_name(member, entry.alias))

    async def _speak(self, vc: discord.VoiceClient, name: str) -> None:
        text = f"...... {name} joined voice chat"
        try:
            path = await synthesize(text)
        except Exception as e:
            log.exception("TTS failed: %s", e)
            return
        await play_file(vc, path, delete_after=True, volume=self.volumes.get(vc.guild.id))

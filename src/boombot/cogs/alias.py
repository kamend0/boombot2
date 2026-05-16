import logging

import discord
from discord import app_commands
from discord.ext import commands

from boombot.aliases import AliasStore
from boombot.sounds import SoundLibrary

log = logging.getLogger(__name__)


class AliasCog(commands.Cog):
    def __init__(self, bot: commands.Bot, aliases: AliasStore, sounds: SoundLibrary) -> None:
        self.bot = bot
        self.aliases = aliases
        self.sounds = sounds

    alias_group = app_commands.Group(name="alias", description="Manage announcement aliases.")
    sound_group = app_commands.Group(name="sound", description="Manage per-user join sounds.")

    @alias_group.command(name="set", description="Set an alias. Defaults to you if no user given.")
    @app_commands.describe(alias="What to call them", user="Whose alias to set (default: you)")
    async def alias_set(
        self,
        interaction: discord.Interaction,
        alias: str,
        user: discord.Member | None = None,
    ) -> None:
        target = user or interaction.user
        await self.aliases.set_alias(target.id, alias)
        log.info("alias set: %s -> %r (by %s)", target, alias, interaction.user)
        await interaction.response.send_message(f"Alias for **{target.display_name}** set to: {alias}")

    @alias_group.command(name="clear", description="Clear an alias. Defaults to you.")
    async def alias_clear(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        target = user or interaction.user
        await self.aliases.set_alias(target.id, None)
        log.info("alias cleared: %s (by %s)", target, interaction.user)
        await interaction.response.send_message(f"Alias cleared for **{target.display_name}**.")

    @alias_group.command(name="list", description="Show all aliases and per-user sounds.")
    async def alias_list(self, interaction: discord.Interaction) -> None:
        lines: list[str] = []
        for uid, entry in self.aliases.items():
            member = interaction.guild.get_member(int(uid)) if interaction.guild else None
            label = member.display_name if member else f"<id:{uid}>"
            parts = []
            if entry.alias:
                parts.append(f"alias={entry.alias!r}")
            if entry.join_sound:
                parts.append(f"sound={entry.join_sound}")
            if parts:
                lines.append(f"• **{label}** — {', '.join(parts)}")
        if not lines:
            await interaction.response.send_message("Nothing set yet.", ephemeral=True)
            return
        await interaction.response.send_message("\n".join(lines))

    async def _sound_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        current = current.lower()
        matches = [n for n in self.sounds.names() if current in n][:25]
        return [app_commands.Choice(name=n, value=n) for n in matches]

    @sound_group.command(name="set", description="Set a join sound. Defaults to you.")
    @app_commands.describe(sound="Sound name (autocomplete)", user="Whose sound to set (default: you)")
    @app_commands.autocomplete(sound=_sound_autocomplete)
    async def sound_set(
        self,
        interaction: discord.Interaction,
        sound: str,
        user: discord.Member | None = None,
    ) -> None:
        if not self.sounds.has(sound):
            await interaction.response.send_message(f"No sound named '{sound}'.", ephemeral=True)
            return
        target = user or interaction.user
        await self.aliases.set_join_sound(target.id, sound.lower())
        log.info("join_sound set: %s -> %s (by %s)", target, sound, interaction.user)
        await interaction.response.send_message(
            f"Join sound for **{target.display_name}** set to: {sound}"
        )

    @sound_group.command(name="clear", description="Clear a join sound. Defaults to you.")
    async def sound_clear(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        target = user or interaction.user
        await self.aliases.set_join_sound(target.id, None)
        log.info("join_sound cleared: %s (by %s)", target, interaction.user)
        await interaction.response.send_message(
            f"Join sound cleared for **{target.display_name}**."
        )

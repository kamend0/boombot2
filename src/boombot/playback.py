"""Shared helpers for playing audio in a voice client."""
import asyncio
import logging
from pathlib import Path

import discord

log = logging.getLogger(__name__)


async def play_file(
    voice: discord.VoiceClient,
    path: Path,
    *,
    delete_after: bool = False,
    volume: float = 1.0,
) -> None:
    """Play an audio file. Waits until the previous track finishes."""
    while voice.is_playing():
        await asyncio.sleep(0.1)

    done = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _after(err: Exception | None) -> None:
        if err:
            log.error("Playback error for %s: %s", path, err)
        loop.call_soon_threadsafe(done.set)

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(str(path)), volume=volume
    )
    voice.play(source, after=_after)
    try:
        await done.wait()
    finally:
        if delete_after:
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                log.warning("Could not delete %s: %s", path, e)

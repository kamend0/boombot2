import asyncio
import tempfile
from pathlib import Path

from gtts import gTTS


async def synthesize(text: str) -> Path:
    """Generate an mp3 from text and return its temp-file path. Caller deletes it."""
    def _do() -> Path:
        fd = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        fd.close()
        gTTS(text=text, lang="en", slow=False).save(fd.name)
        return Path(fd.name)
    return await asyncio.to_thread(_do)

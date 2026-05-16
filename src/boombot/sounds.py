import logging
from pathlib import Path

log = logging.getLogger(__name__)


class SoundLibrary:
    def __init__(self, sounds_dir: Path) -> None:
        self._dir = sounds_dir

    def names(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted(p.stem for p in self._dir.glob("*.mp3"))

    def path(self, name: str) -> Path | None:
        candidate = self._dir / f"{name.lower()}.mp3"
        return candidate if candidate.exists() else None

    def has(self, name: str) -> bool:
        return self.path(name) is not None

from enum import Enum


class Mode(str, Enum):
    DEFAULT = "default"  # per-user join_sound if set, else TTS name
    NAME = "name"        # always TTS name
    SOUND = "sound"      # always sound (user's join_sound, else fallback)


DEFAULT_FALLBACK_SOUND = "boom"


class ModeState:
    """Per-guild mode, in-memory only (resets on restart)."""

    def __init__(self) -> None:
        self._modes: dict[int, Mode] = {}

    def get(self, guild_id: int) -> Mode:
        return self._modes.get(guild_id, Mode.DEFAULT)

    def set(self, guild_id: int, mode: Mode) -> None:
        self._modes[guild_id] = mode


class VolumeState:
    """Per-guild playback volume (0.0–2.0), in-memory only."""

    DEFAULT = 1.0
    MIN = 0.0
    MAX = 2.0

    def __init__(self) -> None:
        self._volumes: dict[int, float] = {}

    def get(self, guild_id: int) -> float:
        return self._volumes.get(guild_id, self.DEFAULT)

    def set(self, guild_id: int, volume: float) -> float:
        clamped = max(self.MIN, min(self.MAX, volume))
        self._volumes[guild_id] = clamped
        return clamped

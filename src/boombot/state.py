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

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    discord_token: str
    discord_guild_id: int | None
    trigger_channel_name: str
    aws_region: str
    s3_bucket: str
    s3_aliases_key: str
    log_level: str
    log_dir: Path
    sounds_dir: Path


def load_config() -> Config:
    token = os.environ["DISCORD_TOKEN"]
    guild_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
    return Config(
        discord_token=token,
        discord_guild_id=int(guild_raw) if guild_raw else None,
        trigger_channel_name=os.getenv("TRIGGER_CHANNEL_NAME", "boom-bot"),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        s3_bucket=os.environ["S3_BUCKET"],
        s3_aliases_key=os.getenv("S3_ALIASES_KEY", "boombot/aliases.json"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=Path(os.getenv("LOG_DIR", "./logs")),
        sounds_dir=Path(os.getenv("SOUNDS_DIR", "./sounds")),
    )

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from typing import Iterator

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


@dataclass
class UserEntry:
    alias: str | None = None
    join_sound: str | None = None

    def is_empty(self) -> bool:
        return not self.alias and not self.join_sound


class AliasStore:
    """In-memory cache of user entries, backed by a single JSON object in S3."""

    def __init__(self, bucket: str, key: str, region: str) -> None:
        self._bucket = bucket
        self._key = key
        self._s3 = boto3.client("s3", region_name=region)
        self._entries: dict[str, UserEntry] = {}
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        await asyncio.to_thread(self._load_sync)

    def _load_sync(self) -> None:
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=self._key)
            raw = json.loads(obj["Body"].read())
            self._entries = {
                str(uid): UserEntry(
                    alias=data.get("alias"),
                    join_sound=data.get("join_sound"),
                )
                for uid, data in raw.items()
            }
            log.info("Loaded %d alias entries from s3://%s/%s", len(self._entries), self._bucket, self._key)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                log.warning("No alias file at s3://%s/%s — starting empty.", self._bucket, self._key)
                self._entries = {}
            else:
                raise

    async def _save(self) -> None:
        payload = {
            uid: {k: v for k, v in asdict(entry).items() if v is not None}
            for uid, entry in self._entries.items()
            if not entry.is_empty()
        }
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        await asyncio.to_thread(
            self._s3.put_object,
            Bucket=self._bucket,
            Key=self._key,
            Body=body,
            ContentType="application/json",
        )

    def get(self, user_id: int) -> UserEntry:
        return self._entries.get(str(user_id), UserEntry())

    def items(self) -> Iterator[tuple[str, UserEntry]]:
        return iter(self._entries.items())

    async def set_alias(self, user_id: int, alias: str | None) -> None:
        async with self._lock:
            entry = self._entries.get(str(user_id), UserEntry())
            entry.alias = alias
            self._entries[str(user_id)] = entry
            await self._save()

    async def set_join_sound(self, user_id: int, sound: str | None) -> None:
        async with self._lock:
            entry = self._entries.get(str(user_id), UserEntry())
            entry.join_sound = sound
            self._entries[str(user_id)] = entry
            await self._save()

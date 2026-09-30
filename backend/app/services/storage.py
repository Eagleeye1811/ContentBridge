"""Object storage behind an S3-shaped interface.

Only a local-disk backend exists today; every call site goes through `storage`
so swapping in MinIO/S3 later touches this file alone.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from app.config import settings


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, uri: str) -> bytes: ...
    def path(self, uri: str) -> Path | None: ...
    def delete(self, uri: str) -> None: ...


class LocalStorage:
    """Writes under STORAGE_LOCAL_DIR. URIs look like `local://documents/<id>.pdf`."""

    scheme = "local://"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        target = (self.root / key).resolve()
        # Refuse anything that escapes the storage root.
        if not target.is_relative_to(self.root):
            raise ValueError(f"Unsafe storage key: {key!r}")
        return target

    def put(self, key: str, data: bytes) -> str:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return f"{self.scheme}{key}"

    def _key(self, uri: str) -> str:
        return uri[len(self.scheme) :] if uri.startswith(self.scheme) else uri

    def get(self, uri: str) -> bytes:
        return self._resolve(self._key(uri)).read_bytes()

    def path(self, uri: str) -> Path | None:
        p = self._resolve(self._key(uri))
        return p if p.exists() else None

    def delete(self, uri: str) -> None:
        self._resolve(self._key(uri)).unlink(missing_ok=True)


def get_storage() -> Storage:
    return LocalStorage(settings.storage_local_dir)


storage: Storage = get_storage()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

"""Private local storage backend with path-traversal protection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from app.core.exceptions import ValidationError


class StorageBackendProtocol(Protocol):
    """Protocol for private resume and generated-document storage backends."""

    async def save_bytes(self, *, key: str, data: bytes) -> str: ...

    async def read_bytes(self, *, key: str) -> bytes: ...

    async def delete(self, *, key: str) -> None: ...


class LocalPrivateStorage:
    """Stores private user artifacts on disk outside public static paths."""

    def __init__(self, base_path: str | Path) -> None:
        self._base_dir = Path(base_path).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_resolve(self, key: str) -> Path:
        cleaned = key.lstrip("/\\")
        if not cleaned or ".." in Path(cleaned).parts:
            raise ValidationError("Invalid storage key path.")
        target = (self._base_dir / cleaned).resolve()
        try:
            target.relative_to(self._base_dir)
        except ValueError as exc:
            raise ValidationError("Storage path escapes private storage root.") from exc
        return target

    async def save_bytes(self, *, key: str, data: bytes) -> str:
        target = self._safe_resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Never overwrite an already existing original artifact
        fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return key

    async def read_bytes(self, *, key: str) -> bytes:
        target = self._safe_resolve(key)
        return target.read_bytes()

    async def delete(self, *, key: str) -> None:
        target = self._safe_resolve(key)
        target.unlink(missing_ok=True)

"""Small file-based cache used by the academic pipeline."""

import hashlib
import json
import os
import time
from typing import Any


class PaperCache:
    """Simple JSON/text cache for downloaded paper artifacts."""

    def __init__(self, base_dir: str = "data/papers_cache", ttl_seconds: int = 7 * 24 * 3600):
        self.base_dir = base_dir
        self.ttl_seconds = ttl_seconds
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, namespace: str, key: str, ext: str) -> str:
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        ns_dir = os.path.join(self.base_dir, namespace)
        os.makedirs(ns_dir, exist_ok=True)
        return os.path.join(ns_dir, f"{digest}.{ext}")

    def _is_expired(self, path: str) -> bool:
        if not os.path.exists(path):
            return True
        modified = int(os.path.getmtime(path))
        now = int(time.time())
        return (now - modified) > self.ttl_seconds

    def get_text(self, namespace: str, key: str) -> str | None:
        path = self._path(namespace, key, "txt")
        if self._is_expired(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def set_text(self, namespace: str, key: str, content: str) -> None:
        path = self._path(namespace, key, "txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_json(self, namespace: str, key: str) -> dict[str, Any] | None:
        path = self._path(namespace, key, "json")
        if self._is_expired(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def set_json(self, namespace: str, key: str, payload: dict[str, Any]) -> None:
        path = self._path(namespace, key, "json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

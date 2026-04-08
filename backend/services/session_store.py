"""session_store.py – Thread-safe LRU in-memory session store."""

from __future__ import annotations
from collections import OrderedDict
from typing import Optional
import threading

_MAX = 30


class SessionStore:
    def __init__(self):
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, sid: str) -> Optional[dict]:
        with self._lock:
            return self._data.get(sid)

    def require(self, sid: str) -> dict:
        data = self.get(sid)
        if data is None:
            from fastapi import HTTPException
            raise HTTPException(404, f"Session '{sid}' not found. Please reload your file.")
        return data

    def create(self, sid: str, data: dict) -> None:
        with self._lock:
            self._data[sid] = data
            self._data.move_to_end(sid)
            while len(self._data) > _MAX:
                self._data.popitem(last=False)

    def update(self, sid: str, patch: dict) -> None:
        with self._lock:
            if sid in self._data:
                self._data[sid].update(patch)
                self._data.move_to_end(sid)


raw_store = SessionStore()
int_store = SessionStore()
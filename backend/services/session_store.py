"""session_store.py – Thread-safe LRU in-memory session store with JSON record persistence."""

from __future__ import annotations
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Optional
import threading

_MAX = 30
_RECORDS_DIR = Path(__file__).resolve().parents[1] / "persisted_peak_records"


def _slugify_name(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\-_\u4e00-\u9fff]+", "-", (value or "").strip())
    slug = slug.strip("-_")
    return slug[:80] or "records"


class SessionStore:
    def __init__(self, namespace: str):
        self.namespace = namespace
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def _records_dir(self) -> Path:
        path = _RECORDS_DIR / self.namespace
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _record_path(self, record_id: str) -> Path:
        return self._records_dir() / f"{record_id}.json"

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

    def save_records(self, sid: str, *, name: str = "") -> dict:
        sess = self.require(sid)
        records = sess.get("records", [])
        if not records:
            raise ValueError("No extracted records to save.")

        saved_at = datetime.now(timezone.utc)
        record_id = saved_at.strftime("%Y%m%dT%H%M%S%fZ")
        display_name = (name or "").strip() or f"{self.namespace}-records-{saved_at.strftime('%Y%m%d-%H%M%S')}"
        payload = {
            "id": record_id,
            "name": display_name,
            "namespace": self.namespace,
            "saved_at": saved_at.isoformat().replace("+00:00", "Z"),
            "record_count": len(records),
            "records": deepcopy(records),
        }
        file_path = self._record_path(f"{record_id}_{_slugify_name(display_name)}")
        with file_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

        return {
            "id": payload["id"],
            "name": payload["name"],
            "namespace": payload["namespace"],
            "saved_at": payload["saved_at"],
            "record_count": payload["record_count"],
            "file_name": file_path.name,
        }

    def list_saved_records(self) -> list[dict]:
        items: list[dict] = []
        for file_path in sorted(self._records_dir().glob("*.json"), reverse=True):
            try:
                with file_path.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            items.append({
                "id": str(payload.get("id") or file_path.stem),
                "name": str(payload.get("name") or file_path.stem),
                "namespace": str(payload.get("namespace") or self.namespace),
                "saved_at": str(payload.get("saved_at") or ""),
                "record_count": int(payload.get("record_count") or len(payload.get("records") or [])),
                "file_name": file_path.name,
            })
        return items

    def load_records(self, sid: str, record_id: str) -> dict:
        self.require(sid)
        record_id = (record_id or "").strip()
        if not record_id:
            raise FileNotFoundError("Saved record id is required.")

        matches = sorted(self._records_dir().glob(f"{record_id}*.json"), reverse=True)
        if not matches:
            raise FileNotFoundError(f"Saved record '{record_id}' not found.")

        with matches[0].open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        records = payload.get("records", [])
        if not isinstance(records, list):
            raise ValueError("Saved record payload is invalid.")

        self.update(sid, {"records": deepcopy(records)})
        return {
            "id": str(payload.get("id") or record_id),
            "name": str(payload.get("name") or matches[0].stem),
            "namespace": str(payload.get("namespace") or self.namespace),
            "saved_at": str(payload.get("saved_at") or ""),
            "record_count": len(records),
            "records": deepcopy(records),
            "file_name": matches[0].name,
        }


raw_store = SessionStore("raw")
int_store = SessionStore("integrated")

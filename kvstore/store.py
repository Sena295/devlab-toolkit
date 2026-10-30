"""Tiny persistent key-value store: append-only log, in-memory index, CRC checks, compaction, TTL.

Record format (one per line):  <crc32 hex>\t<json>   where json = {"op": "set"|"del", "k": ..., "v": ..., "exp": ...}
A torn last line (crash during write) fails its CRC and is ignored on recovery.
"""
from __future__ import annotations

import json
import os
import time
import zlib
from pathlib import Path
from typing import Any, Callable


class CorruptLog(Exception):
    pass


def _encode(record: dict) -> str:
    body = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
    return f"{zlib.crc32(body.encode()):08x}\t{body}\n"


def _decode(line: str) -> dict | None:
    crc, sep, body = line.rstrip("\n").partition("\t")
    if not sep:
        return None
    try:
        if int(crc, 16) != zlib.crc32(body.encode()):
            return None
        return json.loads(body)
    except ValueError:
        return None


class KVStore:
    def __init__(self, path: str | Path, clock: Callable[[], float] = time.time, fsync: bool = False):
        self.path = Path(path)
        self.clock = clock
        self.fsync = fsync
        self.index: dict[str, tuple[Any, float | None]] = {}
        self.dead = 0  # superseded records, drives compaction
        self.skipped = 0  # corrupt lines seen on load
        self._load()
        self._fh = self.path.open("a", encoding="utf-8")

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                rec = _decode(line)
                if rec is None:
                    self.skipped += 1
                    continue
                self._apply(rec)

    def _apply(self, rec: dict) -> None:
        key = rec["k"]
        if key in self.index:
            self.dead += 1
        if rec["op"] == "set":
            self.index[key] = (rec["v"], rec.get("exp"))
        else:
            self.index.pop(key, None)
            self.dead += 1

    def _append(self, rec: dict) -> None:
        self._fh.write(_encode(rec))
        self._fh.flush()
        if self.fsync:
            os.fsync(self._fh.fileno())
        self._apply(rec)

    # --- public API ------------------------------------------------------
    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        rec = {"op": "set", "k": key, "v": value}
        if ttl is not None:
            rec["exp"] = self.clock() + ttl
        self._append(rec)

    def get(self, key: str, default: Any = None) -> Any:
        hit = self.index.get(key)
        if hit is None:
            return default
        value, exp = hit
        if exp is not None and exp <= self.clock():
            self.delete(key)  # lazy expiry
            return default
        return value

    def delete(self, key: str) -> bool:
        if key not in self.index:
            return False
        self._append({"op": "del", "k": key})
        return True

    def keys(self, prefix: str = "") -> list[str]:
        return sorted(k for k in list(self.index) if k.startswith(prefix) and self.get(k, _MISSING) is not _MISSING)

    def incr(self, key: str, by: int = 1) -> int:
        value = self.get(key, 0)
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{key!r} is not an integer")
        self.set(key, value + by)
        return value + by

    def __len__(self) -> int:
        return len(self.keys())

    # --- maintenance -----------------------------------------------------
    def compact(self) -> int:
        """Rewrites the log with only live records. Returns the number of records dropped."""
        now = self.clock()
        live = {k: v for k, v in self.index.items() if v[1] is None or v[1] > now}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for k, (v, exp) in live.items():
                rec = {"op": "set", "k": k, "v": v}
                if exp is not None:
                    rec["exp"] = exp
                fh.write(_encode(rec))
            fh.flush()
            os.fsync(fh.fileno())
        self._fh.close()
        before = len(self.path.read_text(encoding="utf-8").splitlines())
        os.replace(tmp, self.path)  # atomic swap
        self.index = live
        self.dead = 0
        self._fh = self.path.open("a", encoding="utf-8")
        return before - len(live)

    def maybe_compact(self, ratio: float = 0.5) -> bool:
        total = len(self.index) + self.dead
        if total and self.dead / total > ratio:
            self.compact()
            return True
        return False

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "KVStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


_MISSING = object()

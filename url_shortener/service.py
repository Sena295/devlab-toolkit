"""URL shortener: base62 codes, click counting, expiry, custom aliases (SQLite)."""
from __future__ import annotations

import re
import secrets
import sqlite3
import string
import time
from urllib.parse import urlsplit

from httpkit import App, HTTPError, Response

ALPHABET = string.digits + string.ascii_letters  # 62 chars
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
RESERVED = {"api", "stats", "admin"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS links (
    code        TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    created_at  REAL NOT NULL,
    expires_at  REAL,
    clicks      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS clicks (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    code     TEXT NOT NULL REFERENCES links(code) ON DELETE CASCADE,
    at       REAL NOT NULL,
    referer  TEXT
);
"""


def encode_base62(n: int) -> str:
    if n < 0:
        raise ValueError("n deve ser >= 0")
    if n == 0:
        return ALPHABET[0]
    out = []
    while n:
        n, r = divmod(n, 62)
        out.append(ALPHABET[r])
    return "".join(reversed(out))


def decode_base62(s: str) -> int:
    n = 0
    for ch in s:
        n = n * 62 + ALPHABET.index(ch)
    return n


def validate_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise HTTPError(422, "URL inválida: use http:// ou https://")
    if len(url) > 2048:
        raise HTTPError(422, "URL longa demais")
    return url


class Shortener:
    def __init__(self, path: str = ":memory:", clock=time.time) -> None:
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.clock = clock

    def _new_code(self) -> str:
        for _ in range(10):
            code = "".join(secrets.choice(ALPHABET) for _ in range(6))
            if not self.db.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone():
                return code
        raise HTTPError(500, "não foi possível gerar um código único")

    def create(self, url: str, alias: str | None = None, ttl: float | None = None) -> dict:
        validate_url(url)
        if alias is not None:
            if not ALIAS_RE.match(alias) or alias in RESERVED:
                raise HTTPError(422, "alias inválido")
            if self.db.execute("SELECT 1 FROM links WHERE code = ?", (alias,)).fetchone():
                raise HTTPError(409, "alias já em uso")
        code = alias or self._new_code()
        now = self.clock()
        self.db.execute("INSERT INTO links (code, url, created_at, expires_at) VALUES (?, ?, ?, ?)",
                        (code, url, now, now + ttl if ttl else None))
        self.db.commit()
        return {"code": code, "url": url, "expires_at": now + ttl if ttl else None}

    def resolve(self, code: str, referer: str | None = None) -> str:
        row = self.db.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()
        if not row:
            raise HTTPError(404, "link não encontrado")
        if row["expires_at"] is not None and row["expires_at"] <= self.clock():
            raise HTTPError(410, "link expirado")
        self.db.execute("UPDATE links SET clicks = clicks + 1 WHERE code = ?", (code,))
        self.db.execute("INSERT INTO clicks (code, at, referer) VALUES (?, ?, ?)", (code, self.clock(), referer))
        self.db.commit()
        return row["url"]

    def stats(self, code: str) -> dict:
        row = self.db.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()
        if not row:
            raise HTTPError(404, "link não encontrado")
        refs = self.db.execute(
            "SELECT COALESCE(referer, 'direto') AS ref, COUNT(*) AS n FROM clicks WHERE code = ? GROUP BY ref ORDER BY n DESC",
            (code,)).fetchall()
        return {"code": code, "url": row["url"], "clicks": row["clicks"],
                "referers": {r["ref"]: r["n"] for r in refs}}

    def top(self, limit: int = 5) -> list[dict]:
        rows = self.db.execute("SELECT code, url, clicks FROM links ORDER BY clicks DESC, code LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def create_app(shortener: Shortener | None = None) -> App:
    svc = shortener or Shortener()
    app = App()

    @app.route("POST", "/api/links")
    def create(req):
        body = req.require("url")
        out = svc.create(body["url"], body.get("alias"), body.get("ttl"))
        return Response(201, out)

    @app.route("GET", "/api/links/<code>/stats")
    def stats(req):
        return svc.stats(req.params["code"])

    @app.route("GET", "/api/top")
    def top(req):
        return svc.top(int(req.query.get("limit", 5)))

    @app.route("GET", "/<code>")
    def go(req):
        target = svc.resolve(req.params["code"], req.headers.get("referer"))
        return Response(302, None, {"Location": target})

    return app


if __name__ == "__main__":
    server = create_app().serve(port=8000)
    print("Encurtador em http://127.0.0.1:8000  (POST /api/links {\"url\": ...})")
    server.serve_forever()

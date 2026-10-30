"""Tiny JSON web framework on top of http.server (no third-party dependencies).

`App.call()` runs a request in-process, so routes are testable without sockets.
`App.serve()` exposes the same routes over HTTP.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

CONVERTERS = {"int": (r"\d+", int), "str": (r"[^/]+", str)}


class HTTPError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    json: Any = None
    params: dict[str, Any] = field(default_factory=dict)

    def require(self, *fields: str) -> dict:
        if not isinstance(self.json, dict):
            raise HTTPError(400, "corpo JSON obrigatório")
        missing = [f for f in fields if f not in self.json]
        if missing:
            raise HTTPError(422, f"campos ausentes: {', '.join(missing)}")
        return self.json

    def bearer(self) -> str | None:
        auth = self.headers.get("authorization", "")
        return auth[7:] if auth.lower().startswith("bearer ") else None


@dataclass
class Response:
    status: int = 200
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)


def _compile(pattern: str) -> tuple[re.Pattern, list[tuple[str, Callable]]]:
    casts = []

    def repl(m: re.Match) -> str:
        kind, name = m["kind"] or "str", m["name"]
        rx, cast = CONVERTERS[kind]
        casts.append((name, cast))
        return f"(?P<{name}>{rx})"

    regex = re.sub(r"<(?:(?P<kind>\w+):)?(?P<name>\w+)>", repl, pattern)
    return re.compile(f"^{regex}$"), casts


class App:
    def __init__(self) -> None:
        self.routes: list[tuple[str, re.Pattern, list, Callable]] = []
        self.middleware: list[Callable[[Request], None]] = []

    def route(self, method: str, pattern: str):
        regex, casts = _compile(pattern)

        def deco(fn: Callable) -> Callable:
            self.routes.append((method.upper(), regex, casts, fn))
            return fn
        return deco

    def before(self, fn: Callable[[Request], None]) -> Callable:
        """Register a hook that runs before every handler (it may raise HTTPError)."""
        self.middleware.append(fn)
        return fn

    def handle(self, req: Request) -> Response:
        path_matched = False
        for method, regex, casts, fn in self.routes:
            m = regex.match(req.path)
            if not m:
                continue
            path_matched = True
            if method != req.method:
                continue
            req.params = {name: cast(m[name]) for name, cast in casts}
            try:
                for hook in self.middleware:
                    hook(req)
                out = fn(req)
            except HTTPError as e:
                return Response(e.status, {"error": e.message})
            return out if isinstance(out, Response) else Response(200, out)
        if path_matched:
            return Response(405, {"error": "método não permitido"})
        return Response(404, {"error": "rota não encontrada"})

    def call(self, method: str, url: str, json_body: Any = None, headers: dict | None = None) -> Response:
        parts = urlsplit(url)
        query = {k: v[0] for k, v in parse_qs(parts.query).items()}
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        return self.handle(Request(method.upper(), parts.path, query, hdrs, json_body))

    def serve(self, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
        app = self

        class Handler(BaseHTTPRequestHandler):
            def _run(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except json.JSONDecodeError:
                    resp = Response(400, {"error": "JSON inválido"})
                else:
                    parts = urlsplit(self.path)
                    req = Request(self.command, parts.path,
                                  {k: v[0] for k, v in parse_qs(parts.query).items()},
                                  {k.lower(): v for k, v in self.headers.items()}, body)
                    resp = app.handle(req)
                payload = b"" if resp.body is None else json.dumps(resp.body, ensure_ascii=False).encode()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                for k, v in resp.headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _run

            def log_message(self, *args) -> None:  # keep test output quiet
                pass

        return ThreadingHTTPServer((host, port), Handler)

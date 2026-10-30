"""Parsing of access and auth log lines into typed records."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Iterator

from .patterns import ACCESS_LOG, SSH_ACCEPTED, SSH_FAILED

ACCESS_TS_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
AUTH_TS_FORMAT = "%b %d %H:%M:%S"


@dataclass(frozen=True)
class AccessEvent:
    ip: str
    user: str
    timestamp: datetime
    method: str
    path: str
    status: int
    size: int
    referer: str
    agent: str


@dataclass(frozen=True)
class AuthEvent:
    ip: str
    user: str
    timestamp: datetime
    host: str
    success: bool


def parse_access_line(line: str) -> AccessEvent | None:
    m = ACCESS_LOG.match(line.strip())
    if not m:
        return None
    size = m["size"]
    return AccessEvent(
        ip=m["ip"],
        user=m["user"],
        timestamp=datetime.strptime(m["ts"], ACCESS_TS_FORMAT),
        method=m["method"],
        path=m["path"],
        status=int(m["status"]),
        size=0 if size == "-" else int(size),
        referer=m["referer"],
        agent=m["agent"],
    )


def parse_auth_line(line: str, year: int = 2025) -> AuthEvent | None:
    """Parse an sshd line. auth.log carries no year, so the caller supplies one."""
    for regex, ok in ((SSH_FAILED, False), (SSH_ACCEPTED, True)):
        m = regex.search(line)
        if m:
            ts = datetime.strptime(f"{year} {' '.join(m['ts'].split())}", "%Y %b %d %H:%M:%S")
            return AuthEvent(ip=m["ip"], user=m["user"], timestamp=ts, host=m["host"], success=ok)
    return None


def iter_access(lines: Iterable[str]) -> Iterator[AccessEvent]:
    for line in lines:
        ev = parse_access_line(line)
        if ev:
            yield ev


def iter_auth(lines: Iterable[str], year: int = 2025) -> Iterator[AuthEvent]:
    for line in lines:
        ev = parse_auth_line(line, year)
        if ev:
            yield ev

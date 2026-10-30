"""Detection rules: turn parsed events into security findings."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Iterable
from urllib.parse import unquote

from .parser import AccessEvent, AuthEvent
from .patterns import SCANNER_AGENTS, SIGNATURES

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class Finding:
    kind: str
    severity: str
    ip: str
    detail: str
    count: int = 1
    samples: list[str] = field(default_factory=list)


def detect_signatures(events: Iterable[AccessEvent]) -> list[Finding]:
    """Group signature hits per (signature, ip)."""
    hits: dict[tuple[str, str], Finding] = {}
    for ev in events:
        target = unquote(ev.path)
        for sig in SIGNATURES:
            if sig.regex.search(ev.path) or sig.regex.search(target):
                key = (sig.name, ev.ip)
                f = hits.get(key)
                if f is None:
                    f = hits[key] = Finding(sig.name, sig.severity, ev.ip, sig.description, 0)
                f.count += 1
                if len(f.samples) < 3:
                    f.samples.append(ev.path)
    return list(hits.values())


def detect_scanner_agents(events: Iterable[AccessEvent]) -> list[Finding]:
    by_ip: dict[str, Finding] = {}
    for ev in events:
        m = SCANNER_AGENTS.search(ev.agent)
        if not m:
            continue
        f = by_ip.setdefault(
            ev.ip,
            Finding("scanner_user_agent", "medium", ev.ip, f"User-Agent de ferramenta ({m[0].lower()})", 0),
        )
        f.count += 1
    return list(by_ip.values())


def detect_error_bursts(events: Iterable[AccessEvent], threshold: int = 20) -> list[Finding]:
    """Many 4xx responses from one IP usually means enumeration or fuzzing."""
    errors: Counter[str] = Counter()
    for ev in events:
        if 400 <= ev.status < 500:
            errors[ev.ip] += 1
    return [
        Finding("error_burst", "medium", ip, f"{n} respostas 4xx", n)
        for ip, n in errors.items() if n >= threshold
    ]


def detect_bruteforce(
    events: Iterable[AuthEvent],
    max_failures: int = 5,
    window: timedelta = timedelta(minutes=5),
) -> list[Finding]:
    """Sliding window: >= max_failures failed logins from one IP inside `window`."""
    fails: dict[str, list] = defaultdict(list)
    for ev in events:
        if not ev.success:
            fails[ev.ip].append(ev)
    findings = []
    for ip, evs in fails.items():
        evs.sort(key=lambda e: e.timestamp)
        left = 0
        worst = 0
        for right, ev in enumerate(evs):
            while ev.timestamp - evs[left].timestamp > window:
                left += 1
            worst = max(worst, right - left + 1)
        if worst >= max_failures:
            users = sorted({e.user for e in evs})
            findings.append(Finding(
                "ssh_bruteforce", "high", ip,
                f"{worst} falhas em {int(window.total_seconds() // 60)} min; usuários: {', '.join(users[:5])}",
                len(evs),
            ))
    return findings


def detect_compromise(events: Iterable[AuthEvent], max_failures: int = 5) -> list[Finding]:
    """A successful login after a run of failures from the same IP is suspicious."""
    ordered = sorted(events, key=lambda e: e.timestamp)
    streak: Counter[str] = Counter()
    findings = []
    for ev in ordered:
        if not ev.success:
            streak[ev.ip] += 1
        else:
            if streak[ev.ip] >= max_failures:
                findings.append(Finding(
                    "possible_compromise", "critical", ev.ip,
                    f"login bem-sucedido de '{ev.user}' após {streak[ev.ip]} falhas",
                ))
            streak[ev.ip] = 0
    return findings


def rank(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (-SEVERITY_ORDER[f.severity], -f.count, f.ip))

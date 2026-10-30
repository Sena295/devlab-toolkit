"""Synthetic log generator. Produces fully fictitious traffic for study and tests.

IPs come from the documentation ranges (RFC 5737) so they never map to real hosts.
"""
from __future__ import annotations

import random
from urllib.parse import quote
from datetime import datetime, timedelta, timezone

NORMAL_IPS = [f"203.0.113.{i}" for i in range(10, 60)]
ATTACKER_IPS = ["198.51.100.7", "198.51.100.23", "192.0.2.99"]
PAGES = ["/", "/produtos", "/sobre", "/contato", "/blog/post-1", "/blog/post-2", "/api/v1/status", "/preços"]
AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
]
ATTACK_PATHS = [
    "/produtos?id=1' OR 1=1--",
    "/produtos?id=1 UNION SELECT user,pass FROM users",
    "/busca?q=<script>alert(1)</script>",
    "/download?file=../../etc/passwd",
    "/wp-login.php",
    "/.env",
    "/phpmyadmin/index.php",
    "/ping?host=8.8.8.8;cat /etc/shadow",
]


def _fmt_access(ip, ts, method, path, status, size, agent) -> str:
    stamp = ts.strftime("%d/%b/%Y:%H:%M:%S %z")
    path = quote(path, safe="/?=&;:.-_<>'()")
    return f'{ip} - - [{stamp}] "{method} {path} HTTP/1.1" {status} {size} "-" "{agent}"'


def generate_access_log(n_normal: int = 500, seed: int = 42) -> list[str]:
    rng = random.Random(seed)
    start = datetime(2025, 3, 10, 8, 0, tzinfo=timezone.utc)
    lines = []
    for _ in range(n_normal):
        ts = start + timedelta(seconds=rng.randint(0, 6 * 3600))
        status = rng.choices([200, 304, 404, 500], weights=[80, 10, 8, 2])[0]
        lines.append((ts, _fmt_access(
            rng.choice(NORMAL_IPS), ts, "GET", rng.choice(PAGES), status,
            rng.randint(200, 20000), rng.choice(AGENTS),
        )))
    for ip in ATTACKER_IPS:
        base = start + timedelta(minutes=rng.randint(10, 300))
        for i in range(rng.randint(8, 30)):
            ts = base + timedelta(seconds=i * 2)
            agent = "sqlmap/1.7" if ip.endswith(".7") else rng.choice(AGENTS)
            lines.append((ts, _fmt_access(ip, ts, "GET", rng.choice(ATTACK_PATHS), rng.choice([400, 403, 404, 200]), 512, agent)))
    lines.sort(key=lambda t: t[0])
    return [line for _, line in lines]


def generate_auth_log(seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    base = datetime(2025, 3, 10, 2, 0)
    lines = []

    def row(ts, ok, user, ip):
        stamp = f"{ts.strftime('%b')} {ts.day:>2} {ts.strftime('%H:%M:%S')}"
        verb = "Accepted password" if ok else "Failed password"
        who = user if ok else f"invalid user {user}"
        lines.append((ts, f"{stamp} srv-demo sshd[{rng.randint(1000, 9999)}]: {verb} for {who} from {ip} port {rng.randint(30000, 60000)} ssh2"))

    for i in range(6):  # legitimate admin logins
        row(base + timedelta(hours=i * 3), True, "deploy", rng.choice(NORMAL_IPS))
    brute = ATTACKER_IPS[0]
    for i, user in enumerate(["root", "admin", "test", "oracle", "ubuntu", "postgres", "git", "deploy"]):
        row(base + timedelta(minutes=30, seconds=i * 15), False, user, brute)
    row(base + timedelta(minutes=33), True, "deploy", brute)  # breach after brute force
    for i in range(3):  # noise below threshold
        row(base + timedelta(hours=5, minutes=i), False, "admin", ATTACKER_IPS[1])
    lines.sort(key=lambda t: t[0])
    return [line for _, line in lines]

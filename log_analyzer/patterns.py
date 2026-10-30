"""Regex patterns used by the security log analyzer.

All sample data handled by this project is fictitious and generated locally.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Apache/Nginx "combined" access log format.
ACCESS_LOG = re.compile(
    r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}) \S+ (?P<user>\S+) '
    r'\[(?P<ts>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) (?P<proto>HTTP/[\d.]+)" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) '
    r'"(?P<referer>[^"]*)" "(?P<agent>[^"]*)"'
)

# OpenSSH style auth.log lines.
SSH_FAILED = re.compile(
    r'(?P<ts>\w{3}\s+\d+ \d{2}:\d{2}:\d{2}) (?P<host>\S+) sshd\[\d+\]: '
    r'Failed password for (?:invalid user )?(?P<user>\S+) '
    r'from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)'
)
SSH_ACCEPTED = re.compile(
    r'(?P<ts>\w{3}\s+\d+ \d{2}:\d{2}:\d{2}) (?P<host>\S+) sshd\[\d+\]: '
    r'Accepted (?P<method>\w+) for (?P<user>\S+) '
    r'from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)'
)


@dataclass(frozen=True)
class Signature:
    """A named attack signature applied to the request path / query string."""

    name: str
    severity: str
    regex: re.Pattern
    description: str


SIGNATURES: tuple[Signature, ...] = (
    Signature(
        "sql_injection", "high",
        re.compile(r"(?i)(union(\s|%20|\+)+select|or(\s|%20|\+)+1=1|'--|;\s*drop\s+table|sleep\(\d+\))"),
        "Tentativa de injeção de SQL na URL",
    ),
    Signature(
        "xss", "medium",
        re.compile(r"(?i)(<script|%3cscript|onerror=|javascript:|<img[^>]+src=)"),
        "Tentativa de cross-site scripting",
    ),
    Signature(
        "path_traversal", "high",
        re.compile(r"(\.\./|\.\.%2f|%2e%2e/|/etc/passwd|boot\.ini)", re.IGNORECASE),
        "Tentativa de leitura de arquivos fora do diretório web",
    ),
    Signature(
        "scanner_probe", "low",
        re.compile(r"(?i)(/wp-login\.php|/phpmyadmin|/\.env|/\.git/|/admin/config|/xmlrpc\.php)"),
        "Sondagem de caminhos comuns (scanner automatizado)",
    ),
    Signature(
        "command_injection", "critical",
        re.compile(r"(?i)(;|\||%7c|&&)\s*(cat|ls|wget|curl|nc|bash|sh)\b"),
        "Tentativa de execução de comandos no servidor",
    ),
)

SCANNER_AGENTS = re.compile(r"(?i)(sqlmap|nikto|nmap|masscan|dirbuster|gobuster|zgrab)")

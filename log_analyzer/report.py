"""Plain-text and Markdown rendering of analysis results."""
from __future__ import annotations

from collections import Counter

from .detectors import Finding
from .parser import AccessEvent

ICONS = {"low": "[ . ]", "medium": "[ ! ]", "high": "[!!]", "critical": "[XXX]"}


def bar(value: int, maximum: int, width: int = 30) -> str:
    if maximum <= 0:
        return ""
    return "#" * max(1, round(width * value / maximum)) if value else ""


def traffic_summary(events: list[AccessEvent]) -> str:
    status = Counter(f"{e.status // 100}xx" for e in events)
    top_ips = Counter(e.ip for e in events).most_common(5)
    top_paths = Counter(e.path.split("?")[0] for e in events).most_common(5)
    out = [f"Requisições analisadas: {len(events)}", "", "Status HTTP:"]
    biggest = max(status.values(), default=0)
    for k in sorted(status):
        out.append(f"  {k}  {status[k]:>5}  {bar(status[k], biggest)}")
    out += ["", "Top IPs:"] + [f"  {ip:<16}{n:>5}" for ip, n in top_ips]
    out += ["", "Top caminhos:"] + [f"  {p:<28}{n:>5}" for p, n in top_paths]
    return "\n".join(out)


def findings_text(findings: list[Finding]) -> str:
    if not findings:
        return "Nenhuma ameaça encontrada."
    out = []
    for f in findings:
        out.append(f"{ICONS[f.severity]:<6} {f.severity.upper():<9} {f.kind:<20} {f.ip:<16} x{f.count}")
        out.append(f"        {f.detail}")
        for s in f.samples:
            out.append(f"        > {s}")
    return "\n".join(out)


def findings_markdown(findings: list[Finding]) -> str:
    lines = ["# Relatório de segurança", "", "> Dados fictícios gerados para estudo.", "",
             "| Severidade | Tipo | IP | Ocorrências | Detalhe |", "|---|---|---|---|---|"]
    for f in findings:
        lines.append(f"| {f.severity} | {f.kind} | `{f.ip}` | {f.count} | {f.detail} |")
    return "\n".join(lines) + "\n"

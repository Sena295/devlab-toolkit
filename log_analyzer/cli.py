"""Command line entry point: python -m log_analyzer <command>."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import detectors as d
from .generator import generate_access_log, generate_auth_log
from .parser import iter_access, iter_auth
from .report import findings_markdown, findings_text, traffic_summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="log_analyzer", description="Analisador de logs de segurança (dados fictícios).")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="gera logs sintéticos")
    g.add_argument("outdir", type=Path)
    g.add_argument("--normal", type=int, default=500)
    g.add_argument("--seed", type=int, default=42)

    a = sub.add_parser("analyze", help="analisa logs existentes")
    a.add_argument("--access", type=Path, help="access.log (formato combined)")
    a.add_argument("--auth", type=Path, help="auth.log (sshd)")
    a.add_argument("--markdown", type=Path, help="salva relatório em Markdown")
    a.add_argument("--threshold", type=int, default=5, help="falhas SSH para considerar brute force")

    sub.add_parser("demo", help="gera e analisa dados em memória")
    return p


def analyze(access_lines, auth_lines, threshold=5):
    findings = []
    events = list(iter_access(access_lines))
    findings += d.detect_signatures(events)
    findings += d.detect_scanner_agents(events)
    findings += d.detect_error_bursts(events)
    auth = list(iter_auth(auth_lines))
    findings += d.detect_bruteforce(auth, max_failures=threshold)
    findings += d.detect_compromise(auth, max_failures=threshold)
    return events, d.rank(findings)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)

    if args.cmd == "generate":
        args.outdir.mkdir(parents=True, exist_ok=True)
        (args.outdir / "access.log").write_text("\n".join(generate_access_log(args.normal, args.seed)) + "\n", encoding="utf-8")
        (args.outdir / "auth.log").write_text("\n".join(generate_auth_log()) + "\n", encoding="utf-8")
        print(f"Logs fictícios gravados em {args.outdir}")
        return 0

    if args.cmd == "demo":
        events, findings = analyze(generate_access_log(), generate_auth_log())
    else:
        read = lambda p: p.read_text(encoding="utf-8", errors="replace").splitlines() if p else []
        events, findings = analyze(read(args.access), read(args.auth), args.threshold)
        if args.markdown:
            args.markdown.write_text(findings_markdown(findings), encoding="utf-8")

    print(traffic_summary(events))
    print("\n=== Achados ===")
    print(findings_text(findings))
    return 1 if any(f.severity in ("high", "critical") for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())

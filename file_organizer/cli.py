"""Command line: python -m file_organizer {organize,undo,demo}."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import organizer as org
from .rules import parse_custom_rules

DEMO_FILES = ["relatorio.pdf", "foto1.jpg", "foto2.PNG", "dados.csv", "musica.mp3", "script.py",
              "backup.zip", "slides.pptx", "notas.txt", "setup.exe", "sem_extensao", "video.mp4"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="file_organizer", description="Organizador automático de arquivos.")
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("organize", help="organiza uma pasta")
    o.add_argument("path", type=Path)
    o.add_argument("--dry-run", action="store_true", help="só mostra o plano")
    o.add_argument("--by-date", action="store_true", help="subpastas AAAA-MM")
    o.add_argument("--recursive", "-r", action="store_true")
    o.add_argument("--rule", action="append", default=[], metavar=".ext=Pasta", help="regra customizada")

    u = sub.add_parser("undo", help="desfaz a última organização")
    u.add_argument("path", type=Path)

    sub.add_parser("demo", help="roda numa pasta temporária com arquivos fictícios")
    return p


def run_organize(root: Path, dry_run=False, by_date=False, recursive=False, rules=None) -> int:
    if not root.is_dir():
        print(f"erro: '{root}' não é uma pasta", file=sys.stderr)
        return 2
    moves = org.plan(root, rules, by_date, recursive)
    if not moves:
        print("Nada a organizar.")
        return 0
    for m in moves:
        print(f"  {m.source.relative_to(root)}  ->  {m.target.relative_to(root)}")
    print("\nResumo:")
    for cat, n in org.summarize(moves, root).items():
        print(f"  {cat:<14}{n:>3}")
    if dry_run:
        print("\n(dry-run: nada foi movido)")
        return 0
    org.apply(root, moves)
    print(f"\n{len(moves)} arquivo(s) movido(s). Use 'undo' para reverter.")
    return 0


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.cmd == "organize":
        try:
            rules = parse_custom_rules(args.rule)
        except ValueError as e:
            print(f"erro: {e}", file=sys.stderr)
            return 2
        return run_organize(args.path, args.dry_run, args.by_date, args.recursive, rules)
    if args.cmd == "undo":
        try:
            print(f"{org.undo(args.path)} arquivo(s) restaurado(s).")
        except FileNotFoundError as e:
            print(f"erro: {e}", file=sys.stderr)
            return 1
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name in DEMO_FILES:
            (root / name).write_text("conteúdo fictício", encoding="utf-8")
        print(f"Pasta de demonstração: {root}\n")
        run_organize(root)
        print("\nDesfazendo...")
        print(f"{org.undo(root)} arquivo(s) restaurado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

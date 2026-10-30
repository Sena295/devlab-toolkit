"""Core logic: plan moves, apply them, undo them. Planning never touches the disk."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .rules import FALLBACK, classify

JOURNAL_NAME = ".organizer_journal.json"


@dataclass(frozen=True)
class Move:
    source: Path
    target: Path


def unique_target(target: Path, taken: set[Path]) -> Path:
    """Avoid overwriting: report.pdf -> report (1).pdf -> report (2).pdf."""
    candidate, n = target, 1
    while candidate.exists() or candidate in taken:
        candidate = target.with_name(f"{target.stem} ({n}){target.suffix}")
        n += 1
    return candidate


def plan(root: Path, overrides: dict[str, str] | None = None, by_date: bool = False,
         recursive: bool = False) -> list[Move]:
    overrides = overrides or {}
    files = root.rglob("*") if recursive else root.iterdir()
    moves: list[Move] = []
    taken: set[Path] = set()
    for f in sorted(files):
        if not f.is_file() or f.name == JOURNAL_NAME or f.name.startswith("."):
            continue
        category = overrides.get(f.suffix.lower()) or classify(f)
        dest_dir = root / category
        if by_date:
            dest_dir /= datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m")
        if f.parent == dest_dir:
            continue  # already organized
        target = unique_target(dest_dir / f.name, taken)
        taken.add(target)
        moves.append(Move(f, target))
    return moves


def apply(root: Path, moves: list[Move]) -> Path:
    """Execute the plan and write a journal so the run can be undone."""
    done = []
    for m in moves:
        m.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(m.source), str(m.target))
        done.append({"from": str(m.source), "to": str(m.target)})
    journal = root / JOURNAL_NAME
    journal.write_text(json.dumps({"at": datetime.now().isoformat(), "moves": done}, indent=2), encoding="utf-8")
    return journal


def undo(root: Path) -> int:
    journal = root / JOURNAL_NAME
    if not journal.exists():
        raise FileNotFoundError("nenhum journal encontrado; nada para desfazer")
    data = json.loads(journal.read_text(encoding="utf-8"))
    restored = 0
    for item in reversed(data["moves"]):
        src, dst = Path(item["to"]), Path(item["from"])
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            restored += 1
    for d in {Path(i["to"]).parent for i in data["moves"]}:
        try:
            d.rmdir()  # only removes folders that ended up empty
        except OSError:
            pass
    journal.unlink()
    return restored


def summarize(moves: list[Move], root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in moves:
        key = m.target.relative_to(root).parts[0] if m.target != root else FALLBACK
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

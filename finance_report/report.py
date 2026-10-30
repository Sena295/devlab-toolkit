"""Personal finance report: categorize bank-statement CSV rows and print totals.

CSV columns: date (YYYY-MM-DD), description, amount (negative = expense). Sample data is fictitious.
"""
from __future__ import annotations

import argparse
import csv
import io
import random
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

CATEGORY_RULES: list[tuple[str, re.Pattern]] = [
    ("Mercado", re.compile(r"(?i)mercado|supermercado|padaria|hortifruti")),
    ("Transporte", re.compile(r"(?i)uber|99|combust[ií]vel|posto|metr[oô]")),
    ("Assinaturas", re.compile(r"(?i)stream|musica|cloud|assinatura")),
    ("Moradia", re.compile(r"(?i)aluguel|condom[ií]nio|energia|internet")),
    ("Lazer", re.compile(r"(?i)cinema|bar |restaurante|show")),
    ("Renda", re.compile(r"(?i)sal[aá]rio|freela|reembolso")),
]


def categorize(description: str) -> str:
    for name, rx in CATEGORY_RULES:
        if rx.search(description):
            return name
    return "Outros"


def parse(text: str) -> list[dict]:
    rows = []
    for i, r in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        try:
            rows.append({"date": date.fromisoformat(r["date"]), "description": r["description"],
                         "amount": float(r["amount"]), "category": categorize(r["description"])})
        except (ValueError, KeyError) as e:
            raise ValueError(f"linha {i} inválida: {e}") from e
    return rows


def totals(rows: list[dict]) -> dict[str, float]:
    acc: dict[str, float] = defaultdict(float)
    for r in rows:
        acc[r["category"]] += r["amount"]
    return dict(sorted(acc.items(), key=lambda kv: kv[1]))


def monthly_balance(rows: list[dict]) -> dict[str, float]:
    acc: dict[str, float] = defaultdict(float)
    for r in rows:
        acc[r["date"].strftime("%Y-%m")] += r["amount"]
    return dict(sorted(acc.items()))


def money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render(rows: list[dict]) -> str:
    out = ["Gastos e receitas por categoria", "-" * 46]
    spent = [abs(v) for v in totals(rows).values() if v < 0]
    top = max(spent, default=1)
    for cat, v in totals(rows).items():
        out.append(f"{cat:<13}{money(v):>16}  {'#' * round(20 * abs(v) / top) if v < 0 else '+'}")
    out += ["", "Saldo mensal", "-" * 46]
    for month, v in monthly_balance(rows).items():
        out.append(f"{month}{money(v):>20}")
    out.append(f"\nSaldo total: {money(sum(r['amount'] for r in rows))}")
    return "\n".join(out)


def sample_csv(seed: int = 3) -> str:
    rng = random.Random(seed)
    items = [("Salário fictício", 5200), ("Aluguel", -1500), ("Supermercado Bom Preço", -320),
             ("Uber", -28), ("Streaming Plus", -39.9), ("Cinema", -45), ("Posto Central", -180), ("Freela", 800)]
    lines = ["date,description,amount"]
    for m in range(3):
        for desc, amt in items:
            d = date(2025, 1 + m, 1) + timedelta(days=rng.randint(0, 27))
            lines.append(f"{d},{desc},{amt * rng.uniform(0.9, 1.1):.2f}")
    return "\n".join(lines)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Relatório de finanças (dados fictícios)")
    p.add_argument("csv", nargs="?", type=Path, help="extrato CSV; sem argumento usa dados de exemplo")
    args = p.parse_args(argv)
    text = args.csv.read_text(encoding="utf-8") if args.csv else sample_csv()
    try:
        print(render(parse(text)))
    except ValueError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

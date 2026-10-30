"""Fictitious dataset generator (people, products, orders) -> CSV / JSON / SQLite.

Everything is random and seeded; no real person, company or document number is used.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

FIRST = ["Ana", "Bruno", "Carla", "Diego", "Eva", "Felipe", "Gabi", "Hugo", "Iris", "João", "Lia", "Marco"]
LAST = ["Silva", "Souza", "Lima", "Prado", "Dias", "Rocha", "Alves", "Costa", "Nunes", "Melo"]
CITIES = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Recife", "Porto Alegre"]
PRODUCTS = [("Caderno", 18.9), ("Caneta", 3.5), ("Mochila", 129.0), ("Garrafa", 42.0), ("Fone", 89.9),
            ("Teclado", 159.0), ("Mouse", 59.0), ("Monitor", 899.0)]


def customers(rng: random.Random, n: int) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        rows.append({
            "id": i,
            "name": f"{first} {last}",
            "email": f"{first}.{last}{i}@example.com".lower().replace("ã", "a"),
            "city": rng.choice(CITIES),
            "joined": (date(2024, 1, 1) + timedelta(days=rng.randint(0, 600))).isoformat(),
        })
    return rows


def orders(rng: random.Random, custs: list[dict], n: int) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        product, price = rng.choice(PRODUCTS)
        qty = rng.randint(1, 4)
        rows.append({
            "id": i,
            "customer_id": rng.choice(custs)["id"],
            "product": product,
            "quantity": qty,
            "unit_price": price,
            "total": round(qty * price, 2),
            "ordered_at": (date(2025, 1, 1) + timedelta(days=rng.randint(0, 364))).isoformat(),
        })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def write_sqlite(path: Path, tables: dict[str, list[dict]]) -> None:
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    for name, rows in tables.items():
        cols = list(rows[0])
        conn.execute(f"CREATE TABLE {name} ({', '.join(cols)})")
        conn.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(cols))})",
                         [tuple(r[c] for c in cols) for r in rows])
    conn.commit()
    conn.close()


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Gerador de dados fictícios")
    p.add_argument("outdir", type=Path)
    p.add_argument("--customers", type=int, default=100)
    p.add_argument("--orders", type=int, default=500)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--format", choices=["csv", "json", "sqlite", "all"], default="all")
    args = p.parse_args(argv)

    rng = random.Random(args.seed)
    custs = customers(rng, args.customers)
    tables = {"customers": custs, "orders": orders(rng, custs, args.orders)}
    args.outdir.mkdir(parents=True, exist_ok=True)

    for name, rows in tables.items():
        if args.format in ("csv", "all"):
            write_csv(args.outdir / f"{name}.csv", rows)
        if args.format in ("json", "all"):
            (args.outdir / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.format in ("sqlite", "all"):
        write_sqlite(args.outdir / "loja.db", tables)
    print(f"{len(custs)} clientes e {len(tables['orders'])} pedidos fictícios em {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

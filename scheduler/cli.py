"""Command line: python -m scheduler {demo,book,list,cancel,free} --db arquivo.db"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from . import service as svc


def when(text: str) -> datetime:
    return datetime.strptime(text, svc.ISO)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scheduler", description="Sistema de agendamento (dados fictícios).")
    p.add_argument("--db", default="agenda.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    r = sub.add_parser("resource"); r.add_argument("name"); r.add_argument("--kind", default="sala")
    b = sub.add_parser("book")
    b.add_argument("resource"); b.add_argument("customer")
    b.add_argument("start", type=when, help="AAAA-MM-DDTHH:MM"); b.add_argument("end", type=when)
    c = sub.add_parser("cancel"); c.add_argument("id", type=int)
    l = sub.add_parser("list"); l.add_argument("--day", type=lambda s: datetime.strptime(s, "%Y-%m-%d"))
    f = sub.add_parser("free")
    f.add_argument("resource"); f.add_argument("day", type=lambda s: datetime.strptime(s, "%Y-%m-%d"))
    f.add_argument("--minutes", type=int, default=60)
    return p


def show(bookings) -> None:
    if not bookings:
        print("Nenhum agendamento.")
    for b in bookings:
        print(f"#{b.id:<3} {b.starts_at:%d/%m %H:%M}-{b.ends_at:%H:%M}  {b.resource:<14} {b.customer}")


def demo() -> int:
    conn = svc.connect()
    for name, kind in [("Sala Azul", "sala"), ("Dra. Helena", "profissional")]:
        svc.add_resource(conn, name, kind)
    day = datetime(2025, 3, 10)  # segunda-feira
    at = lambda h, m=0: day.replace(hour=h, minute=m)
    attempts = [
        ("Sala Azul", "Ana Souza", at(9), at(10)),
        ("Sala Azul", "Bruno Lima", at(9, 30), at(10, 30)),   # conflito
        ("Sala Azul", "Carla Dias", at(10), at(11)),
        ("Dra. Helena", "Diego Ramos", at(7), at(8)),          # antes do expediente
        ("Dra. Helena", "Eva Prado", at(14), at(15)),
    ]
    for res, who, s, e in attempts:
        try:
            bid = svc.book(conn, res, who, s, e)
            print(f"OK    #{bid} {res} {s:%H:%M}-{e:%H:%M} {who}")
        except svc.BookingError as err:
            print(f"ERRO  {res} {s:%H:%M}-{e:%H:%M} {who}: {err}")
    svc.cancel(conn, 1)
    print("\nApós cancelar #1, horários livres da Sala Azul:")
    print("  " + ", ".join(f"{s:%H:%M}" for s in svc.free_slots(conn, "Sala Azul", day)))
    print("\nAgenda do dia:")
    show(svc.list_bookings(conn, day))
    return 0


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.cmd == "demo":
        return demo()
    conn = svc.connect(args.db)
    try:
        if args.cmd == "resource":
            svc.add_resource(conn, args.name, args.kind)
        elif args.cmd == "book":
            print(f"Agendamento #{svc.book(conn, args.resource, args.customer, args.start, args.end)} criado.")
        elif args.cmd == "cancel":
            svc.cancel(conn, args.id)
        elif args.cmd == "list":
            show(svc.list_bookings(conn, args.day))
        elif args.cmd == "free":
            for s in svc.free_slots(conn, args.resource, args.day, timedelta(minutes=args.minutes)):
                print(f"{s:%H:%M}")
    except svc.BookingError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

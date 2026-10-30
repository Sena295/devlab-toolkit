"""Booking rules on top of SQLite: overlap detection, business hours, cancellation."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
ISO = "%Y-%m-%dT%H:%M"
OPEN, CLOSE = time(8, 0), time(18, 0)
MIN_SLOT = timedelta(minutes=15)


class BookingError(Exception):
    """Raised when a booking violates a business rule."""


@dataclass(frozen=True)
class Booking:
    id: int
    resource: str
    customer: str
    starts_at: datetime
    ends_at: datetime
    status: str


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def add_resource(conn, name: str, kind: str = "sala", capacity: int = 1) -> int:
    cur = conn.execute("INSERT INTO resources (name, kind, capacity) VALUES (?, ?, ?)", (name, kind, capacity))
    conn.commit()
    return cur.lastrowid


def _resource_id(conn, name: str) -> int:
    row = conn.execute("SELECT id FROM resources WHERE name = ?", (name,)).fetchone()
    if not row:
        raise BookingError(f"recurso '{name}' não existe")
    return row["id"]


def _validate_window(start: datetime, end: datetime) -> None:
    if end <= start:
        raise BookingError("o fim deve ser depois do início")
    if end - start < MIN_SLOT:
        raise BookingError("duração mínima: 15 minutos")
    if start.date() != end.date():
        raise BookingError("agendamento não pode cruzar a meia-noite")
    if start.time() < OPEN or end.time() > CLOSE:
        raise BookingError(f"fora do expediente ({OPEN:%H:%M}-{CLOSE:%H:%M})")
    if start.weekday() >= 5:
        raise BookingError("não atendemos aos fins de semana")


def find_conflicts(conn, resource_id: int, start: datetime, end: datetime):
    """Two intervals overlap when each one starts before the other ends."""
    return conn.execute(
        """SELECT * FROM bookings
           WHERE resource_id = ? AND status = 'confirmed'
             AND starts_at < ? AND ends_at > ?""",
        (resource_id, end.strftime(ISO), start.strftime(ISO)),
    ).fetchall()


def book(conn, resource: str, customer: str, start: datetime, end: datetime) -> int:
    _validate_window(start, end)
    rid = _resource_id(conn, resource)
    capacity = conn.execute("SELECT capacity FROM resources WHERE id = ?", (rid,)).fetchone()["capacity"]
    if len(find_conflicts(conn, rid, start, end)) >= capacity:
        raise BookingError(f"horário indisponível para '{resource}'")
    cur = conn.execute(
        "INSERT INTO bookings (resource_id, customer, starts_at, ends_at) VALUES (?, ?, ?, ?)",
        (rid, customer, start.strftime(ISO), end.strftime(ISO)),
    )
    conn.commit()
    return cur.lastrowid


def cancel(conn, booking_id: int) -> None:
    cur = conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ? AND status = 'confirmed'", (booking_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise BookingError(f"agendamento {booking_id} não encontrado ou já cancelado")


def list_bookings(conn, day: datetime | None = None) -> list[Booking]:
    sql = """SELECT b.*, r.name AS resource FROM bookings b JOIN resources r ON r.id = b.resource_id
             WHERE b.status = 'confirmed'"""
    params: tuple = ()
    if day:
        sql += " AND substr(b.starts_at, 1, 10) = ?"
        params = (day.strftime("%Y-%m-%d"),)
    rows = conn.execute(sql + " ORDER BY b.starts_at", params).fetchall()
    return [Booking(r["id"], r["resource"], r["customer"],
                    datetime.strptime(r["starts_at"], ISO), datetime.strptime(r["ends_at"], ISO), r["status"])
            for r in rows]


def free_slots(conn, resource: str, day: datetime, length: timedelta = timedelta(minutes=60)):
    """Return start times of free windows of `length` inside business hours."""
    rid = _resource_id(conn, resource)
    cursor = datetime.combine(day.date(), OPEN)
    closing = datetime.combine(day.date(), CLOSE)
    slots = []
    while cursor + length <= closing:
        if not find_conflicts(conn, rid, cursor, cursor + length):
            slots.append(cursor)
        cursor += length
    return slots

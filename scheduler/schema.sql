-- Schema do sistema de agendamento (SQLite). Dados fictícios.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS resources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL CHECK (kind IN ('sala', 'profissional', 'equipamento')),
    capacity    INTEGER NOT NULL DEFAULT 1 CHECK (capacity > 0)
);

CREATE TABLE IF NOT EXISTS bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id  INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    customer     TEXT NOT NULL,
    starts_at    TEXT NOT NULL,   -- ISO 8601, ex.: 2025-03-10T09:00
    ends_at      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_bookings_resource_time ON bookings (resource_id, starts_at, ends_at);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings (status);

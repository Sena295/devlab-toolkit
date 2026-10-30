"""Library REST API: books, members, loans with business rules (SQLite)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from httpkit import App, HTTPError, Response

LOAN_DAYS = 14
MAX_ACTIVE_LOANS = 3
FINE_PER_DAY = 0.50

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    isbn TEXT UNIQUE,
    copies INTEGER NOT NULL DEFAULT 1 CHECK (copies >= 0)
);
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    loaned_on TEXT NOT NULL,
    due_on TEXT NOT NULL,
    returned_on TEXT,
    fine REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_loans_member ON loans (member_id, returned_on);
"""


def isbn10_valid(isbn: str) -> bool:
    digits = isbn.replace("-", "")
    if len(digits) != 10 or not digits[:9].isdigit() or not (digits[9].isdigit() or digits[9] == "X"):
        return False
    total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(digits))
    return total % 11 == 0


class Library:
    def __init__(self, path: str = ":memory:", today=date.today) -> None:
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.today = today

    # --- books -----------------------------------------------------------
    def add_book(self, title: str, author: str, isbn: str | None, copies: int = 1) -> dict:
        if not title.strip() or not author.strip():
            raise HTTPError(422, "título e autor são obrigatórios")
        if copies < 1:
            raise HTTPError(422, "copies deve ser >= 1")
        if isbn and not isbn10_valid(isbn):
            raise HTTPError(422, "ISBN-10 inválido")
        try:
            cur = self.db.execute("INSERT INTO books (title, author, isbn, copies) VALUES (?, ?, ?, ?)",
                                  (title.strip(), author.strip(), isbn, copies))
        except sqlite3.IntegrityError as e:
            raise HTTPError(409, "ISBN já cadastrado") from e
        self.db.commit()
        return self.get_book(cur.lastrowid)

    def get_book(self, book_id: int) -> dict:
        row = self.db.execute("""
            SELECT b.*, b.copies - (SELECT COUNT(*) FROM loans l WHERE l.book_id = b.id AND l.returned_on IS NULL) AS available
            FROM books b WHERE b.id = ?""", (book_id,)).fetchone()
        if not row:
            raise HTTPError(404, "livro não encontrado")
        return dict(row)

    def search_books(self, term: str = "", only_available: bool = False) -> list[dict]:
        like = f"%{term}%"
        rows = self.db.execute("""
            SELECT b.*, b.copies - (SELECT COUNT(*) FROM loans l WHERE l.book_id = b.id AND l.returned_on IS NULL) AS available
            FROM books b WHERE b.title LIKE ? OR b.author LIKE ? ORDER BY b.title""", (like, like)).fetchall()
        books = [dict(r) for r in rows]
        return [b for b in books if b["available"] > 0] if only_available else books

    # --- members ---------------------------------------------------------
    def add_member(self, name: str, email: str) -> dict:
        if "@" not in email:
            raise HTTPError(422, "e-mail inválido")
        try:
            cur = self.db.execute("INSERT INTO members (name, email) VALUES (?, ?)", (name.strip(), email.lower()))
        except sqlite3.IntegrityError as e:
            raise HTTPError(409, "e-mail já cadastrado") from e
        self.db.commit()
        return {"id": cur.lastrowid, "name": name.strip(), "email": email.lower()}

    def _member(self, member_id: int) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        if not row:
            raise HTTPError(404, "membro não encontrado")
        return row

    # --- loans -----------------------------------------------------------
    def lend(self, book_id: int, member_id: int) -> dict:
        self._member(member_id)
        book = self.get_book(book_id)
        if book["available"] < 1:
            raise HTTPError(409, "nenhum exemplar disponível")
        today = self.today()
        rows = self.db.execute("SELECT due_on FROM loans WHERE member_id = ? AND returned_on IS NULL", (member_id,)).fetchall()
        if len(rows) >= MAX_ACTIVE_LOANS:
            raise HTTPError(409, f"limite de {MAX_ACTIVE_LOANS} empréstimos ativos")
        if any(date.fromisoformat(r["due_on"]) < today for r in rows):
            raise HTTPError(409, "membro com empréstimo em atraso")
        cur = self.db.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (?, ?, ?, ?)",
                              (book_id, member_id, today.isoformat(), (today + timedelta(days=LOAN_DAYS)).isoformat()))
        self.db.commit()
        return self.get_loan(cur.lastrowid)

    def get_loan(self, loan_id: int) -> dict:
        row = self.db.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        if not row:
            raise HTTPError(404, "empréstimo não encontrado")
        return dict(row)

    def give_back(self, loan_id: int) -> dict:
        loan = self.get_loan(loan_id)
        if loan["returned_on"]:
            raise HTTPError(409, "já devolvido")
        today = self.today()
        late = max(0, (today - date.fromisoformat(loan["due_on"])).days)
        self.db.execute("UPDATE loans SET returned_on = ?, fine = ? WHERE id = ?",
                        (today.isoformat(), round(late * FINE_PER_DAY, 2), loan_id))
        self.db.commit()
        return self.get_loan(loan_id)

    def overdue(self) -> list[dict]:
        rows = self.db.execute("""
            SELECT l.id, m.name AS member, b.title, l.due_on FROM loans l
            JOIN members m ON m.id = l.member_id JOIN books b ON b.id = l.book_id
            WHERE l.returned_on IS NULL AND l.due_on < ? ORDER BY l.due_on""", (self.today().isoformat(),)).fetchall()
        return [dict(r) for r in rows]


def create_app(lib: Library | None = None) -> App:
    lib = lib or Library()
    app = App()

    @app.route("POST", "/books")
    def add_book(req):
        b = req.require("title", "author")
        return Response(201, lib.add_book(b["title"], b["author"], b.get("isbn"), b.get("copies", 1)))

    @app.route("GET", "/books")
    def books(req):
        return lib.search_books(req.query.get("q", ""), req.query.get("available") == "true")

    @app.route("GET", "/books/<int:id>")
    def book(req):
        return lib.get_book(req.params["id"])

    @app.route("POST", "/members")
    def add_member(req):
        b = req.require("name", "email")
        return Response(201, lib.add_member(b["name"], b["email"]))

    @app.route("POST", "/loans")
    def lend(req):
        b = req.require("book_id", "member_id")
        return Response(201, lib.lend(b["book_id"], b["member_id"]))

    @app.route("POST", "/loans/<int:id>/return")
    def give_back(req):
        return lib.give_back(req.params["id"])

    @app.route("GET", "/loans/overdue")
    def overdue(req):
        return lib.overdue()

    return app

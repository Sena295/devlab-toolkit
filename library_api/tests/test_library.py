import unittest
from datetime import date, timedelta

from library_api.service import Library, create_app, isbn10_valid

VALID_ISBN = "0-306-40615-2"  # standard ISBN-10 example


class Today:
    d = date(2025, 3, 10)

    def __call__(self):
        return self.d


class IsbnTests(unittest.TestCase):
    def test_validation(self):
        self.assertTrue(isbn10_valid(VALID_ISBN))
        self.assertTrue(isbn10_valid("080442957X"))
        self.assertFalse(isbn10_valid("0-306-40615-3"))
        self.assertFalse(isbn10_valid("abc"))


class LibraryApiTests(unittest.TestCase):
    def setUp(self):
        self.today = Today()
        self.app = create_app(Library(today=self.today))
        self.member = self.app.call("POST", "/members", {"name": "Ana", "email": "ana@example.com"}).body["id"]

    def book(self, title="Dom Casmurro", copies=1, isbn=None):
        return self.app.call("POST", "/books", {"title": title, "author": "Autor Fictício", "copies": copies, "isbn": isbn}).body

    def lend(self, book_id, member=None):
        return self.app.call("POST", "/loans", {"book_id": book_id, "member_id": member or self.member})

    def test_book_crud_and_validation(self):
        self.assertEqual(self.book(isbn=VALID_ISBN)["available"], 1)
        self.assertEqual(self.app.call("POST", "/books", {"title": "X", "author": "Y", "isbn": VALID_ISBN}).status, 409)
        self.assertEqual(self.app.call("POST", "/books", {"title": "X", "author": "Y", "isbn": "123"}).status, 422)
        self.assertEqual(self.app.call("POST", "/books", {"title": "X"}).status, 422)
        self.assertEqual(self.app.call("GET", "/books/999").status, 404)

    def test_lending_reduces_availability(self):
        b = self.book(copies=2)
        self.assertEqual(self.lend(b["id"]).status, 201)
        self.assertEqual(self.app.call("GET", f"/books/{b['id']}").body["available"], 1)

    def test_no_copies_left(self):
        b = self.book()
        self.lend(b["id"])
        other = self.app.call("POST", "/members", {"name": "Bia", "email": "bia@example.com"}).body["id"]
        self.assertEqual(self.lend(b["id"], other).status, 409)

    def test_max_active_loans(self):
        ids = [self.book(f"Livro {i}")["id"] for i in range(4)]
        for i in ids[:3]:
            self.assertEqual(self.lend(i).status, 201)
        self.assertEqual(self.lend(ids[3]).status, 409)

    def test_return_on_time_has_no_fine(self):
        loan = self.lend(self.book()["id"]).body
        done = self.app.call("POST", f"/loans/{loan['id']}/return").body
        self.assertEqual(done["fine"], 0)
        self.assertEqual(self.app.call("POST", f"/loans/{loan['id']}/return").status, 409)

    def test_late_return_fine_and_overdue_block(self):
        b1, b2 = self.book("A")["id"], self.book("B")["id"]
        loan = self.lend(b1).body
        self.today.d += timedelta(days=14 + 4)
        overdue = self.app.call("GET", "/loans/overdue").body
        self.assertEqual([o["title"] for o in overdue], ["A"])
        self.assertEqual(self.lend(b2).status, 409)  # blocked while overdue
        self.assertEqual(self.app.call("POST", f"/loans/{loan['id']}/return").body["fine"], 2.0)
        self.assertEqual(self.lend(b2).status, 201)

    def test_search(self):
        self.book("Python Básico")
        self.book("Redes de Computadores")
        self.assertEqual(len(self.app.call("GET", "/books?q=python").body), 1)
        self.assertEqual(len(self.app.call("GET", "/books").body), 2)

    def test_member_rules(self):
        self.assertEqual(self.app.call("POST", "/members", {"name": "Ana 2", "email": "ANA@example.com"}).status, 409)
        self.assertEqual(self.app.call("POST", "/members", {"name": "X", "email": "sem-arroba"}).status, 422)
        self.assertEqual(self.lend(self.book()["id"], member=999).status, 404)


if __name__ == "__main__":
    unittest.main()

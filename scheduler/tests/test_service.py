import unittest
from datetime import datetime, timedelta

from scheduler import service as svc

MON = datetime(2025, 3, 10)  # segunda-feira
SAT = datetime(2025, 3, 15)


def at(h, m=0, day=MON):
    return day.replace(hour=h, minute=m)


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.conn = svc.connect()
        svc.add_resource(self.conn, "Sala A")
        svc.add_resource(self.conn, "Sala B")

    def test_book_and_list(self):
        svc.book(self.conn, "Sala A", "Ana", at(9), at(10))
        (b,) = svc.list_bookings(self.conn, MON)
        self.assertEqual((b.customer, b.resource), ("Ana", "Sala A"))

    def test_overlap_rejected(self):
        svc.book(self.conn, "Sala A", "Ana", at(9), at(10))
        for s, e in [(at(9, 30), at(10, 30)), (at(8, 30), at(9, 30)), (at(9), at(10)), (at(8), at(11))]:
            with self.assertRaises(svc.BookingError):
                svc.book(self.conn, "Sala A", "Bia", s, e)

    def test_adjacent_allowed(self):
        svc.book(self.conn, "Sala A", "Ana", at(9), at(10))
        svc.book(self.conn, "Sala A", "Bia", at(10), at(11))
        svc.book(self.conn, "Sala A", "Cris", at(8), at(9))

    def test_other_resource_independent(self):
        svc.book(self.conn, "Sala A", "Ana", at(9), at(10))
        svc.book(self.conn, "Sala B", "Bia", at(9), at(10))

    def test_business_rules(self):
        cases = [(at(7), at(8)), (at(17), at(19)), (at(9), at(9, 10)), (at(10), at(9)),
                 (at(9, day=SAT), at(10, day=SAT))]
        for s, e in cases:
            with self.assertRaises(svc.BookingError):
                svc.book(self.conn, "Sala A", "X", s, e)

    def test_unknown_resource(self):
        with self.assertRaises(svc.BookingError):
            svc.book(self.conn, "Sala Z", "X", at(9), at(10))

    def test_cancel_frees_slot(self):
        bid = svc.book(self.conn, "Sala A", "Ana", at(9), at(10))
        svc.cancel(self.conn, bid)
        svc.book(self.conn, "Sala A", "Bia", at(9), at(10))
        with self.assertRaises(svc.BookingError):
            svc.cancel(self.conn, bid)  # já cancelado

    def test_free_slots(self):
        svc.book(self.conn, "Sala A", "Ana", at(9), at(11))
        hours = [s.hour for s in svc.free_slots(self.conn, "Sala A", MON)]
        self.assertEqual(hours, [8, 11, 12, 13, 14, 15, 16, 17])

    def test_capacity_greater_than_one(self):
        svc.add_resource(self.conn, "Auditório", "sala", capacity=2)
        svc.book(self.conn, "Auditório", "A", at(9), at(10))
        svc.book(self.conn, "Auditório", "B", at(9), at(10))
        with self.assertRaises(svc.BookingError):
            svc.book(self.conn, "Auditório", "C", at(9), at(10))


if __name__ == "__main__":
    unittest.main()

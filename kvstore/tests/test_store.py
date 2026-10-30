import tempfile
import unittest
from pathlib import Path

from kvstore.store import KVStore


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


class KVStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "data.log"
        self.clock = Clock()

    def tearDown(self):
        self._tmp.cleanup()

    def open(self):
        return KVStore(self.path, clock=self.clock)

    def test_set_get_delete(self):
        with self.open() as db:
            db.set("a", {"x": [1, 2]})
            self.assertEqual(db.get("a"), {"x": [1, 2]})
            self.assertTrue(db.delete("a"))
            self.assertFalse(db.delete("a"))
            self.assertIsNone(db.get("a"))
            self.assertEqual(db.get("a", "padrão"), "padrão")

    def test_persistence_across_restarts(self):
        with self.open() as db:
            db.set("a", 1)
            db.set("b", "dois")
            db.set("a", 10)
            db.delete("b")
        with self.open() as db:
            self.assertEqual((db.get("a"), db.get("b")), (10, None))
            self.assertEqual(len(db), 1)

    def test_ttl(self):
        with self.open() as db:
            db.set("session", "x", ttl=30)
            self.assertEqual(db.get("session"), "x")
            self.clock.now += 31
            self.assertIsNone(db.get("session"))
            self.assertEqual(db.keys(), [])

    def test_ttl_survives_restart(self):
        with self.open() as db:
            db.set("k", 1, ttl=10)
        self.clock.now += 11
        with self.open() as db:
            self.assertIsNone(db.get("k"))

    def test_prefix_keys_and_incr(self):
        with self.open() as db:
            for k in ("user:2", "user:1", "post:1"):
                db.set(k, 1)
            self.assertEqual(db.keys("user:"), ["user:1", "user:2"])
            self.assertEqual((db.incr("hits"), db.incr("hits", 5)), (1, 6))
            db.set("name", "texto")
            with self.assertRaises(TypeError):
                db.incr("name")

    def test_torn_write_is_ignored(self):
        with self.open() as db:
            db.set("ok", 1)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write('deadbeef\t{"op":"set","k":"bad","v":')  # crash in the middle of a write
        with self.open() as db:
            self.assertEqual(db.get("ok"), 1)
            self.assertIsNone(db.get("bad"))
            self.assertEqual(db.skipped, 1)

    def test_bit_flip_detected_by_crc(self):
        with self.open() as db:
            db.set("a", "valor")
        text = self.path.read_text(encoding="utf-8").replace("valor", "valar")
        self.path.write_text(text, encoding="utf-8")
        with self.open() as db:
            self.assertIsNone(db.get("a"))
            self.assertEqual(db.skipped, 1)

    def test_compaction_shrinks_log(self):
        with self.open() as db:
            for i in range(50):
                db.set("hot", i)
            db.set("keep", "x")
            db.set("temp", "y", ttl=1)
            db.delete("temp")
            size_before = self.path.stat().st_size
            dropped = db.compact()
            self.assertGreater(dropped, 40)
            self.assertLess(self.path.stat().st_size, size_before)
            self.assertEqual((db.get("hot"), db.get("keep")), (49, "x"))
            db.set("after", 1)  # still writable after compaction
        with self.open() as db:
            self.assertEqual((db.get("hot"), db.get("after")), (49, 1))

    def test_maybe_compact_threshold(self):
        with self.open() as db:
            db.set("a", 1)
            self.assertFalse(db.maybe_compact())
            for i in range(10):
                db.set("a", i)
            self.assertTrue(db.maybe_compact())


if __name__ == "__main__":
    unittest.main()

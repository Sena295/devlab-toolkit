import sqlite3
import tempfile
import unittest
from pathlib import Path

from datagen.generate import main


class GenerateTests(unittest.TestCase):
    def test_all_formats_and_determinism(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            main([a, "--customers", "10", "--orders", "30", "--seed", "5"])
            main([b, "--customers", "10", "--orders", "30", "--seed", "5"])
            for name in ("customers.csv", "orders.json", "loja.db"):
                self.assertTrue((Path(a) / name).exists())
            self.assertEqual((Path(a) / "orders.csv").read_text(encoding="utf-8"),
                             (Path(b) / "orders.csv").read_text(encoding="utf-8"))
            conn = sqlite3.connect(Path(a) / "loja.db")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 30)
            conn.close()

    def test_only_example_domain_emails(self):
        with tempfile.TemporaryDirectory() as d:
            main([d, "--format", "csv", "--customers", "20"])
            lines = (Path(d) / "customers.csv").read_text(encoding="utf-8").splitlines()[1:]
            self.assertTrue(all(l.split(",")[2].endswith("@example.com") for l in lines))


if __name__ == "__main__":
    unittest.main()

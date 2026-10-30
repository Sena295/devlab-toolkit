import tempfile
import unittest
from pathlib import Path

from file_organizer import organizer as org
from file_organizer.rules import classify, parse_custom_rules


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def touch(self, *names):
        for n in names:
            (self.root / n).write_text("x")


class RulesTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify(Path("a.PNG")), "Imagens")
        self.assertEqual(classify(Path("a.xyz")), "Outros")
        self.assertEqual(classify(Path("Makefile")), "Outros")

    def test_custom_rules(self):
        self.assertEqual(parse_custom_rules([".log=Logs"]), {".log": "Logs"})
        with self.assertRaises(ValueError):
            parse_custom_rules(["log=Logs"])


class OrganizerTests(Base):
    def test_plan_does_not_touch_disk(self):
        self.touch("a.pdf", "b.jpg")
        moves = org.plan(self.root)
        self.assertEqual(len(moves), 2)
        self.assertTrue((self.root / "a.pdf").exists())

    def test_apply_and_undo_roundtrip(self):
        self.touch("a.pdf", "b.jpg", "c.zip")
        org.apply(self.root, org.plan(self.root))
        self.assertTrue((self.root / "Documentos" / "a.pdf").exists())
        self.assertEqual(org.undo(self.root), 3)
        self.assertTrue((self.root / "a.pdf").exists())
        self.assertFalse((self.root / "Documentos").exists())

    def test_name_collision_gets_suffix(self):
        self.touch("a.pdf")
        (self.root / "Documentos").mkdir()
        (self.root / "Documentos" / "a.pdf").write_text("old")
        (move,) = org.plan(self.root)
        self.assertEqual(move.target.name, "a (1).pdf")

    def test_override_rule(self):
        self.touch("x.log")
        (move,) = org.plan(self.root, {".log": "Logs"})
        self.assertEqual(move.target.parent.name, "Logs")

    def test_undo_without_journal(self):
        with self.assertRaises(FileNotFoundError):
            org.undo(self.root)

    def test_hidden_files_ignored(self):
        self.touch(".secret")
        self.assertEqual(org.plan(self.root), [])


if __name__ == "__main__":
    unittest.main()

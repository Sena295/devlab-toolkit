import unittest

from bot_engine.engine import Bot, BotError, convert, parse_duration, safe_eval


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


class PureFunctionTests(unittest.TestCase):
    def test_safe_eval(self):
        self.assertEqual(safe_eval("2*(3+4)"), 14)
        self.assertEqual(safe_eval("10/4"), 2.5)
        self.assertEqual(safe_eval("-3+5"), 2)
        self.assertEqual(safe_eval("2+3*4-1"), 13)

    def test_safe_eval_rejects_code(self):
        for bad in ("__import__('os')", "2**3", "1/0", "(1+2", "", "abc", "1 2"):
            with self.assertRaises(BotError, msg=bad):
                safe_eval(bad)

    def test_duration(self):
        self.assertEqual(parse_duration("90s"), 90)
        self.assertEqual(parse_duration("2h"), 7200)
        for bad in ("0m", "10", "m", "5x"):
            with self.assertRaises(BotError):
                parse_duration(bad)

    def test_convert(self):
        self.assertEqual(convert(10, "usd", "brl"), 50)
        self.assertAlmostEqual(convert(55, "BRL", "EUR"), 10)
        with self.assertRaises(BotError):
            convert(1, "XXX", "BRL")


class BotTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.bot = Bot(clock=self.clock, cooldown=0)

    def test_ignores_plain_text_and_unknown_commands(self):
        self.assertIsNone(self.bot.handle("ana", "oi pessoal"))
        self.assertIn("desconhecido", self.bot.handle("ana", "!xyz"))

    def test_basic_commands(self):
        self.assertEqual(self.bot.handle("ana", "!ping"), "pong")
        self.assertEqual(self.bot.handle("ana", "!calc 6*7"), "= 42")
        self.assertIn("500,00 BRL", self.bot.handle("ana", "!cotacao 100 usd brl").replace(".", ","))
        self.assertIn("Erro", self.bot.handle("ana", "!calc 1/0"))
        self.assertIn("!ping", self.bot.handle("ana", "!ajuda"))

    def test_reminders_fire_in_order(self):
        self.bot.handle("ana", '!lembrar 10m "tomar água"')
        self.bot.handle("bia", "!lembrar 5m reunião")
        self.assertEqual(self.bot.due_reminders(), [])
        self.clock.now += 301
        self.assertEqual([r.text for r in self.bot.due_reminders()], ["reunião"])
        self.clock.now += 400
        (r,) = self.bot.due_reminders()
        self.assertEqual((r.user, r.text), ("ana", "tomar água"))

    def test_poll(self):
        self.bot.handle("ana", "!enquete criar pizza calabresa queijo")
        self.bot.handle("ana", "!enquete votar pizza queijo")
        self.bot.handle("bia", "!enquete votar pizza queijo")
        self.assertIn("queijo: 2 (100%)", self.bot.handle("ana", "!enquete ver pizza"))
        self.assertIn("Erro", self.bot.handle("ana", "!enquete votar pizza abacaxi"))

    def test_cooldown(self):
        bot = Bot(clock=self.clock, cooldown=5)
        self.assertEqual(bot.handle("ana", "!ping"), "pong")
        self.assertIn("Calma", bot.handle("ana", "!ping"))
        self.assertEqual(bot.handle("bia", "!ping"), "pong")  # per-user
        self.clock.now += 6
        self.assertEqual(bot.handle("ana", "!ping"), "pong")

    def test_unbalanced_quotes(self):
        self.assertEqual(self.bot.handle("ana", '!lembrar 5m "abc'), "Aspas não fechadas.")

    def test_custom_command(self):
        @self.bot.command("oi")
        def oi(user, args):
            return f"oi, {user}"
        self.assertEqual(self.bot.handle("ana", "!oi"), "oi, ana")


if __name__ == "__main__":
    unittest.main()

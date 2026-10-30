import unittest

from finance_report import report as r

CSV = "date,description,amount\n2025-01-05,Salário,1000\n2025-01-06,Uber,-30\n2025-02-01,Supermercado,-200\n2025-02-02,Coisa estranha,-10\n"


class FinanceTests(unittest.TestCase):
    def test_categorize(self):
        self.assertEqual(r.categorize("UBER *TRIP"), "Transporte")
        self.assertEqual(r.categorize("xyz"), "Outros")

    def test_totals_and_monthly(self):
        rows = r.parse(CSV)
        self.assertEqual(r.totals(rows)["Mercado"], -200)
        self.assertEqual(r.monthly_balance(rows), {"2025-01": 970.0, "2025-02": -210.0})

    def test_invalid_row(self):
        with self.assertRaises(ValueError):
            r.parse("date,description,amount\nontem,x,1\n")

    def test_money_format(self):
        self.assertEqual(r.money(1234.5), "R$ 1.234,50")

    def test_render_has_total(self):
        self.assertIn("Saldo total: R$ 760,00", r.render(r.parse(CSV)))


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import timedelta

from log_analyzer import detectors as d
from log_analyzer.cli import analyze
from log_analyzer.generator import generate_access_log, generate_auth_log
from log_analyzer.parser import iter_access, iter_auth, parse_access_line, parse_auth_line

LINE = '203.0.113.5 - - [10/Mar/2025:08:00:00 +0000] "GET /a?id=1\'%20OR%201=1-- HTTP/1.1" 200 512 "-" "sqlmap/1.7"'


class ParserTests(unittest.TestCase):
    def test_access_line(self):
        ev = parse_access_line(LINE)
        self.assertEqual(ev.ip, "203.0.113.5")
        self.assertEqual(ev.status, 200)
        self.assertEqual(ev.method, "GET")

    def test_garbage_returns_none(self):
        self.assertIsNone(parse_access_line("not a log line"))
        self.assertIsNone(parse_auth_line("random"))

    def test_auth_failed(self):
        ev = parse_auth_line("Mar 10 02:30:00 srv sshd[1234]: Failed password for invalid user root from 198.51.100.7 port 4000 ssh2")
        self.assertFalse(ev.success)
        self.assertEqual(ev.user, "root")


class DetectorTests(unittest.TestCase):
    def test_sqli_and_scanner(self):
        events = list(iter_access([LINE]))
        kinds = {f.kind for f in d.detect_signatures(events)}
        self.assertIn("sql_injection", kinds)
        self.assertEqual(d.detect_scanner_agents(events)[0].kind, "scanner_user_agent")

    def test_bruteforce_window(self):
        auth = list(iter_auth(generate_auth_log()))
        found = d.detect_bruteforce(auth, max_failures=5, window=timedelta(minutes=5))
        self.assertEqual([f.ip for f in found], ["198.51.100.7"])

    def test_compromise_detected(self):
        auth = list(iter_auth(generate_auth_log()))
        self.assertEqual(len(d.detect_compromise(auth)), 1)

    def test_full_pipeline_ranks_critical_first(self):
        _, findings = analyze(generate_access_log(), generate_auth_log())
        self.assertEqual(findings[0].severity, "critical")

    def test_generator_is_deterministic(self):
        self.assertEqual(generate_access_log(50, seed=1), generate_access_log(50, seed=1))


if __name__ == "__main__":
    unittest.main()

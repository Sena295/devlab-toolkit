import unittest

from tinylang.interpreter import run
from tinylang.lexer import TinyError, tokenize
from tinylang.parser import parse


def output(src: str) -> list[str]:
    lines: list[str] = []
    run(src, lines.append)
    return lines


class LexerTests(unittest.TestCase):
    def test_tokens(self):
        kinds = [t.kind for t in tokenize('let x = 3.5 + "a"; # comentário')]
        self.assertEqual(kinds, ["KW", "ID", "SYM", "NUM", "SYM", "STR", "SYM", "EOF"])

    def test_line_numbers(self):
        self.assertEqual(tokenize("a\n\nb")[1].line, 3)

    def test_errors(self):
        for bad in ('"abc', "@", '"\\q"'):
            with self.assertRaises(TinyError):
                tokenize(bad)


class ParserTests(unittest.TestCase):
    def test_precedence(self):
        (stmt,) = parse("1 + 2 * 3;")
        self.assertEqual(stmt[1][1], "+")
        self.assertEqual(stmt[1][3][1], "*")

    def test_syntax_errors(self):
        for bad in ("let = 1;", "print 1", "if x { ", "1 + ;", "(1 + 2;", "1 = 2;"):
            with self.assertRaises(TinyError, msg=bad):
                parse(bad)


class EvalTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(output("print 2 + 3 * 4; print (2 + 3) * 4; print 7 % 3; print 10 / 4; print 8 / 2;"),
                         ["14", "20", "1", "2.5", "4"])

    def test_strings_and_comparison(self):
        self.assertEqual(output('print "n=" + 3; print "a" < "b"; print 1 == 1.0; print nil == false;'),
                         ["n=3", "true", "true", "false"])

    def test_logic_short_circuit(self):
        self.assertEqual(output("let x = 0; print false and (x = 1); print x; print nil or 5; print not true;"),
                         ["false", "0", "5", "false"])

    def test_control_flow(self):
        src = "let i = 0; let s = 0; while i < 5 { s = s + i; i = i + 1; } if s > 5 { print \"grande\"; } else { print \"pequeno\"; }"
        self.assertEqual(output(src), ["grande"])

    def test_else_if_chain(self):
        src = "let f = fn(n) { if n < 0 { return \"neg\"; } else if n == 0 { return \"zero\"; } else { return \"pos\"; } };" \
              "print f(-1); print f(0); print f(9);"
        self.assertEqual(output(src), ["neg", "zero", "pos"])

    def test_closures(self):
        src = """
        let counter = fn() { let n = 0; return fn() { n = n + 1; return n; }; };
        let a = counter(); let b = counter();
        a(); a();
        print a(); print b();
        """
        self.assertEqual(output(src), ["3", "1"])

    def test_recursion(self):
        self.assertEqual(output("let f = fn(n) { if n <= 1 { return 1; } return n * f(n - 1); }; print f(10);"), ["3628800"])

    def test_block_scope(self):
        with self.assertRaises(TinyError):
            output("{ let hidden = 1; } print hidden;")

    def test_shadowing_and_assignment_to_outer(self):
        self.assertEqual(output("let x = 1; { x = 2; let y = 5; } print x;"), ["2"])

    def test_builtins(self):
        self.assertEqual(output('print len("abcd"); print max(3, 9, 2); print sqrt(16); print num("42") + 1;'), ["4", "9", "4", "43"])

    def test_runtime_errors(self):
        cases = ["print 1 / 0;", "print undefined_var;", 'print -"a";', "let f = fn(a) { return a; }; f(1, 2);",
                 "5();", "print 1 < nil;"]
        for src in cases:
            with self.assertRaises(TinyError, msg=src):
                output(src)

    def test_error_reports_line(self):
        with self.assertRaises(TinyError) as ctx:
            output("let a = 1;\nlet b = 2;\nprint a / 0;")
        self.assertIn("linha 3", str(ctx.exception))

    def test_infinite_loop_is_stopped(self):
        with self.assertRaises(TinyError):
            output("while true { }")

    def test_runaway_recursion_is_stopped(self):
        with self.assertRaises(TinyError):
            output("let f = fn() { return f(); }; f();")


if __name__ == "__main__":
    unittest.main()

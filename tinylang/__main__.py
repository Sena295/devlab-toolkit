"""python -m tinylang [arquivo.tiny]  -- sem argumento, abre o REPL; com `demo`, roda um exemplo."""
import sys

from .interpreter import repl, run

DEMO = """
# closures e recursão
let make_counter = fn() {
  let n = 0;
  return fn() { n = n + 1; return n; };
};
let c = make_counter();
c(); c();
print "contador: " + c();

let fib = fn(n) { if n < 2 { return n; } return fib(n - 1) + fib(n - 2); };
let i = 0;
while i < 10 { print "fib(" + i + ") = " + fib(i); i = i + 1; }
"""

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "demo":
        run(DEMO)
    elif arg:
        with open(arg, encoding="utf-8") as fh:
            run(fh.read())
    else:
        repl()

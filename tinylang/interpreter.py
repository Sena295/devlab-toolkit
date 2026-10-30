"""Tree-walking evaluator with lexical scoping, closures and a recursion limit."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .lexer import TinyError
from .parser import parse

MAX_DEPTH = 200
MAX_STEPS = 1_000_000  # guards against infinite loops in untrusted snippets


class Return(Exception):
    def __init__(self, value):
        self.value = value


class Env:
    def __init__(self, parent: "Env | None" = None):
        self.vars: dict[str, object] = {}
        self.parent = parent

    def lookup(self, name: str, line: int):
        env = self
        while env:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise TinyError(f"variável não definida: {name}", line)

    def assign(self, name: str, value, line: int):
        env = self
        while env:
            if name in env.vars:
                env.vars[name] = value
                return value
            env = env.parent
        raise TinyError(f"atribuição a variável não definida: {name}", line)


@dataclass
class Function:
    params: list[str]
    body: tuple
    closure: Env

    def __repr__(self) -> str:
        return f"<fn/{len(self.params)}>"


def show(v) -> str:
    if v is None:
        return "nil"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def truthy(v) -> bool:
    return v is not None and v is not False


class Interpreter:
    def __init__(self, out: Callable[[str], None] = print):
        self.out = out
        self.globals = Env()
        self.depth = 0
        self.steps = 0
        self._install_builtins()

    def _install_builtins(self) -> None:
        g = self.globals.vars
        g["len"] = lambda s: len(s)
        g["str"] = lambda v: show(v)
        g["num"] = lambda s: float(s) if "." in s else int(s)
        g["sqrt"] = lambda x: x ** 0.5
        g["max"] = max
        g["min"] = min
        g["abs"] = abs

    def run(self, src: str):
        result = None
        for stmt in parse(src):
            result = self.exec(stmt, self.globals)
        return result

    # --- statements ------------------------------------------------------
    def exec(self, node, env: Env):
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise TinyError("limite de passos excedido (loop infinito?)")
        kind = node[0]
        if kind == "let":
            env.vars[node[1]] = self.eval(node[2], env)
        elif kind == "print":
            self.out(show(self.eval(node[1], env)))
        elif kind == "expr":
            return self.eval(node[1], env)
        elif kind == "block":
            inner = Env(env)
            for s in node[1]:
                self.exec(s, inner)
        elif kind == "if":
            if truthy(self.eval(node[1], env)):
                self.exec(node[2], env)
            elif node[3] is not None:
                self.exec(node[3], env)
        elif kind == "while":
            while truthy(self.eval(node[1], env)):
                self.exec(node[2], env)
        elif kind == "return":
            raise Return(None if node[1] is None else self.eval(node[1], env))
        else:
            raise TinyError(f"instrução desconhecida {kind}")
        return None

    # --- expressions -----------------------------------------------------
    def eval(self, node, env: Env):
        kind = node[0]
        if kind == "lit":
            return node[1]
        if kind == "var":
            return env.lookup(node[1], node[2])
        if kind == "assign":
            return env.assign(node[1], self.eval(node[2], env), node[3])
        if kind == "neg":
            return -self.number(self.eval(node[1], env), node[2])
        if kind == "not":
            return not truthy(self.eval(node[1], env))
        if kind == "logic":
            left = self.eval(node[2], env)
            if node[1] == "or":
                return left if truthy(left) else self.eval(node[3], env)
            return self.eval(node[3], env) if truthy(left) else left
        if kind == "bin":
            return self.binary(node[1], self.eval(node[2], env), self.eval(node[3], env), node[4])
        if kind == "fn":
            return Function(node[1], node[2], env)
        if kind == "call":
            return self.call(self.eval(node[1], env), [self.eval(a, env) for a in node[2]], node[3])
        raise TinyError(f"expressão desconhecida {kind}")

    @staticmethod
    def number(v, line: int):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise TinyError(f"esperado número, recebido {show(v)}", line)
        return v

    def binary(self, op: str, a, b, line: int):
        if op == "+" and (isinstance(a, str) or isinstance(b, str)):
            return show(a) + show(b)  # string concatenation converts the other side
        if op in ("==", "!="):
            return (a == b) == (op == "==")
        if op in ("<", "<=", ">", ">=") and isinstance(a, str) and isinstance(b, str):
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        a, b = self.number(a, line), self.number(b, line)
        if op == "+": return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op in ("/", "%") and b == 0:
            raise TinyError("divisão por zero", line)
        if op == "/":
            q = a / b
            return int(q) if isinstance(a, int) and isinstance(b, int) and a % b == 0 else q
        if op == "%": return a % b
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]

    def call(self, fn, args: list, line: int):
        if callable(fn) and not isinstance(fn, Function):
            try:
                return fn(*args)
            except TypeError as e:
                raise TinyError(f"chamada inválida de função nativa: {e}", line) from e
        if not isinstance(fn, Function):
            raise TinyError(f"não é possível chamar {show(fn)}", line)
        if len(args) != len(fn.params):
            raise TinyError(f"esperado {len(fn.params)} argumento(s), recebido {len(args)}", line)
        if self.depth >= MAX_DEPTH:
            raise TinyError("recursão profunda demais", line)
        local = Env(fn.closure)
        local.vars.update(zip(fn.params, args))
        self.depth += 1
        try:
            for stmt in fn.body[1]:
                self.exec(stmt, local)
        except Return as r:
            return r.value
        finally:
            self.depth -= 1
        return None


def run(src: str, out: Callable[[str], None] = print):
    return Interpreter(out).run(src)


def repl() -> None:
    it = Interpreter()
    print("TinyLang REPL (Ctrl+C para sair). Ex.: print 1 + 2;")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            value = it.run(line)
            if value is not None:
                print(show(value))
        except TinyError as e:
            print(f"erro: {e}")

"""Recursive-descent parser producing a tuple-based AST.

Grammar (lowest to highest precedence):
    program    := statement* EOF
    statement  := let | print | if | while | return | block | expr ';'
    expr       := assignment
    assignment := ID '=' assignment | or
    or         := and ('or' and)*          and := equality ('and' equality)*
    equality   := compare (('=='|'!=') compare)*
    compare    := term (('<'|'<='|'>'|'>=') term)*
    term       := factor (('+'|'-') factor)*      factor := unary (('*'|'/'|'%') unary)*
    unary      := ('-'|'not') unary | call
    call       := primary ('(' args ')')*
    primary    := NUM | STR | true | false | nil | ID | '(' expr ')' | 'fn' '(' params ')' block
"""
from __future__ import annotations

from .lexer import TinyError, Token, tokenize


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # --- helpers ---------------------------------------------------------
    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def check(self, kind: str, value=None) -> bool:
        t = self.peek()
        return t.kind == kind and (value is None or t.value == value)

    def match(self, kind: str, *values) -> Token | None:
        t = self.peek()
        if t.kind == kind and (not values or t.value in values):
            return self.advance()
        return None

    def expect(self, kind: str, value=None) -> Token:
        if self.check(kind, value):
            return self.advance()
        t = self.peek()
        wanted = value or kind
        raise TinyError(f"esperado '{wanted}', encontrado '{t.value}'", t.line)

    # --- statements ------------------------------------------------------
    def program(self) -> list:
        stmts = []
        while not self.check("EOF"):
            stmts.append(self.statement())
        return stmts

    def block(self) -> tuple:
        self.expect("SYM", "{")
        body = []
        while not self.check("SYM", "}"):
            if self.check("EOF"):
                raise TinyError("bloco não fechado", self.peek().line)
            body.append(self.statement())
        self.expect("SYM", "}")
        return ("block", body)

    def statement(self):
        line = self.peek().line
        if self.match("KW", "let"):
            name = self.expect("ID").value
            self.expect("SYM", "=")
            value = self.expr()
            self.expect("SYM", ";")
            return ("let", name, value, line)
        if self.match("KW", "print"):
            value = self.expr()
            self.expect("SYM", ";")
            return ("print", value, line)
        if self.match("KW", "if"):
            cond = self.expr()
            then = self.block()
            other = None
            if self.match("KW", "else"):
                other = self.statement() if self.check("KW", "if") else self.block()
            return ("if", cond, then, other, line)
        if self.match("KW", "while"):
            return ("while", self.expr(), self.block(), line)
        if self.match("KW", "return"):
            value = None if self.check("SYM", ";") else self.expr()
            self.expect("SYM", ";")
            return ("return", value, line)
        if self.check("SYM", "{"):
            return self.block()
        value = self.expr()
        self.expect("SYM", ";")
        return ("expr", value, line)

    # --- expressions -----------------------------------------------------
    def expr(self):
        return self.assignment()

    def assignment(self):
        left = self.or_()
        if self.check("SYM", "="):
            eq = self.advance()
            if left[0] != "var":
                raise TinyError("alvo de atribuição inválido", eq.line)
            return ("assign", left[1], self.assignment(), eq.line)
        return left

    def binary(self, sub, kind, *ops):
        left = sub()
        while (t := self.match(kind, *ops)):
            left = ("bin", t.value, left, sub(), t.line)
        return left

    def or_(self):
        left = self.and_()
        while (t := self.match("KW", "or")):
            left = ("logic", "or", left, self.and_(), t.line)
        return left

    def and_(self):
        left = self.equality()
        while (t := self.match("KW", "and")):
            left = ("logic", "and", left, self.equality(), t.line)
        return left

    def equality(self):
        return self.binary(self.compare, "SYM", "==", "!=")

    def compare(self):
        return self.binary(self.term, "SYM", "<", "<=", ">", ">=")

    def term(self):
        return self.binary(self.factor, "SYM", "+", "-")

    def factor(self):
        return self.binary(self.unary, "SYM", "*", "/", "%")

    def unary(self):
        if (t := self.match("SYM", "-")):
            return ("neg", self.unary(), t.line)
        if (t := self.match("KW", "not")):
            return ("not", self.unary(), t.line)
        return self.call()

    def call(self):
        expr = self.primary()
        while (t := self.match("SYM", "(")):
            args = []
            if not self.check("SYM", ")"):
                args.append(self.expr())
                while self.match("SYM", ","):
                    args.append(self.expr())
            self.expect("SYM", ")")
            expr = ("call", expr, args, t.line)
        return expr

    def primary(self):
        t = self.advance()
        if t.kind in ("NUM", "STR"):
            return ("lit", t.value)
        if t.kind == "KW" and t.value in ("true", "false", "nil"):
            return ("lit", {"true": True, "false": False, "nil": None}[t.value])
        if t.kind == "ID":
            return ("var", t.value, t.line)
        if t.kind == "SYM" and t.value == "(":
            e = self.expr()
            self.expect("SYM", ")")
            return e
        if t.kind == "KW" and t.value == "fn":
            self.expect("SYM", "(")
            params = []
            if not self.check("SYM", ")"):
                params.append(self.expect("ID").value)
                while self.match("SYM", ","):
                    params.append(self.expect("ID").value)
            self.expect("SYM", ")")
            return ("fn", params, self.block(), t.line)
        raise TinyError(f"expressão inesperada '{t.value}'", t.line)


def parse(src: str) -> list:
    return Parser(tokenize(src)).program()

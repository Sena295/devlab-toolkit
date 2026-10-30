"""Lexer for TinyLang, a small dynamically typed language (numbers, strings, functions, closures)."""
from __future__ import annotations

from dataclasses import dataclass

KEYWORDS = {"let", "fn", "if", "else", "while", "return", "true", "false", "nil", "and", "or", "not", "print"}
SYMBOLS = {"==", "!=", "<=", ">=", "+", "-", "*", "/", "%", "<", ">", "=", "(", ")", "{", "}", ",", ";"}


class TinyError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"linha {line}: {message}" if line else message)
        self.line = line


@dataclass(frozen=True)
class Token:
    kind: str  # NUM, STR, ID, KW, SYM, EOF
    value: object
    line: int


ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    i, line, n = 0, 1, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
        elif c in " \t\r":
            i += 1
        elif c == "#":  # comment to end of line
            while i < n and src[i] != "\n":
                i += 1
        elif c.isdigit():
            j = i
            while j < n and (src[j].isdigit() or (src[j] == "." and j + 1 < n and src[j + 1].isdigit())):
                j += 1
            text = src[i:j]
            tokens.append(Token("NUM", float(text) if "." in text else int(text), line))
            i = j
        elif c == '"':
            j, buf = i + 1, []
            while j < n and src[j] != '"':
                if src[j] == "\\" and j + 1 < n:
                    j += 1
                    if src[j] not in ESCAPES:
                        raise TinyError(f"escape inválido \\{src[j]}", line)
                    buf.append(ESCAPES[src[j]])
                else:
                    if src[j] == "\n":
                        line += 1
                    buf.append(src[j])
                j += 1
            if j >= n:
                raise TinyError("string não terminada", line)
            tokens.append(Token("STR", "".join(buf), line))
            i = j + 1
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            tokens.append(Token("KW" if word in KEYWORDS else "ID", word, line))
            i = j
        elif src[i:i + 2] in SYMBOLS:
            tokens.append(Token("SYM", src[i:i + 2], line))
            i += 2
        elif c in SYMBOLS:
            tokens.append(Token("SYM", c, line))
            i += 1
        else:
            raise TinyError(f"caractere inesperado {c!r}", line)
    tokens.append(Token("EOF", None, line))
    return tokens

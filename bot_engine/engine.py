"""Chat-bot command engine (platform independent).

Adapters for Discord/Telegram only need to call `Bot.handle(user, text)` and send back the reply,
so the engine can be tested offline. Exchange rates here are FICTITIOUS sample values.
"""
from __future__ import annotations

import heapq
import re
import shlex
import time
from dataclasses import dataclass, field
from typing import Callable

PREFIX = "!"
RATES_BRL = {"BRL": 1.0, "USD": 5.00, "EUR": 5.50, "GBP": 6.40, "ARS": 0.005}  # fictitious values
DURATION_RE = re.compile(r"^(\d+)([smhd])$")
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class BotError(Exception):
    """Error shown to the user as a friendly message."""


def parse_duration(text: str) -> int:
    m = DURATION_RE.match(text.lower())
    if not m or int(m[1]) == 0:
        raise BotError("duração inválida; exemplos: 30s, 10m, 2h, 1d")
    return int(m[1]) * UNITS[m[2]]


def convert(amount: float, src: str, dst: str) -> float:
    src, dst = src.upper(), dst.upper()
    for cur in (src, dst):
        if cur not in RATES_BRL:
            raise BotError(f"moeda desconhecida: {cur} (disponíveis: {', '.join(RATES_BRL)})")
    return amount * RATES_BRL[src] / RATES_BRL[dst]


def safe_eval(expr: str) -> float:
    """Arithmetic only (digits and + - * / ( ) .), evaluated by a small recursive parser, never eval()."""
    tokens = re.findall(r"\d+(?:\.\d+)?|[()+\-*/]", expr.replace(" ", ""))
    if "".join(tokens) != expr.replace(" ", "") or not tokens or re.search(r"\d\s+\d", expr):
        raise BotError("expressão inválida")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def eat():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def atom():
        t = peek()
        if t == "(":
            eat()
            v = add()
            if peek() != ")":
                raise BotError("parêntese não fechado")
            eat()
            return v
        if t == "-":
            eat()
            return -atom()
        if t is None or not t[0].isdigit():
            raise BotError("expressão inválida")
        return float(eat())

    def mul():
        v = atom()
        while peek() in ("*", "/"):
            op = eat()
            r = atom()
            if op == "/" and r == 0:
                raise BotError("divisão por zero")
            v = v * r if op == "*" else v / r
        return v

    def add():
        v = mul()
        while peek() in ("+", "-"):
            op = eat()
            r = mul()
            v = v + r if op == "+" else v - r
        return v

    result = add()
    if pos != len(tokens):
        raise BotError("expressão inválida")
    return result


@dataclass(order=True)
class Reminder:
    due: float
    user: str = field(compare=False)
    text: str = field(compare=False)


class Bot:
    def __init__(self, clock: Callable[[], float] = time.time, cooldown: float = 1.0) -> None:
        self.clock = clock
        self.cooldown = cooldown
        self.commands: dict[str, tuple[Callable, str]] = {}
        self.reminders: list[Reminder] = []
        self.last_call: dict[str, float] = {}
        self.polls: dict[str, dict[str, int]] = {}
        self._register_builtins()

    def command(self, name: str, help_text: str = ""):
        def deco(fn):
            self.commands[name] = (fn, help_text)
            return fn
        return deco

    def handle(self, user: str, text: str) -> str | None:
        if not text.startswith(PREFIX):
            return None
        try:
            parts = shlex.split(text[len(PREFIX):])
        except ValueError:
            return "Aspas não fechadas."
        if not parts:
            return None
        name, args = parts[0].lower(), parts[1:]
        if name not in self.commands:
            return f"Comando desconhecido: {name}. Use {PREFIX}ajuda."
        now = self.clock()
        if now - self.last_call.get(user, -1e9) < self.cooldown:
            return "Calma! Aguarde um instante antes do próximo comando."
        self.last_call[user] = now
        try:
            return self.commands[name][0](user, args)
        except BotError as e:
            return f"Erro: {e}"

    def due_reminders(self) -> list[Reminder]:
        out = []
        while self.reminders and self.reminders[0].due <= self.clock():
            out.append(heapq.heappop(self.reminders))
        return out

    def _register_builtins(self) -> None:
        @self.command("ajuda", "lista os comandos")
        def ajuda(user, args):
            return "Comandos: " + ", ".join(f"{PREFIX}{n}" + (f" ({h})" if h else "") for n, (_, h) in sorted(self.commands.items()))

        @self.command("ping", "teste de vida")
        def ping(user, args):
            return "pong"

        @self.command("calc", "calculadora: !calc 2*(3+4)")
        def calc(user, args):
            value = safe_eval(" ".join(args))
            return f"= {value:g}"

        @self.command("cotacao", "!cotacao 100 usd brl")
        def cotacao(user, args):
            if len(args) != 3:
                raise BotError(f"uso: {PREFIX}cotacao <valor> <de> <para>")
            try:
                amount = float(args[0].replace(",", "."))
            except ValueError:
                raise BotError("valor inválido") from None
            return f"{amount:,.2f} {args[1].upper()} = {convert(amount, args[1], args[2]):,.2f} {args[2].upper()} (cotação fictícia)"

        @self.command("lembrar", "!lembrar 10m \"tomar água\"")
        def lembrar(user, args):
            if len(args) < 2:
                raise BotError(f"uso: {PREFIX}lembrar <tempo> <texto>")
            delay = parse_duration(args[0])
            heapq.heappush(self.reminders, Reminder(self.clock() + delay, user, " ".join(args[1:])))
            return f"Ok, {user}! Lembro você em {args[0]}."

        @self.command("enquete", "!enquete criar <nome> | votar <nome> <opção> | ver <nome>")
        def enquete(user, args):
            if not args:
                raise BotError("uso: enquete criar|votar|ver")
            action, rest = args[0], args[1:]
            if action == "criar" and len(rest) >= 3:
                self.polls[rest[0]] = {opt: 0 for opt in rest[1:]}
                return f"Enquete '{rest[0]}' criada: {', '.join(rest[1:])}"
            if action in ("votar", "ver") and rest and rest[0] in self.polls:
                poll = self.polls[rest[0]]
                if action == "votar":
                    if len(rest) != 2 or rest[1] not in poll:
                        raise BotError("opção inválida")
                    poll[rest[1]] += 1
                total = sum(poll.values()) or 1
                return " | ".join(f"{o}: {n} ({100 * n // total}%)" for o, n in poll.items())
            raise BotError("enquete inexistente ou uso incorreto")


def repl() -> None:
    bot = Bot(cooldown=0)
    print("Bot de demonstração (Ctrl+C para sair). Tente !ajuda")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        reply = bot.handle("voce", line)
        if reply:
            print(reply)
        for r in bot.due_reminders():
            print(f"[lembrete para {r.user}] {r.text}")


if __name__ == "__main__":
    repl()

"""Auth service: register, login, refresh with rotation, role-based access, login throttling."""
from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass, field

from httpkit import App, HTTPError, Response

from .tokens import TokenError, decode_jwt, encode_jwt, hash_password, new_secret, verify_password

ACCESS_TTL = 15 * 60
REFRESH_TTL = 7 * 24 * 3600
MAX_ATTEMPTS = 5
LOCK_SECONDS = 300
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES = ("user", "editor", "admin")


@dataclass
class User:
    id: int
    email: str
    password_hash: str
    role: str = "user"
    failures: int = 0
    locked_until: float = 0.0


@dataclass
class AuthService:
    key: bytes = field(default_factory=new_secret)
    clock: callable = time.time
    iterations: int = 1_000  # low for tests; raise to the PBKDF2 default in real use
    users: dict[str, User] = field(default_factory=dict)
    refresh_tokens: dict[str, int] = field(default_factory=dict)  # token -> user id
    _next_id: int = 1

    def register(self, email: str, password: str, role: str = "user") -> User:
        email = email.strip().lower()
        if not EMAIL_RE.match(email):
            raise HTTPError(422, "e-mail inválido")
        if len(password) < 8 or password.isalpha() or password.isdigit():
            raise HTTPError(422, "senha fraca: mínimo 8 caracteres misturando letras e números")
        if role not in ROLES:
            raise HTTPError(422, "perfil inválido")
        if email in self.users:
            raise HTTPError(409, "e-mail já cadastrado")
        user = User(self._next_id, email, hash_password(password, self.iterations), role)
        self._next_id += 1
        self.users[email] = user
        return user

    def _issue(self, user: User) -> dict:
        now = self.clock()
        access = encode_jwt({"sub": user.id, "email": user.email, "role": user.role,
                             "iat": now, "exp": now + ACCESS_TTL}, self.key)
        refresh = secrets.token_urlsafe(32)
        self.refresh_tokens[refresh] = user.id
        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "expires_in": ACCESS_TTL}

    def login(self, email: str, password: str) -> dict:
        user = self.users.get(email.strip().lower())
        now = self.clock()
        if user and user.locked_until > now:
            raise HTTPError(429, "conta temporariamente bloqueada")
        # same error for unknown user and wrong password: do not leak which e-mails exist
        if not user or not verify_password(password, user.password_hash):
            if user:
                user.failures += 1
                if user.failures >= MAX_ATTEMPTS:
                    user.locked_until, user.failures = now + LOCK_SECONDS, 0
            raise HTTPError(401, "credenciais inválidas")
        user.failures = 0
        return self._issue(user)

    def refresh(self, token: str) -> dict:
        uid = self.refresh_tokens.pop(token, None)  # single use: rotation
        if uid is None:
            raise HTTPError(401, "refresh token inválido")
        user = next(u for u in self.users.values() if u.id == uid)
        return self._issue(user)

    def logout(self, token: str) -> None:
        self.refresh_tokens.pop(token, None)

    def authenticate(self, token: str | None) -> dict:
        if not token:
            raise HTTPError(401, "token ausente")
        try:
            return decode_jwt(token, self.key, self.clock())
        except TokenError as e:
            raise HTTPError(401, str(e)) from e


def require_role(claims: dict, *roles: str) -> None:
    if claims["role"] not in roles:
        raise HTTPError(403, "permissão insuficiente")


def create_app(svc: AuthService | None = None) -> App:
    svc = svc or AuthService()
    app = App()

    @app.route("POST", "/register")
    def register(req):
        b = req.require("email", "password")
        user = svc.register(b["email"], b["password"])  # role is never taken from the client
        return Response(201, {"id": user.id, "email": user.email, "role": user.role})

    @app.route("POST", "/login")
    def login(req):
        b = req.require("email", "password")
        return svc.login(b["email"], b["password"])

    @app.route("POST", "/refresh")
    def refresh(req):
        return svc.refresh(req.require("refresh_token")["refresh_token"])

    @app.route("POST", "/logout")
    def logout(req):
        svc.logout(req.require("refresh_token")["refresh_token"])
        return Response(204)

    @app.route("GET", "/me")
    def me(req):
        c = svc.authenticate(req.bearer())
        return {"id": c["sub"], "email": c["email"], "role": c["role"]}

    @app.route("GET", "/admin/users")
    def users(req):
        require_role(svc.authenticate(req.bearer()), "admin")
        return [{"id": u.id, "email": u.email, "role": u.role} for u in svc.users.values()]

    return app

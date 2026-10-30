"""Password hashing and JWT (HS256) implemented with the standard library.

Study implementation: in production prefer audited libraries (bcrypt/argon2, PyJWT).
No secret is stored in this repository: keys are generated at runtime or injected by the caller.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

PBKDF2_ITERATIONS = 200_000


class TokenError(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(iters))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, _unb64(digest))


def new_secret() -> bytes:
    return secrets.token_bytes(32)


def encode_jwt(payload: dict, key: bytes) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(key, f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64(sig)}"


def decode_jwt(token: str, key: bytes, now: float | None = None) -> dict:
    try:
        header_b64, body_b64, sig_b64 = token.split(".")
        header = json.loads(_unb64(header_b64))
    except (ValueError, json.JSONDecodeError) as e:
        raise TokenError("token malformado") from e
    if header.get("alg") != "HS256":  # blocks the classic alg=none / alg confusion attack
        raise TokenError("algoritmo não suportado")
    expected = hmac.new(key, f"{header_b64}.{body_b64}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _unb64(sig_b64)):
        raise TokenError("assinatura inválida")
    payload = json.loads(_unb64(body_b64))
    if payload.get("exp") is not None and payload["exp"] <= (now if now is not None else time.time()):
        raise TokenError("token expirado")
    return payload

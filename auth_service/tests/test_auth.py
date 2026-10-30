import unittest

from auth_service.service import AuthService, create_app
from auth_service.tokens import TokenError, decode_jwt, encode_jwt, hash_password, verify_password

PW = "Senha1234Forte"  # fictitious test password


class Clock:
    now = 10_000.0

    def __call__(self):
        return self.now


class TokenTests(unittest.TestCase):
    def test_password_hash(self):
        h = hash_password(PW, 1000)
        self.assertTrue(verify_password(PW, h))
        self.assertFalse(verify_password("outra", h))
        self.assertNotEqual(h, hash_password(PW, 1000))  # random salt
        self.assertFalse(verify_password(PW, "lixo"))

    def test_jwt_roundtrip_and_tamper(self):
        key = b"k" * 32
        tok = encode_jwt({"sub": 1, "exp": 100}, key)
        self.assertEqual(decode_jwt(tok, key, now=50)["sub"], 1)
        with self.assertRaises(TokenError):
            decode_jwt(tok, key, now=101)
        with self.assertRaises(TokenError):
            decode_jwt(tok, b"x" * 32, now=50)
        h, b, s = tok.split(".")
        with self.assertRaises(TokenError):
            decode_jwt(f"{h}.{b}x.{s}", key, now=50)
        with self.assertRaises(TokenError):
            decode_jwt("abc", key)

    def test_alg_none_rejected(self):
        import base64
        import json
        enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
        forged = f"{enc({'alg': 'none'})}.{enc({'sub': 1})}."
        with self.assertRaises(TokenError):
            decode_jwt(forged, b"k" * 32)


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.svc = AuthService(clock=self.clock)
        self.app = create_app(self.svc)

    def register(self, email="ana@example.com"):
        return self.app.call("POST", "/register", {"email": email, "password": PW})

    def login(self, email="ana@example.com", pw=PW):
        return self.app.call("POST", "/login", {"email": email, "password": pw})

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_register_validation(self):
        self.assertEqual(self.register().status, 201)
        self.assertEqual(self.register().status, 409)
        for body in ({"email": "x", "password": PW}, {"email": "a@b.co", "password": "curta1"},
                     {"email": "a@b.co", "password": "somenteletras"}):
            self.assertEqual(self.app.call("POST", "/register", body).status, 422)

    def test_privilege_escalation_blocked(self):
        r = self.app.call("POST", "/register", {"email": "evil@example.com", "password": PW, "role": "admin"})
        self.assertEqual(r.body["role"], "user")

    def test_login_and_me(self):
        self.register()
        tok = self.login().body["access_token"]
        self.assertEqual(self.app.call("GET", "/me", headers=self.auth(tok)).body["email"], "ana@example.com")
        self.assertEqual(self.app.call("GET", "/me").status, 401)

    def test_same_error_for_unknown_user_and_bad_password(self):
        self.register()
        a, b = self.login(pw="errada123A"), self.login(email="nao@example.com")
        self.assertEqual((a.status, a.body), (b.status, b.body))

    def test_refresh_rotation(self):
        self.register()
        first = self.login().body
        second = self.app.call("POST", "/refresh", {"refresh_token": first["refresh_token"]})
        self.assertEqual(second.status, 200)
        replay = self.app.call("POST", "/refresh", {"refresh_token": first["refresh_token"]})
        self.assertEqual(replay.status, 401)

    def test_logout_revokes_refresh(self):
        self.register()
        rt = self.login().body["refresh_token"]
        self.app.call("POST", "/logout", {"refresh_token": rt})
        self.assertEqual(self.app.call("POST", "/refresh", {"refresh_token": rt}).status, 401)

    def test_access_token_expires(self):
        self.register()
        tok = self.login().body["access_token"]
        self.clock.now += 16 * 60
        self.assertEqual(self.app.call("GET", "/me", headers=self.auth(tok)).status, 401)

    def test_lockout_after_failures(self):
        self.register()
        for _ in range(5):
            self.assertEqual(self.login(pw="errada123A").status, 401)
        self.assertEqual(self.login().status, 429)  # even the right password is refused
        self.clock.now += 301
        self.assertEqual(self.login().status, 200)

    def test_rbac_admin_route(self):
        self.svc.register("root@example.com", PW, role="admin")
        self.register()
        admin = self.login("root@example.com").body["access_token"]
        user = self.login().body["access_token"]
        self.assertEqual(self.app.call("GET", "/admin/users", headers=self.auth(user)).status, 403)
        self.assertEqual(len(self.app.call("GET", "/admin/users", headers=self.auth(admin)).body), 2)


if __name__ == "__main__":
    unittest.main()

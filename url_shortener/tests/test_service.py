import json
import threading
import unittest
import urllib.request

from httpkit import App
from url_shortener.service import Shortener, create_app, decode_base62, encode_base62


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Base62Tests(unittest.TestCase):
    def test_roundtrip(self):
        for n in (0, 1, 61, 62, 3844, 10**12):
            self.assertEqual(decode_base62(encode_base62(n)), n)

    def test_negative(self):
        with self.assertRaises(ValueError):
            encode_base62(-1)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.app = create_app(Shortener(clock=self.clock))

    def make(self, **body):
        body.setdefault("url", "https://example.com/pagina")
        return self.app.call("POST", "/api/links", body)

    def test_create_and_redirect(self):
        r = self.make()
        self.assertEqual(r.status, 201)
        go = self.app.call("GET", "/" + r.body["code"])
        self.assertEqual(go.status, 302)
        self.assertEqual(go.headers["Location"], "https://example.com/pagina")

    def test_invalid_urls(self):
        for bad in ("ftp://x.com", "javascript:alert(1)", "sem-esquema", "https://"):
            self.assertEqual(self.make(url=bad).status, 422, bad)

    def test_alias_rules(self):
        self.assertEqual(self.make(alias="meu-link").status, 201)
        self.assertEqual(self.make(alias="meu-link").status, 409)
        self.assertEqual(self.make(alias="a b").status, 422)
        self.assertEqual(self.make(alias="api").status, 422)

    def test_expiry(self):
        code = self.make(ttl=60).body["code"]
        self.assertEqual(self.app.call("GET", "/" + code).status, 302)
        self.clock.now += 61
        self.assertEqual(self.app.call("GET", "/" + code).status, 410)

    def test_stats_and_top(self):
        a = self.make(alias="aaa").body["code"]
        b = self.make(alias="bbb").body["code"]
        for _ in range(3):
            self.app.call("GET", "/" + a, headers={"Referer": "https://blog.example"})
        self.app.call("GET", "/" + a)
        self.app.call("GET", "/" + b)
        st = self.app.call("GET", f"/api/links/{a}/stats").body
        self.assertEqual(st["clicks"], 4)
        self.assertEqual(st["referers"], {"https://blog.example": 3, "direto": 1})
        self.assertEqual(self.app.call("GET", "/api/top?limit=1").body[0]["code"], "aaa")

    def test_errors(self):
        self.assertEqual(self.app.call("GET", "/naoexiste").status, 404)
        self.assertEqual(self.app.call("POST", "/api/links", {}).status, 422)
        self.assertEqual(self.app.call("DELETE", "/api/top").status, 405)


class HttpIntegrationTests(unittest.TestCase):
    def test_over_real_socket(self):
        server = create_app().serve(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            req = urllib.request.Request(base + "/api/links", data=json.dumps({"url": "https://example.com"}).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 201)
                self.assertIn("code", json.load(resp))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()

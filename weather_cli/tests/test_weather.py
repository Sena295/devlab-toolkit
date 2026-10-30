import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from weather_cli import weather as w

GEO = {"results": [{"name": "Cidade Exemplo", "country": "Brasil", "latitude": -23.5, "longitude": -46.6}]}
FORECAST = {
    "current": {"temperature_2m": 24.4, "relative_humidity_2m": 70, "wind_speed_10m": 12.3, "weather_code": 2},
    "daily": {"time": ["2025-03-10", "2025-03-11"], "temperature_2m_max": [28.0, 26.5],
              "temperature_2m_min": [19.0, 18.2], "precipitation_probability_max": [10, None], "weather_code": [0, 63]},
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class ParsingTests(unittest.TestCase):
    def test_place(self):
        self.assertEqual(w.parse_place(GEO)["name"], "Cidade Exemplo")
        with self.assertRaises(w.WeatherError):
            w.parse_place({})

    def test_forecast_and_render(self):
        fc = w.parse_forecast(FORECAST)
        self.assertEqual(len(fc["days"]), 2)
        out = w.render(w.parse_place(GEO), fc)
        self.assertIn("Cidade Exemplo, Brasil", out)
        self.assertIn("Parcialmente nublado: 24°C", out)
        self.assertIn("seg 03-10", out)
        self.assertIn("Chuva", out)

    def test_bad_payload(self):
        with self.assertRaises(w.WeatherError):
            w.parse_forecast({"current": {}})

    def test_describe_unknown_code(self):
        self.assertEqual(w.describe(1234)[0], "Condição desconhecida")

    def test_url_building(self):
        self.assertEqual(w.build_url("http://x", a=1, b="á b"), "http://x?a=1&b=%C3%A1+b")


class FetchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cache_prevents_second_request(self):
        calls = []

        def opener(url, timeout):
            calls.append(url)
            return FakeResponse(json.dumps(GEO).encode())
        self.assertEqual(w.fetch_json("http://x/a", self.dir, opener=opener), GEO)
        self.assertEqual(w.fetch_json("http://x/a", self.dir, opener=opener), GEO)
        self.assertEqual(len(calls), 1)

    def test_offline_falls_back_to_stale_cache(self):
        ok = lambda url, timeout: FakeResponse(json.dumps(GEO).encode())
        w.fetch_json("http://x/a", self.dir, opener=ok)

        def down(url, timeout):
            raise urllib.error.URLError("offline")
        self.assertEqual(w.fetch_json("http://x/a", self.dir, ttl=0, opener=down), GEO)

    def test_offline_without_cache_raises(self):
        def down(url, timeout):
            raise urllib.error.URLError("offline")
        with self.assertRaises(w.WeatherError):
            w.fetch_json("http://x/b", self.dir, opener=down)


if __name__ == "__main__":
    unittest.main()

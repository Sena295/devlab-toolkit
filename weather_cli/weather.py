"""Weather CLI using the public Open-Meteo API (no key required) with disk cache and offline fallback.

Parsing and formatting are pure functions, so tests use a recorded fixture and never touch the network.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL = 15 * 60
CACHE_DIR = Path.home() / ".cache" / "devlab-weather"

WMO = {
    0: ("Céu limpo", "☀"), 1: ("Predomínio de sol", "🌤"), 2: ("Parcialmente nublado", "⛅"), 3: ("Nublado", "☁"),
    45: ("Neblina", "🌫"), 48: ("Neblina com geada", "🌫"), 51: ("Garoa leve", "🌦"), 53: ("Garoa", "🌦"),
    55: ("Garoa forte", "🌧"), 61: ("Chuva fraca", "🌧"), 63: ("Chuva", "🌧"), 65: ("Chuva forte", "🌧"),
    71: ("Neve fraca", "❄"), 73: ("Neve", "❄"), 75: ("Neve forte", "❄"), 80: ("Pancadas de chuva", "🌦"),
    95: ("Trovoada", "⛈"), 96: ("Trovoada com granizo", "⛈"), 99: ("Trovoada forte", "⛈"),
}
WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


class WeatherError(Exception):
    pass


def describe(code: int) -> tuple[str, str]:
    return WMO.get(code, ("Condição desconhecida", "?"))


def build_url(base: str, **params) -> str:
    return base + "?" + urllib.parse.urlencode(params)


def parse_place(payload: dict) -> dict:
    results = payload.get("results") or []
    if not results:
        raise WeatherError("cidade não encontrada")
    r = results[0]
    return {"name": r["name"], "country": r.get("country", ""), "lat": r["latitude"], "lon": r["longitude"]}


def parse_forecast(payload: dict) -> dict:
    try:
        cur = payload["current"]
        daily = payload["daily"]
        days = [
            {"date": d, "max": hi, "min": lo, "rain": rain, "code": code}
            for d, hi, lo, rain, code in zip(daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"],
                                             daily["precipitation_probability_max"], daily["weather_code"])
        ]
        return {"temp": cur["temperature_2m"], "wind": cur["wind_speed_10m"], "humidity": cur["relative_humidity_2m"],
                "code": cur["weather_code"], "days": days}
    except (KeyError, TypeError) as e:
        raise WeatherError(f"resposta inesperada da API: {e}") from e


def weekday_abbr(iso_date: str) -> str:
    from datetime import date
    return WEEKDAYS[date.fromisoformat(iso_date).weekday()]


def render(place: dict, fc: dict) -> str:
    label, icon = describe(fc["code"])
    lines = [f"{place['name']}, {place['country']}", f"{icon} {label}: {fc['temp']:.0f}°C  "
             f"umidade {fc['humidity']}%  vento {fc['wind']:.0f} km/h", ""]
    for d in fc["days"]:
        text, ic = describe(d["code"])
        lines.append(f"  {weekday_abbr(d['date'])} {d['date'][5:]}  {d['min']:>4.0f}° / {d['max']:<4.0f}° "
                     f"chuva {d['rain'] if d['rain'] is not None else '-':>3}%  {ic} {text}")
    return "\n".join(lines)


def fetch_json(url: str, cache_dir: Path = CACHE_DIR, ttl: int = CACHE_TTL, opener=urllib.request.urlopen) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = cache_dir / (urllib.parse.quote(url, safe="")[-120:] + ".json")
    if key.exists() and time.time() - key.stat().st_mtime < ttl:
        return json.loads(key.read_text(encoding="utf-8"))
    try:
        with opener(url, timeout=10) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        if key.exists():  # stale data is better than no data
            return json.loads(key.read_text(encoding="utf-8"))
        raise WeatherError(f"falha ao consultar a API: {e}") from e
    key.write_text(json.dumps(data), encoding="utf-8")
    return data


def forecast_for(city: str, days: int = 5, **kw) -> str:
    place = parse_place(fetch_json(build_url(GEOCODE_URL, name=city, count=1, language="pt"), **kw))
    data = fetch_json(build_url(
        FORECAST_URL, latitude=place["lat"], longitude=place["lon"], timezone="auto", forecast_days=days,
        current="temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        daily="temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"), **kw)
    return render(place, parse_forecast(data))


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Previsão do tempo (Open-Meteo)")
    p.add_argument("city")
    p.add_argument("--days", type=int, default=5, choices=range(1, 8))
    args = p.parse_args(argv)
    try:
        print(forecast_for(args.city, args.days))
    except WeatherError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

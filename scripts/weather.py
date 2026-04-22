#!/usr/bin/env python3
"""Render a Singapore weather + live-clock card SVG from wttr.in.

wttr.in returns JSON with no API key needed. If the request fails, fall back to a
"clock-only" card so the workflow never blocks on upstream flakiness.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "images" / "sg-card.svg"
SGT = timezone(timedelta(hours=8))

ICONS = {
    "sun":     "☀",
    "cloud":   "☁",
    "rain":    "🌧",
    "thunder": "⛈",
    "fog":     "🌫",
    "night":   "🌙",
}


def classify(desc: str, hour: int) -> str:
    d = (desc or "").lower()
    if "thunder" in d or "storm" in d:
        return "thunder"
    if "rain" in d or "drizzle" in d or "shower" in d:
        return "rain"
    if "fog" in d or "mist" in d or "haze" in d:
        return "fog"
    if "cloud" in d or "overcast" in d:
        return "cloud"
    if hour < 6 or hour >= 19:
        return "night"
    return "sun"


def fetch_weather() -> dict | None:
    try:
        req = urllib.request.Request(
            "https://wttr.in/Singapore?format=j1",
            headers={"User-Agent": "sg-card-generator"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"wttr fetch failed: {exc}", file=sys.stderr)
        return None


def extract(data: dict | None) -> dict:
    if not data:
        return {"temp": "—", "desc": "offline", "feels": "—", "humidity": "—", "sunrise": "—", "sunset": "—"}
    cur = (data.get("current_condition") or [{}])[0]
    today = (data.get("weather") or [{}])[0]
    astro = (today.get("astronomy") or [{}])[0]
    return {
        "temp": cur.get("temp_C", "—"),
        "desc": (cur.get("weatherDesc") or [{"value": "—"}])[0]["value"],
        "feels": cur.get("FeelsLikeC", "—"),
        "humidity": cur.get("humidity", "—"),
        "sunrise": astro.get("sunrise", "—"),
        "sunset": astro.get("sunset", "—"),
    }


SVG_TMPL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 220" width="480" height="220" role="img" aria-label="singapore weather">
  <title>jason.sg-card.svg — {desc}</title>
  <defs>
    <linearGradient id="skyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{sky_a}"/>
      <stop offset="100%" stop-color="{sky_b}"/>
    </linearGradient>
  </defs>
  <rect width="480" height="220" rx="14" fill="url(#skyGrad)"/>
  <rect x="0.5" y="0.5" width="479" height="219" rx="14" fill="none" stroke="#3c3836"/>

  <g font-family="ui-monospace,'Fira Code','JetBrains Mono',monospace">
    <text x="24" y="36" font-size="12" fill="#ebdbb2" opacity="0.7">Singapore · SGT</text>
    <text x="456" y="36" font-size="13" fill="#ebdbb2" text-anchor="end">{stamp}</text>

    <text x="24" y="96" font-size="52" fill="#fabd2f" font-weight="900">{icon}</text>
    <text x="96" y="88" font-size="38" fill="#ebdbb2" font-weight="900">{temp}°C</text>
    <text x="96" y="112" font-size="13" fill="#d5c4a1">feels like {feels}° · {humidity}% humidity</text>

    <text x="24" y="148" font-size="14" fill="#ebdbb2">{desc}</text>

    <text x="24" y="184" font-size="11" fill="#a89984">sunrise {sunrise}</text>
    <text x="240" y="184" font-size="11" fill="#a89984">sunset {sunset}</text>
    <text x="24" y="202" font-size="10" fill="#928374">source: wttr.in · refreshed hourly</text>
  </g>
</svg>
"""

SKY_PALETTES = {
    "sun":     ("#458588", "#1d2021"),
    "cloud":   ("#3c3836", "#1d2021"),
    "rain":    ("#0072B2", "#1d2021"),
    "thunder": ("#504945", "#1d2021"),
    "fog":     ("#665c54", "#282828"),
    "night":   ("#1d1b2e", "#0f0d1a"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    data = fetch_weather()
    w = extract(data)
    now = datetime.now(SGT)
    kind = classify(w["desc"], now.hour)
    icon = ICONS[kind]
    sky_a, sky_b = SKY_PALETTES[kind]

    svg = SVG_TMPL.format(
        icon=icon,
        temp=w["temp"],
        feels=w["feels"],
        humidity=w["humidity"],
        desc=w["desc"],
        sunrise=w["sunrise"],
        sunset=w["sunset"],
        sky_a=sky_a,
        sky_b=sky_b,
        stamp=now.strftime("%a %d %b · %H:%M"),
    )
    args.out.write_text(svg, encoding="utf-8")
    print(f"wrote {args.out} ({kind} {w['temp']}°C)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

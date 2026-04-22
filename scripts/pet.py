#!/usr/bin/env python3
"""Render a Tamagotchi-style ASCII pet SVG.

State derived from `days since last public push`:
  0-1 happy, 2-6 chill, 7-13 hungry, 14+ starved.

Species derived from top language:
  Python   -> snake
  JS/TS    -> caterpillar
  C/C++    -> crab
  Go       -> gopher
  Rust     -> crab
  default  -> blob

Testing:
  GH_USER=jasonmatthewsuhari GITHUB_TOKEN=... python scripts/pet.py
  DAYS=9 LANG=Python python scripts/pet.py     # skip API, force values
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
DEFAULT_OUT = ROOT / "images" / "pet.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        pushedAt
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

PETS = {
    "snake":       ["  ___", " (o.o)", "  >^<", " ~~~~~~~"],
    "caterpillar": ["(o-.-o)   ___", " \\_||_/~~~|__|~~~___", "       \\___/   \\___/"],
    "crab":        [" (v)_(v) ", " /(o.o)\\ ", " /  _  \\ "],
    "gopher":      ["   _____", "  / o o \\", " |   ^   |", "  \\_---_/"],
    "blob":        ["  _____", " (     )", "  ^   ^", " smile"],
}

MOOD = {
    "happy":   {"face": "(^o^)/", "msg": "bonded with jason, hp full", "color": "#b8bb26"},
    "chill":   {"face": "(-_-)",  "msg": "content. quiet day.",         "color": "#8ec07c"},
    "hungry":  {"face": "(ಠ_ಠ)",  "msg": "feed me commits",             "color": "#fabd2f"},
    "starved": {"face": "(x_x)",  "msg": "starved... needs a push",     "color": "#fb4934"},
}


def gh_graphql(token: str, login: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "pet-gen"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]["user"]


def days_since_push(user_data: dict) -> int:
    repos = user_data["repositories"]["nodes"]
    latest = None
    for r in repos:
        ts = r.get("pushedAt")
        if not ts:
            continue
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if latest is None or dt > latest:
            latest = dt
    if latest is None:
        return 30
    return (datetime.now(timezone.utc) - latest).days


def top_language(user_data: dict) -> str:
    totals: dict[str, int] = {}
    for r in user_data["repositories"]["nodes"]:
        for e in (r.get("languages") or {}).get("edges", []) or []:
            totals[e["node"]["name"]] = totals.get(e["node"]["name"], 0) + (e["size"] or 0)
    if not totals:
        return "unknown"
    return max(totals.items(), key=lambda kv: kv[1])[0]


def pick_species(lang: str) -> str:
    lang = (lang or "").lower()
    if lang == "python":
        return "snake"
    if lang in ("javascript", "typescript"):
        return "caterpillar"
    if lang in ("c", "c++", "cpp"):
        return "crab"
    if lang == "go":
        return "gopher"
    if lang == "rust":
        return "crab"
    return "blob"


def pick_mood(days: int) -> str:
    if days <= 1:
        return "happy"
    if days <= 6:
        return "chill"
    if days <= 13:
        return "hungry"
    return "starved"


def render(species: str, mood_key: str, days: int, lang: str) -> str:
    mood = MOOD[mood_key]
    art = PETS.get(species, PETS["blob"])
    # pad art to 4 lines
    while len(art) < 4:
        art.append("")
    art_lines = "".join(
        f'<tspan x="40" dy="{22 if i else 0}">{line}</tspan>' for i, line in enumerate(art)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 280" width="480" height="280" role="img" aria-label="tamagotchi pet">
  <title>jason.pet.svg — {species} ({mood_key})</title>
  <defs>
    <linearGradient id="screenGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a89984" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="#1d2021"/>
    </linearGradient>
  </defs>
  <rect width="480" height="280" fill="#CC79A7" rx="120"/>
  <rect x="60" y="36" width="360" height="208" rx="18" fill="#1d2021"/>
  <rect x="68" y="44" width="344" height="192" rx="12" fill="url(#screenGrad)"/>
  <rect x="68" y="44" width="344" height="192" rx="12" fill="none" stroke="#3c3836"/>

  <g font-family="ui-monospace,'Fira Code','JetBrains Mono',monospace">
    <text x="82" y="72" font-size="11" fill="#928374">jason.pet · {species} · day {days} since push</text>
    <text x="82" y="92" font-size="18" fill="{mood['color']}" font-weight="700">{mood['face']}</text>

    <text x="40" y="140" font-size="13" fill="#ebdbb2">{art_lines}</text>

    <text x="82" y="200" font-size="12" fill="#d5c4a1">status: {mood_key}</text>
    <text x="82" y="218" font-size="12" fill="#a89984">"{mood['msg']}"</text>
  </g>

  <!-- buttons -->
  <circle cx="130" cy="260" r="10" fill="#3c3836" stroke="#ebdbb2"/>
  <circle cx="240" cy="260" r="10" fill="#3c3836" stroke="#ebdbb2"/>
  <circle cx="350" cy="260" r="10" fill="#3c3836" stroke="#ebdbb2"/>
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default=os.environ.get("GH_USER", "jasonmatthewsuhari"))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    # env overrides for testing without an API call
    force_days = os.environ.get("DAYS")
    force_lang = os.environ.get("LANG_OVERRIDE")

    if force_days is not None and force_lang is not None:
        days = int(force_days)
        lang = force_lang
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GITHUB_TOKEN not set (or pass DAYS=... LANG_OVERRIDE=...)", file=sys.stderr)
            return 2
        data = gh_graphql(token, args.user)
        days = days_since_push(data)
        lang = top_language(data)

    species = pick_species(lang)
    mood_key = pick_mood(days)
    svg = render(species, mood_key, days, lang)
    args.out.write_text(svg, encoding="utf-8")
    print(f"wrote {args.out} ({species}, {mood_key}, {days}d since push, lang={lang})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

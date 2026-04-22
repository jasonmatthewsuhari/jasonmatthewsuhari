#!/usr/bin/env python3
"""Render a JRPG-style character sheet SVG from GitHub stats.

LVL = floor(public_repos / 5)
HP  = commits in last 365 days
STR = merged PRs (lifetime)
DEX = issues opened (lifetime)
INT = distinct languages across public repos
CHA = followers

Equipment = top 4 languages by bytes
Boss = "Unemployment", HP counts down days until graduation (2027-05-15)

Uses GraphQL via GITHUB_TOKEN. Testing:
  GH_USER=jasonmatthewsuhari GITHUB_TOKEN=... python scripts/rpg_sheet.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "images" / "rpg-sheet.svg"
GRADUATION = date(2027, 5, 15)
COURSE_START = date(2023, 8, 1)

QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    followers { totalCount }
    pullRequests(states: MERGED) { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def gh_graphql(token: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "rpg-sheet-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]["user"]


def aggregate(user: dict) -> dict:
    repos = user["repositories"]["nodes"]
    public_repos = user["repositories"]["totalCount"]
    lang_bytes: dict[str, int] = {}
    lang_color: dict[str, str] = {}
    total_stars = 0
    for r in repos:
        total_stars += r.get("stargazerCount", 0) or 0
        for edge in (r.get("languages") or {}).get("edges", []) or []:
            name = edge["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + (edge.get("size") or 0)
            lang_color[name] = edge["node"].get("color") or "#a89984"

    top_langs = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)
    commits = user["contributionsCollection"]["totalCommitContributions"]

    return {
        "login": user["login"],
        "lvl": max(1, public_repos // 5),
        "hp": max(commits, 1),
        "hp_cap": max(commits, 500),
        "str": user["pullRequests"]["totalCount"],
        "dex": user["issues"]["totalCount"],
        "int": len(lang_bytes),
        "cha": user["followers"]["totalCount"],
        "stars": total_stars,
        "repos": public_repos,
        "top_langs": top_langs[:4],
        "lang_colors": lang_color,
    }


def boss_hp() -> tuple[int, int]:
    total = (GRADUATION - COURSE_START).days
    remaining = max(0, (GRADUATION - date.today()).days)
    return remaining, total


SVG_TMPL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 520" width="820" height="520" role="img" aria-label="character sheet">
  <title>jason.character_sheet.svg</title>
  <defs>
    <linearGradient id="hpGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#b8bb26"/>
      <stop offset="100%" stop-color="#8ec07c"/>
    </linearGradient>
    <linearGradient id="mpGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#83a598"/>
      <stop offset="100%" stop-color="#458588"/>
    </linearGradient>
    <linearGradient id="bossGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#fb4934"/>
      <stop offset="100%" stop-color="#cc241d"/>
    </linearGradient>
    <linearGradient id="panel" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#282828"/>
      <stop offset="100%" stop-color="#1d2021"/>
    </linearGradient>
    <filter id="panGlow" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="0.6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>
    .lbl {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 12px; fill:#a89984; }}
    .val {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 14px; fill:#ebdbb2; font-weight:700; }}
    .name {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 22px; fill:#fabd2f; font-weight:900; }}
    .sub {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 11px; fill:#928374; }}
    .head {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 13px; fill:#d5c4a1; font-weight:700; }}
    .stat {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 13px; fill:#ebdbb2; }}
    .pct {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 11px; fill:#d5c4a1; }}
    .boss {{ font-family: ui-monospace,'Fira Code','JetBrains Mono',monospace; font-size: 14px; fill:#fb4934; font-weight:700; }}
  </style>

  <rect width="820" height="520" fill="url(#panel)" rx="14"/>
  <rect x="0.5" y="0.5" width="819" height="519" rx="14" fill="none" stroke="#3c3836"/>

  <!-- Header -->
  <text x="24" y="36" class="name">CHARACTER SHEET · /home/jason</text>
  <text x="24" y="56" class="sub">class: DATA_SCIENTIST · subclass: INDIE_DEV · alignment: chaotic-neutral</text>

  <!-- Portrait -->
  <rect x="24" y="80" width="168" height="168" fill="#1d2021" stroke="#3c3836" rx="6"/>
  <g transform="translate(40,96)">
    <!-- pixel avatar (24x24 blocks, 6px each) -->
    {avatar}
  </g>
  <text x="108" y="266" class="head" text-anchor="middle">{login}</text>
  <text x="108" y="282" class="sub" text-anchor="middle">LVL {lvl} · {repos} repos · ⭐ {stars}</text>

  <!-- HP bar -->
  <text x="216" y="96"  class="lbl">HP · commits this year</text>
  <rect x="216" y="104" width="380" height="20" rx="10" fill="#3c3836"/>
  <rect x="216" y="104" width="0" height="20" rx="10" fill="url(#hpGrad)" filter="url(#panGlow)">
    <animate attributeName="width" from="0" to="{hp_bar}" begin="0.1s" dur="1.4s" fill="freeze" calcMode="spline" keySplines="0.2 0.6 0.3 1"/>
  </rect>
  <text x="610" y="119" class="val">{hp} / {hp_cap}</text>

  <!-- MP bar (followers as 'audience') -->
  <text x="216" y="138" class="lbl">MP · followers</text>
  <rect x="216" y="146" width="380" height="16" rx="8" fill="#3c3836"/>
  <rect x="216" y="146" width="0" height="16" rx="8" fill="url(#mpGrad)" filter="url(#panGlow)">
    <animate attributeName="width" from="0" to="{mp_bar}" begin="0.25s" dur="1.3s" fill="freeze" calcMode="spline" keySplines="0.2 0.6 0.3 1"/>
  </rect>
  <text x="610" y="159" class="val">{cha}</text>

  <!-- Stat grid -->
  <g transform="translate(216,184)">
    <rect x="0"   y="0" width="88" height="56" rx="6" fill="#1d2021" stroke="#3c3836"/>
    <text x="44"  y="20" class="lbl" text-anchor="middle">STR</text>
    <text x="44"  y="44" class="stat" text-anchor="middle">{str_}</text>
    <text x="44"  y="56" class="pct" text-anchor="middle">PRs merged</text>
    <rect x="96"  y="0" width="88" height="56" rx="6" fill="#1d2021" stroke="#3c3836"/>
    <text x="140" y="20" class="lbl" text-anchor="middle">DEX</text>
    <text x="140" y="44" class="stat" text-anchor="middle">{dex_}</text>
    <text x="140" y="56" class="pct" text-anchor="middle">issues opened</text>
    <rect x="192" y="0" width="88" height="56" rx="6" fill="#1d2021" stroke="#3c3836"/>
    <text x="236" y="20" class="lbl" text-anchor="middle">INT</text>
    <text x="236" y="44" class="stat" text-anchor="middle">{int_}</text>
    <text x="236" y="56" class="pct" text-anchor="middle">languages</text>
    <rect x="288" y="0" width="88" height="56" rx="6" fill="#1d2021" stroke="#3c3836"/>
    <text x="332" y="20" class="lbl" text-anchor="middle">CHA</text>
    <text x="332" y="44" class="stat" text-anchor="middle">{cha}</text>
    <text x="332" y="56" class="pct" text-anchor="middle">followers</text>
  </g>

  <!-- Equipment -->
  <text x="24" y="318" class="head">EQUIPMENT</text>
  <g transform="translate(24,330)">
    {equipment}
  </g>

  <!-- Boss fight -->
  <rect x="24" y="412" width="772" height="84" rx="10" fill="#1d2021" stroke="#fb4934" stroke-width="1.5"/>
  <text x="40" y="438" class="boss">⚔  CURRENT BOSS: UNEMPLOYMENT (LVL 99)</text>
  <text x="40" y="456" class="sub">graduation target: {grad} · {days_left} days remain before the encounter</text>
  <rect x="40" y="466" width="720" height="16" rx="8" fill="#3c3836"/>
  <rect x="40" y="466" width="0" height="16" rx="8" fill="url(#bossGrad)" filter="url(#panGlow)">
    <animate attributeName="width" from="0" to="{boss_hp_bar}" begin="0.6s" dur="1.6s" fill="freeze" calcMode="spline" keySplines="0.2 0.6 0.3 1"/>
  </rect>
  <text x="756" y="478" class="val" text-anchor="end">{days_left} HP</text>
</svg>
"""


def make_avatar() -> str:
    """A 24x24 pixel self-portrait built from hardcoded bitmap data."""
    # 24 rows of 24 chars: "." = transparent, "s" = skin, "h" = hair, "g" = glasses, "r" = shirt
    rows = [
        "........................",
        "........................",
        "...........hhhh.........",
        "..........hhhhhh........",
        ".........hhhhhhhh.......",
        "........hhhhhhhhhh......",
        ".......hssssssssssh.....",
        "......hsssssssssssh.....",
        "......hsssgssggssh......",
        "......hsssgssggsssh.....",
        "......hssssssssssssh....",
        "......hssssssmmssssh....",
        "......hssssmmmmssssh....",
        ".......hsssssssssh......",
        "........hsssssssh.......",
        ".........hsssssh........",
        "........rrrrrrrrr.......",
        ".......rrrrrrrrrrr......",
        "......rrrrrrrrrrrrr.....",
        "......rrrrrrrrrrrrr.....",
        "......rrrrrrrrrrrrr.....",
        "......rrrrrrrrrrrrr.....",
        "......rrrrrrrrrrrrr.....",
        "......rrrrrrrrrrrrr.....",
    ]
    palette = {"s": "#e4b592", "h": "#2b1d14", "g": "#1d2021", "r": "#458588", "m": "#CC79A7"}
    out = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            out.append(f'<rect x="{x*6}" y="{y*6}" width="6" height="6" fill="{palette[ch]}"/>')
    return "\n    ".join(out)


def render_equipment(top_langs: list[tuple[str, int]], lang_colors: dict[str, str]) -> str:
    if not top_langs:
        return '<text x="0" y="20" class="sub">no data</text>'
    slots = ["⚔ weapon", "🛡 shield", "👢 boots", "💍 ring"]
    out = []
    total = sum(b for _, b in top_langs) or 1
    for i, ((name, b), slot) in enumerate(zip(top_langs, slots)):
        x = i * 192
        pct = 100 * b / total
        color = lang_colors.get(name, "#ebdbb2")
        out.append(
            f'<g transform="translate({x},0)">'
            f'<rect x="0" y="0" width="180" height="68" rx="8" fill="#1d2021" stroke="#3c3836"/>'
            f'<rect x="8" y="8" width="16" height="16" rx="4" fill="{color}"/>'
            f'<text x="32" y="22" class="lbl">{slot}</text>'
            f'<text x="32" y="42" class="val">{name}</text>'
            f'<text x="32" y="58" class="pct">+{pct:.0f}% affinity</text>'
            f'</g>'
        )
    return "\n    ".join(out)


def render(stats: dict) -> str:
    days_left, total = boss_hp()
    boss_pct = days_left / total if total else 0
    hp_ratio = stats["hp"] / stats["hp_cap"] if stats["hp_cap"] else 0
    mp_ratio = min(1.0, stats["cha"] / 100)
    return SVG_TMPL.format(
        avatar=make_avatar(),
        login=stats["login"],
        lvl=stats["lvl"],
        repos=stats["repos"],
        stars=stats["stars"],
        hp=stats["hp"],
        hp_cap=stats["hp_cap"],
        hp_bar=f"{380 * hp_ratio:.1f}",
        mp_bar=f"{380 * mp_ratio:.1f}",
        str_=stats["str"],
        dex_=stats["dex"],
        int_=stats["int"],
        cha=stats["cha"],
        equipment=render_equipment(stats["top_langs"], stats["lang_colors"]),
        grad=GRADUATION.isoformat(),
        days_left=days_left,
        boss_hp_bar=f"{720 * boss_pct:.1f}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default=os.environ.get("GH_USER", "jasonmatthewsuhari"))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set", file=sys.stderr)
        return 2

    user = gh_graphql(token, {"login": args.user})
    stats = aggregate(user)
    svg = render(stats)
    args.out.write_text(svg, encoding="utf-8")
    print(f"wrote {args.out} (lvl {stats['lvl']}, hp {stats['hp']}, stars {stats['stars']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

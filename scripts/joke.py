#!/usr/bin/env python3
"""Pick the joke-of-the-day deterministically and rewrite the JOKE block in README.md."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_README = ROOT / "README.md"
JOKES = ROOT / "data" / "jokes.json"

START = "<!-- JOKE:START -->"
END = "<!-- JOKE:END -->"


def pick(today: date) -> str:
    pool = json.loads(JOKES.read_text(encoding="utf-8"))["jokes"]
    if not pool:
        return "the joke pool is empty. that's the joke."
    h = int(hashlib.sha1(today.isoformat().encode()).hexdigest(), 16)
    return pool[h % len(pool)]


def render_block(joke: str, today: date) -> str:
    safe = joke.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"{START}\n"
        f"> 🃏 **joke of the day** — _{today.isoformat()}_\n"
        f"> \n"
        f"> {safe}\n"
        f"{END}"
    )


def update_readme(readme: Path, block: str) -> bool:
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise RuntimeError("JOKE markers not found")
    before = text.split(START, 1)[0]
    after = text.split(END, 1)[1]
    new = before + block + after
    if new == text:
        return False
    readme.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--date", help="YYYY-MM-DD override for testing")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    today = date.fromisoformat(args.date) if args.date else date.today()
    joke = pick(today)
    block = render_block(joke, today)

    if args.dry_run:
        print(block)
        return 0

    changed = update_readme(args.readme, block)
    print(f"{'updated' if changed else 'no-op'}: {joke[:60]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

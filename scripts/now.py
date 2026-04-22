#!/usr/bin/env python3
"""Update the NOW block in README.md with a time-aware "what jason is doing right now" status.

Picks a status from data/statuses.json based on Singapore time + weekday.
Most-specific match wins: day-name > weekday/weekend group > default.
Within a match, picks deterministically from the list using a minute-salted hash so
the status changes across successive cron runs within the same hour.

Testing overrides:
  NOW=2026-04-23T14:30:00+08 python scripts/now.py --readme README.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "statuses.json"
DEFAULT_README = ROOT / "README.md"
SGT = timezone(timedelta(hours=8))

START = "<!-- NOW:START -->"
END = "<!-- NOW:END -->"

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def now_sgt() -> datetime:
    override = os.environ.get("NOW")
    if override:
        return datetime.fromisoformat(override).astimezone(SGT)
    return datetime.now(SGT)


def pick_status(table: dict, dt: datetime) -> str:
    day = WEEKDAYS[dt.weekday()]
    hour = dt.hour
    candidate_groups = [day]
    if dt.weekday() < 5:
        candidate_groups.append("weekday")
    else:
        candidate_groups.append("weekend")
    candidate_groups.append("default")

    for group in candidate_groups:
        bucket = table.get(group)
        if not bucket:
            continue
        for range_key, statuses in bucket.items():
            if range_key.startswith("_"):
                continue
            lo, _, hi = range_key.partition("-")
            try:
                lo_i, hi_i = int(lo), int(hi) if hi else int(lo)
            except ValueError:
                continue
            if lo_i <= hour <= hi_i:
                salt = f"{dt.date().isoformat()}:{hour}:{dt.minute // 30}"
                idx = int(hashlib.sha1(salt.encode()).hexdigest(), 16) % len(statuses)
                return statuses[idx]
    return "👨‍💻 doing something, probably"


def render_block(status: str, dt: datetime) -> str:
    stamp = dt.strftime("%a %H:%M SGT")
    return (
        f"{START}\n"
        f"> **right now** — {status} _(last ping: {stamp})_\n"
        f"{END}"
    )


def update_readme(readme_path: Path, block: str) -> bool:
    text = readme_path.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise RuntimeError(f"NOW markers not found in {readme_path}")
    before = text.split(START, 1)[0]
    after = text.split(END, 1)[1]
    new_text = before + block + after
    if new_text == text:
        return False
    readme_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    table = json.loads(DATA.read_text(encoding="utf-8"))
    dt = now_sgt()
    status = pick_status(table, dt)
    block = render_block(status, dt)

    if args.dry_run:
        print(block)
        return 0

    changed = update_readme(args.readme, block)
    print(f"{'updated' if changed else 'no-op'}: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

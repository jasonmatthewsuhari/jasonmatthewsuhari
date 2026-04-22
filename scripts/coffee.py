#!/usr/bin/env python3
"""Sum total commit contributions via GitHub GraphQL and rewrite the COFFEE block in README.md.

Each commit == one cup of coffee. Because that's approximately correct.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_README = ROOT / "README.md"

START = "<!-- COFFEE:START -->"
END = "<!-- COFFEE:END -->"

# contributionsCollection is year-scoped; we query multiple years to get a lifetime total.
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
    }
  }
}
"""


def gh(token: str, login: str, from_dt: str, to_dt: str) -> int:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login, "from": from_dt, "to": to_dt}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "coffee-counter"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]["user"]["contributionsCollection"]["totalCommitContributions"]


def total_commits(token: str, login: str, start_year: int = 2020) -> int:
    now = datetime.utcnow()
    total = 0
    for y in range(start_year, now.year + 1):
        frm = f"{y}-01-01T00:00:00Z"
        end = f"{y}-12-31T23:59:59Z" if y < now.year else now.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            total += gh(token, login, frm, end)
        except Exception as exc:
            print(f"skip {y}: {exc}", file=sys.stderr)
    return total


def render_block(total: int) -> str:
    return (
        f"{START}\n"
        f"> ☕ **{total:,}** cups of coffee fueled these commits · _(lifetime count, refreshed daily)_\n"
        f"{END}"
    )


def update_readme(readme: Path, block: str) -> bool:
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise RuntimeError("COFFEE markers not found")
    before = text.split(START, 1)[0]
    after = text.split(END, 1)[1]
    new = before + block + after
    if new == text:
        return False
    readme.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default=os.environ.get("GH_USER", "jasonmatthewsuhari"))
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set", file=sys.stderr)
        return 2

    total = total_commits(token, args.user)
    block = render_block(total)

    if args.dry_run:
        print(block)
        return 0

    changed = update_readme(args.readme, block)
    print(f"{'updated' if changed else 'no-op'}: {total} cups")
    return 0


if __name__ == "__main__":
    sys.exit(main())

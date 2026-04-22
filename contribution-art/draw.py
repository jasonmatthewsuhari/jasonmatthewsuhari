#!/usr/bin/env python3
"""
Contribution graph pixel art generator.
Creates backdated git commits to spell out a message on your GitHub profile.

Usage:
    python draw.py              # preview the message in terminal
    python draw.py --execute    # actually create the commits
"""

import argparse
import subprocess
import sys
from datetime import datetime, timedelta

# 3x5 pixel font (each char is 3 cols wide, 5 rows tall)
# Row 0 = top, Row 4 = bottom
FONT = {
    "H": [
        "1.1",
        "1.1",
        "111",
        "1.1",
        "1.1",
    ],
    "I": [
        "111",
        ".1.",
        ".1.",
        ".1.",
        "111",
    ],
    "R": [
        "11.",
        "1.1",
        "11.",
        "1.1",
        "1.1",
    ],
    "E": [
        "111",
        "1..",
        "111",
        "1..",
        "111",
    ],
    "M": [
        "1.1",
        "111",
        "111",
        "1.1",
        "1.1",
    ],
    "P": [
        "11.",
        "1.1",
        "11.",
        "1..",
        "1..",
    ],
    "L": [
        "1..",
        "1..",
        "1..",
        "1..",
        "111",
    ],
    "S": [
        "111",
        "1..",
        "111",
        "..1",
        "111",
    ],
    " ": [
        ".",
        ".",
        ".",
        ".",
        ".",
    ],
}

MESSAGE = "HIRE ME PLS"
COMMITS_PER_PIXEL = 15  # enough to get a solid dark green square


def build_grid(message: str) -> list[list[bool]]:
    """Build a 7-row grid from the message. Text is vertically centered."""
    cols: list[list[bool]] = []

    for i, ch in enumerate(message):
        glyph = FONT.get(ch)
        if glyph is None:
            print(f"Character '{ch}' not in font, skipping")
            continue

        width = len(glyph[0])
        # vertically center the 5-row glyph in 7 rows (1 row padding top & bottom)
        for col_idx in range(width):
            column = [False]  # top padding
            for row in glyph:
                column.append(row[col_idx] == "1")
            column.append(False)  # bottom padding
            cols.append(column)

        # 1-column gap between characters (2 for spaces, but space glyph is already narrow)
        if i < len(message) - 1 and ch != " ":
            cols.append([False] * 7)

    return cols


# 🥚 EGG 4/7: four eggs down, three to go. next clue lives in the Indonesian
# README (alt_readme/README_ID.md) — look for an HTML comment tagged EGG5.
def get_start_sunday(weeks_back: int = 52) -> datetime:
    """Get the Sunday that starts the contribution graph ~1 year ago."""
    today = datetime.now()
    # contribution graph ends on the current Saturday
    # go back to the most recent Sunday
    days_since_sunday = today.weekday()  # Monday=0 ... Sunday=6
    # python weekday: Mon=0, Sun=6. We want days since last Sunday.
    days_since_sunday = (today.weekday() + 1) % 7
    current_sunday = today - timedelta(days=days_since_sunday)
    start_sunday = current_sunday - timedelta(weeks=weeks_back - 1)
    return start_sunday


def preview(grid: list[list[bool]]) -> None:
    """Print a terminal preview of the contribution graph."""
    if not grid:
        print("Empty grid!")
        return

    num_cols = len(grid)
    num_rows = len(grid[0])

    print(f"\nPreview ({num_cols} weeks needed, 52 available):\n")
    if num_cols > 52:
        print("WARNING: message is too wide! It will be clipped.\n")

    for row in range(num_rows):
        line = ""
        for col in range(num_cols):
            line += "##" if grid[col][row] else "  "
        print(line)
    print()


def execute(grid: list[list[bool]], commits_per_pixel: int = COMMITS_PER_PIXEL) -> None:
    """Create backdated commits for each lit pixel."""
    start = get_start_sunday()
    total_pixels = sum(1 for col in grid for val in col if val)
    total_commits = total_pixels * commits_per_pixel
    print(f"Creating {total_commits} commits for {total_pixels} pixels...")

    count = 0
    for col_idx, column in enumerate(grid):
        if col_idx >= 52:
            break
        for row_idx, lit in enumerate(column):
            if not lit:
                continue
            date = start + timedelta(weeks=col_idx, days=row_idx)
            date_str = date.strftime("%Y-%m-%dT12:00:00")

            for n in range(commits_per_pixel):
                count += 1
                msg = f"art: pixel ({col_idx},{row_idx}) commit {n+1}"
                subprocess.run(
                    ["git", "commit", "--allow-empty", "-m", msg],
                    env={
                        **dict(__import__("os").environ),
                        "GIT_AUTHOR_DATE": date_str,
                        "GIT_COMMITTER_DATE": date_str,
                    },
                    capture_output=True,
                    check=True,
                )

                if count % 50 == 0:
                    print(f"  {count}/{total_commits} commits created...")

    print(f"\nDone! {count} commits created.")
    print("Push with: git push")
    print("Note: may take a few minutes to show up on your profile.")


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub contribution pixel art")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create commits (default is preview only)",
    )
    parser.add_argument(
        "--message",
        default=MESSAGE,
        help=f"Message to display (default: {MESSAGE})",
    )
    parser.add_argument(
        "--intensity",
        type=int,
        default=COMMITS_PER_PIXEL,
        help=f"Commits per pixel for darkness (default: {COMMITS_PER_PIXEL})",
    )
    args = parser.parse_args()

    grid = build_grid(args.message)
    preview(grid)

    if args.execute:
        print("This will create backdated commits in the CURRENT repo.")
        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm == "y":
            execute(grid, args.intensity)
        else:
            print("Aborted.")
    else:
        print("Run with --execute to create the commits.")
        print("Recommended: run this in a dedicated empty repo, not your main projects.")


if __name__ == "__main__":
    main()

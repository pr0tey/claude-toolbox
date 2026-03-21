#!/usr/bin/env python3
"""Search/list MDR index entries.

Usage:
    python search.py              # list all entries
    python search.py "<keyword>"  # filter by keyword (case-insensitive)

Output format (one per line):
    id: problem
"""

import json
import sys
from pathlib import Path

INDEX_PATH = Path(".claude/mdr/index.json")


def main():
    if not INDEX_PATH.exists():
        print("No MDR index found.")
        return

    with open(INDEX_PATH) as f:
        entries = json.load(f)

    if not entries:
        print("No decisions recorded yet.")
        return

    keyword = sys.argv[1].lower() if len(sys.argv) > 1 else None

    found = False
    for entry in entries:
        if keyword and keyword not in entry["problem"].lower():
            continue
        print(f'{entry["id"]}: {entry["problem"]}')
        found = True

    if not found and keyword:
        print(f"No decisions matching '{sys.argv[1]}'.")


if __name__ == "__main__":
    main()

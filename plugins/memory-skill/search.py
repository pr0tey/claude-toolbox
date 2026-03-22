# ruff: noqa
# type: ignore
#!/usr/bin/env python3
"""Search/list MDR index entries.

Usage:
    python3 search.py                    # list all entries
    python3 search.py "<keyword>"        # filter by keyword (case-insensitive)
    python3 search.py --full "<keyword>" # also search inside decision files

Output format (one per line):
    id: problem
"""

import json
import sys
from pathlib import Path

INDEX_PATH = Path(".mdr/index.json")
DECISIONS_DIR = Path(".mdr/decisions")


def main():
    if not INDEX_PATH.exists():
        print("No MDR index found.")
        return

    try:
        with open(INDEX_PATH) as f:
            entries = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: index.json is corrupted: {e}", file=sys.stderr)
        print(f"Fix or delete {INDEX_PATH} to recover.", file=sys.stderr)
        sys.exit(1)

    if not entries:
        print("No decisions recorded yet.")
        return

    # Parse arguments
    args = sys.argv[1:]
    full_search = False
    if args and args[0] == "--full":
        full_search = True
        args = args[1:]
    keyword = args[0].lower() if args else None

    found = False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "")
        problem = entry.get("problem", "")

        if keyword:
            match = keyword in problem.lower() or keyword in entry_id.lower()
            if not match and full_search:
                decision_file = DECISIONS_DIR / f"{entry_id}.md"
                if decision_file.exists():
                    match = keyword in decision_file.read_text().lower()
            if not match:
                continue

        print(f"{entry_id}: {problem}")
        found = True

    if not found and keyword:
        print(f"No decisions matching '{args[0]}'.")


if __name__ == "__main__":
    main()

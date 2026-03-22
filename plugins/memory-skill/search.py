# ruff: noqa
# type: ignore
#!/usr/bin/env python3
"""Search/list MDR decisions by scanning .mdr/decisions/ directory.

Usage:
    python3 search.py                    # list all decisions
    python3 search.py "<keyword>"        # filter by keyword in id + title
    python3 search.py --full "<keyword>" # also search inside decision files

Output format (one per line):
    id: problem statement
"""

import sys
from pathlib import Path

DECISIONS_DIR = Path(".mdr/decisions")


def extract_title(filepath):
    """Extract problem statement from first '# ...' line."""
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
        return filepath.stem
    except OSError:
        return filepath.stem


def main():
    if not DECISIONS_DIR.exists():
        print("No MDR decisions directory found.")
        return

    files = sorted(DECISIONS_DIR.glob("*.md"))
    if not files:
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
    for filepath in files:
        entry_id = filepath.stem
        problem = extract_title(filepath)

        if keyword:
            match = keyword in problem.lower() or keyword in entry_id.lower()
            if not match and full_search:
                try:
                    match = keyword in filepath.read_text().lower()
                except OSError:
                    pass
            if not match:
                continue

        print(f"{entry_id}: {problem}")
        found = True

    if not found and keyword:
        print(f"No decisions matching '{args[0]}'.")


if __name__ == "__main__":
    main()

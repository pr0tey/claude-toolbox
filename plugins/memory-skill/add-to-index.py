# ruff: noqa
# type: ignore
#!/usr/bin/env python3
"""Add a new entry to the MDR index.

Usage:
    python3 add-to-index.py "<id>" "<problem statement>"

Creates index.json and directories if they don't exist.
Writes atomically via tmp file + rename.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

INDEX_PATH = Path(".mdr/index.json")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 add-to-index.py <id> <problem>", file=sys.stderr)
        sys.exit(1)

    entry_id = sys.argv[1].strip()
    problem = sys.argv[2].strip()

    if not entry_id or not KEBAB_RE.match(entry_id):
        print(f"Error: id must be kebab-case (a-z, 0-9, hyphens), got '{entry_id}'.", file=sys.stderr)
        sys.exit(1)

    if not problem:
        print("Error: problem statement must not be empty.", file=sys.stderr)
        sys.exit(1)

    # Ensure directories exist
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    Path(".mdr/decisions").mkdir(parents=True, exist_ok=True)

    # Read existing index
    if INDEX_PATH.exists():
        try:
            with open(INDEX_PATH) as f:
                entries = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error: index.json is corrupted: {e}", file=sys.stderr)
            print(f"Fix or delete {INDEX_PATH} to recover.", file=sys.stderr)
            sys.exit(1)
    else:
        entries = []

    # Check for duplicate
    if any(e.get("id") == entry_id for e in entries if isinstance(e, dict)):
        print(f"Entry '{entry_id}' already exists in index.", file=sys.stderr)
        sys.exit(1)

    # Append new entry
    entries.append({"id": entry_id, "problem": problem})

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=INDEX_PATH.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, INDEX_PATH)
    except Exception:
        os.unlink(tmp_path)
        raise

    print(f"Added '{entry_id}' to index.")


if __name__ == "__main__":
    main()

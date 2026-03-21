#!/usr/bin/env python3
"""Add a new entry to the MDR index.

Usage:
    python add-to-index.py "<id>" "<problem statement>"

Creates index.json and directories if they don't exist.
Writes atomically via tmp file + rename.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

INDEX_PATH = Path(".claude/mdr/index.json")


def main():
    if len(sys.argv) != 3:
        print("Usage: python add-to-index.py <id> <problem>", file=sys.stderr)
        sys.exit(1)

    entry_id = sys.argv[1]
    problem = sys.argv[2]

    # Ensure directories exist
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    Path(".claude/mdr/decisions").mkdir(parents=True, exist_ok=True)

    # Read existing index
    if INDEX_PATH.exists():
        with open(INDEX_PATH) as f:
            entries = json.load(f)
    else:
        entries = []

    # Check for duplicate
    if any(e["id"] == entry_id for e in entries):
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

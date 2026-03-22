---
name: mdr-check
description: Search existing Micro-Decision Records before choosing an approach. Use when facing a choice between multiple technical alternatives — architecture, error handling, naming, tooling, API design.
user-invocable: true
allowed-tools: Bash, Read
---

# Check Micro-Decision Records

## Index format

`.mdr/index.json` — JSON array of `{"id": "<kebab-case-id>", "problem": "<problem statement>"}`.
Full decision files are at `.mdr/decisions/<id>.md`.

## Steps

1. If `.mdr/index.json` does not exist, return "No MDR index found. Run /mdr-init to set up." and stop.

2. Run the search script to list existing MDRs:
   ```
   python3 .claude/mdr/search.py
   ```

3. If a keyword is relevant to the current choice, filter:
   ```
   python3 .claude/mdr/search.py "<keyword>"
   ```
   For deeper search inside decision files:
   ```
   python3 .claude/mdr/search.py --full "<keyword>"
   ```

4. **If relevant MDRs exist:**
   - Read the decision files at `.mdr/decisions/<id>.md`
   - **Match by pattern, not context** — if the MDR uses the same tool/library/pattern for a similar category of problem, it applies even if the original context was different (e.g. a retry decision for one service applies to retries everywhere)
   - Return the found decisions to the caller with their full content

5. **If no relevant MDR exists:**
   - Return "No relevant past decisions found"

---
name: mdr-save
description: Save a new Micro-Decision Record after a choice is made. Use when the user confirms or agrees on an approach between alternatives.
user-invocable: true
allowed-tools: Read, Write, Bash
---

# Save Micro-Decision Record

## Step 0 — Reusability check

Save by default. Skip ONLY if the decision cannot apply to any other part of the project or any future task. When in doubt — save.

If skipped — inform the caller: "This decision is too specific to record." Then stop.

## Step 1 — Check for existing related decision

Search for an existing MDR that covers the same topic:
```
python .claude/mdr/search.py "<keyword>"
```

- **If a closely related MDR exists** — read `.mdr/decisions/<id>.md` and decide:
  - If the new decision **supersedes** the old one (same topic, different choice) → **update** the existing file in place. Add the old decision to "Rejected alternatives" with a note that it was the previous decision.
  - If the new decision **refines** the old one (adds specifics to the same choice) → **update** the existing file, expanding the "Decision" or "Why" sections.
  - If it's a **genuinely different topic** → proceed to create a new MDR (Step 2).
- **If no related MDR exists** → proceed to Step 2.

## Step 2 — Create or update the decision file

### New MDR

1. Generate a short **kebab-case** id from the problem (e.g. `error-response-format`)
   - Use only lowercase letters, digits, and hyphens
   - Keep it concise but descriptive (2-4 words)

2. Create the decision file at `.mdr/decisions/<id>.md` using this template:

   ```markdown
   # <Problem statement>

   ## Decision
   <What was decided>

   ## Why
   <Reasoning>

   ## Rejected alternatives

   ### <Alternative 1>
   <Why rejected>

   ### <Alternative 2>
   <Why rejected>
   ```

3. Add the entry to the index:
   ```
   python .claude/mdr/add-to-index.py "<id>" "<problem statement>"
   ```

4. **If add-to-index.py reports the ID already exists:**
   - Read the existing `.mdr/decisions/<id>.md` to check if it's the same decision
   - If same decision — skip, inform caller it's already recorded
   - If different decision — append a numeric suffix (`-v2`, `-v3`, etc.) and retry

### Updating an existing MDR

1. Edit the existing `.mdr/decisions/<id>.md` file directly.
2. Do NOT create a new index entry — the existing one is sufficient.

## Step 3 — Report

For new MDR:
> Saved decision: **<problem statement>** → `.mdr/decisions/<id>.md`

For updated MDR:
> Updated decision: **<problem statement>** → `.mdr/decisions/<id>.md`

## Notes

- The problem statement MUST be **generalized** — describe the category, not the instance. Bad: "retries for service X". Good: "Retry strategy for external API calls". The MDR must be discoverable in any future context where the same pattern applies.
- Keep problem statements under 200 characters.

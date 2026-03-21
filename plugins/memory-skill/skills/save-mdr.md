---
name: save-mdr
description: Save a new Micro-Decision Record when a choice between alternatives has been made
user-invocable: false
allowed-tools: Read, Write, Bash
---

# Save Micro-Decision Record

After a decision between alternatives has been made, save it as an MDR.

## Steps

1. Generate a short **kebab-case** id from the problem (e.g. `error-response-format`)

2. Create the decision file at `.claude/mdr/decisions/<id>.md` using this template:

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
   python $PLUGIN_DIR/add-to-index.py "<id>" "<problem statement>"
   ```

4. Inform the user what was saved:
   > Saved decision: **<problem statement>** → `.claude/mdr/decisions/<id>.md`

## Notes

- The problem statement should describe the **essence** of the decision, not the context where it was first made. This ensures the MDR is discoverable in any future context.
- Create the `.claude/mdr/decisions/` directory if it does not exist.
- Do not wait for user confirmation before saving.

---
name: check-mdr
description: Check existing Micro-Decision Records when facing a choice between multiple approaches to any task — code, architecture, tooling, naming, processes
user-invocable: false
allowed-tools: Bash, Read
---

# Check Micro-Decision Records

When you identify multiple possible approaches to a task, check existing MDRs before proceeding.

## Steps

1. Run the search script to list existing MDRs:
   ```
   python $PLUGIN_DIR/search.py
   ```

2. If a keyword is relevant to the current choice, filter:
   ```
   python $PLUGIN_DIR/search.py "<keyword>"
   ```

3. **If a relevant MDR exists:**
   - Read the decision file at `.claude/mdr/decisions/<id>.md`
   - Inform the user: "Applying existing decision: **<problem statement>**"
   - Follow the decision. Do not wait for user confirmation.

4. **If no relevant MDR exists:**
   - Search the existing codebase for similar patterns or approaches
   - If found, include them as one of the options marked *"(already used in codebase)"*
   - Present options to the user via AskUserQuestion
   - Discuss until a decision is made
   - Once decided — the save-mdr skill will be auto-invoked to record the decision

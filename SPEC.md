# Micro-Decision Records (MDR) for Claude Code

## Overview

A skill + rule system for Claude Code that builds a project-level knowledge base of decisions. When the agent faces a choice between multiple approaches, it checks existing decisions first, and if none exist — discusses with the user and saves the outcome.

## Problem

When working on a project, the same types of decisions come up repeatedly — error handling, naming, architecture patterns, tooling choices, etc. Without a memory of past decisions, the agent either asks the user again or makes inconsistent choices.

## Solution

Two mechanisms working together:

- **Rule** (always loaded): instructs Claude to check the MDR index whenever it sees multiple possible approaches
- **Skill** (auto-invoked): handles saving new decisions to the knowledge base

## File Structure

```
.claude/
├── rules/
│   └── micro-decision-records.md      # Rule: check MDRs when facing choices
├── skills/
│   └── save-mdr/
│       └── SKILL.md                   # Skill: save a new MDR
└── mdr/
    ├── index.json                     # Compact index for search
    ├── add-to-index.py                # Script: add entry to index
    ├── search.py                      # Script: search/list index
    └── decisions/                     # MDR files
```

## Components

### 1. Rule: `.claude/rules/micro-decision-records.md`

Loaded at every session. Instructs Claude:

1. When you see multiple possible approaches to any task (code, architecture, tooling, naming, processes — anything):
2. Run `python .claude/mdr/search.py` to list existing MDRs
3. If a keyword is relevant, run `python .claude/mdr/search.py "<keyword>"` to filter
4. If a relevant MDR exists — open the decision file at `.claude/mdr/decisions/<id>.md`, inform the user "Applying existing decision: <name>", and follow it. Do not wait for user confirmation.
5. If no relevant MDR exists — search the existing codebase for similar patterns/approaches. If found, include them as one of the options marked "(already used in codebase)".
6. Present options to the user via AskUserQuestion, discuss until a decision is made.
7. Once decided — save the MDR (Claude auto-invokes the save-mdr skill).

### 2. Skill: `.claude/skills/save-mdr/SKILL.md`

Frontmatter:
- name: save-mdr
- description: Saves a new Micro-Decision Record when a choice between alternatives has been made
- user-invocable: false
- allowed-tools: Read, Write, Bash

Behavior:

1. Generate a short kebab-case id from the problem (e.g. `error-response-format`)
2. Create `.claude/mdr/decisions/<id>.md` using the template (see below)
3. Run `python .claude/mdr/add-to-index.py "<id>" "<problem statement>"` to add to index
4. Inform the user what was saved

### 3. Decision File Template

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

### 4. Index Format: `index.json`

```json
[]
```

Each entry:
```json
{"id": "<kebab-case-id>", "problem": "<problem statement>"}
```

The problem statement should describe the essence of the decision, not the context where it was first made. This ensures the MDR is discoverable in any future context.

### 5. Script: `add-to-index.py`

- Pure Python, standard library only (json module), no dependencies
- Arguments: `<id>` `<problem>`
- Reads index.json, appends new entry, writes back
- Atomic: write to tmp file, then rename

### 6. Script: `search.py`

- Pure Python, standard library only, no dependencies
- No arguments: lists all entries, one per line, format `id: problem`
- Optional argument: keyword — filters entries by case-insensitive substring match in problem field
- Compact output, no JSON syntax — saves context tokens

## Behavior Flow

```
Claude faces a choice
       │
       ▼
  Run search.py
       │
       ▼
  Relevant MDR found? ──yes──▶ Open decisions/<id>.md
       │                        Inform user: "Applying decision: <name>"
       no                       Follow the decision
       │
       ▼
  Search codebase for
  existing patterns
       │
       ▼
  Present options to user
  (including codebase patterns
   marked "already used in codebase")
       │
       ▼
  User chooses / discusses
       │
       ▼
  Decision made
       │
       ▼
  Save MDR:
  - Write decisions/<id>.md
  - Run add-to-index.py
  - Inform user what was saved
```

## Design Decisions

- **No categories or tags**: Claude matches by problem description. Keeps index minimal and avoids the problem of decisions being relevant outside their original category.
- **No deprecation mechanism**: Delete or update MDR files manually when they become outdated.
- **No user confirmation on save**: Claude saves immediately, shows what was saved. User can edit later if needed.
- **No user confirmation on apply**: Claude informs but does not block waiting for approval.
- **Edit-safe index updates**: A Python script handles index.json writes to avoid Claude accidentally losing entries when rewriting the file.
- **Compact search output**: search.py outputs `id: problem` lines instead of JSON to save context tokens.
- **Language**: All system files (rules, skills, scripts) in English. Decision content in whatever language the team uses.

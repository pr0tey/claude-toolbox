# Micro-Decision Records (MDR) — Claude Code Plugin

## Overview

A plugin for Claude Code that builds a project-level knowledge base of decisions. When the agent faces a choice between multiple approaches, it checks existing decisions first, and if none exist — discusses with the user and saves the outcome.

Part of the **claude-toolbox** marketplace.

## Problem

When working on a project, the same types of decisions come up repeatedly — error handling, naming, architecture patterns, tooling choices, etc. Without a memory of past decisions, the agent either asks the user again or makes inconsistent choices.

## Solution

Two auto-invoked skills working together:

- **check-mdr** (auto-invoked): checks the MDR index whenever Claude sees multiple possible approaches
- **save-mdr** (auto-invoked): saves new decisions to the knowledge base

Additionally, the plugin recommends adding a line to the project's `CLAUDE.md` to reinforce the behavior:

```markdown
## Decision Records
This project uses memory-skill plugin for tracking architectural decisions.
When facing a choice between approaches, always check existing MDRs first.
```

This gives two levels of reliability:
1. Skills with good descriptions — Claude invokes them when it sees a decision point
2. CLAUDE.md — hard rule in project context, Claude cannot "forget"

## Repository Structure

This repository is a **Claude Code plugin marketplace** (`claude-toolbox`). Each plugin lives in its own directory under `plugins/`.

```
claude-toolbox/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace descriptor
├── plugins/
│   └── memory-skill/
│       ├── plugin.json           # Plugin descriptor
│       ├── skills/
│       │   ├── check-mdr.md      # Skill: check existing MDRs
│       │   └── save-mdr.md       # Skill: save a new MDR
│       ├── search.py             # Script: search/list index
│       └── add-to-index.py       # Script: add entry to index
├── SPEC.md
└── README.md
```

## Plugin Installation

User adds the marketplace to their settings:

```json
{
  "extraKnownMarketplaces": {
    "claude-toolbox": {
      "source": {
        "source": "github",
        "repo": "pr0tey/claude-toolbox"
      }
    }
  }
}
```

Then enables the plugin:

```json
{
  "enabledPlugins": {
    "memory-skill@claude-toolbox": true
  }
}
```

## Components

### 1. Marketplace: `.claude-plugin/marketplace.json`

```json
{
  "name": "claude-toolbox",
  "owner": {
    "name": "pr0tey"
  },
  "plugins": [
    {
      "name": "memory-skill",
      "source": "./plugins/memory-skill",
      "description": "Track architectural decisions as Micro-Decision Records"
    }
  ]
}
```

### 2. Plugin: `plugins/memory-skill/plugin.json`

Standard Claude Code plugin descriptor pointing to the two skills.

### 3. Skill: `check-mdr`

Frontmatter:
- name: check-mdr
- description: Check existing Micro-Decision Records when facing a choice between multiple approaches to any task — code, architecture, tooling, naming, processes
- user-invocable: false
- allowed-tools: Bash, Read

Behavior:

1. Run `search.py` to list existing MDRs
2. If a keyword is relevant, run `search.py "<keyword>"` to filter
3. If a relevant MDR exists — open the decision file at `.claude/mdr/decisions/<id>.md`, inform the user "Applying existing decision: <name>", and follow it
4. If no relevant MDR exists — search the codebase for similar patterns/approaches. If found, include them as one of the options marked "(already used in codebase)"
5. Present options to the user, discuss until a decision is made
6. Once decided — save the MDR (Claude auto-invokes save-mdr)

### 4. Skill: `save-mdr`

Frontmatter:
- name: save-mdr
- description: Save a new Micro-Decision Record when a choice between alternatives has been made
- user-invocable: false
- allowed-tools: Read, Write, Bash

Behavior:

1. Generate a short kebab-case id from the problem (e.g. `error-response-format`)
2. Create `.claude/mdr/decisions/<id>.md` using the template (see below)
3. Run `add-to-index.py "<id>" "<problem statement>"` to add to index
4. Inform the user what was saved

### 5. Decision File Template

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

### 6. Index Format: `index.json`

```json
[]
```

Each entry:
```json
{"id": "<kebab-case-id>", "problem": "<problem statement>"}
```

The problem statement should describe the essence of the decision, not the context where it was first made. This ensures the MDR is discoverable in any future context.

### 7. Script: `add-to-index.py`

- Pure Python, standard library only (json module), no dependencies
- Arguments: `<id>` `<problem>`
- Reads index.json, appends new entry, writes back
- Atomic: write to tmp file, then rename

### 8. Script: `search.py`

- Pure Python, standard library only, no dependencies
- No arguments: lists all entries, one per line, format `id: problem`
- Optional argument: keyword — filters entries by case-insensitive substring match in problem field
- Compact output, no JSON syntax — saves context tokens

## MDR Storage Location

MDR files are stored in the **user's project**, not in the plugin:

```
<user-project>/
└── .claude/
    └── mdr/
        ├── index.json
        └── decisions/
            ├── error-response-format.md
            └── ...
```

The scripts in the plugin operate on `.claude/mdr/` relative to the current working directory.

## Behavior Flow

```
Claude faces a choice
       │
       ▼
  check-mdr skill auto-invoked
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
  save-mdr skill auto-invoked:
  - Write decisions/<id>.md
  - Run add-to-index.py
  - Inform user what was saved
```

## Design Decisions

- **Plugin, not rule**: Distributed as a Claude Code plugin via marketplace. The rule behavior is replaced by a skill with a precise description that triggers auto-invocation.
- **CLAUDE.md recommendation**: The plugin README recommends adding a line to the project's CLAUDE.md as a second reliability layer.
- **No categories or tags**: Claude matches by problem description. Keeps index minimal and avoids the problem of decisions being relevant outside their original category.
- **No deprecation mechanism**: Delete or update MDR files manually when they become outdated.
- **No user confirmation on save**: Claude saves immediately, shows what was saved. User can edit later if needed.
- **No user confirmation on apply**: Claude informs but does not block waiting for approval.
- **Edit-safe index updates**: A Python script handles index.json writes to avoid Claude accidentally losing entries when rewriting the file.
- **Compact search output**: search.py outputs `id: problem` lines instead of JSON to save context tokens.
- **Language**: All system files (skills, scripts) in English. Decision content in whatever language the team uses.

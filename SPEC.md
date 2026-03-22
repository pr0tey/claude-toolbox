# Micro-Decision Records (MDR) — Claude Code Plugin

## Overview

A plugin for Claude Code that builds a **persistent knowledge base of project decisions**. When the same type of choice comes up again — error handling, naming, architecture, tooling — the agent finds and applies the past decision instead of making an inconsistent one or asking the user to repeat themselves.

Discussions with the user are the mechanism for populating the knowledge base: when no prior decision exists, the agent presents options and waits for the user's choice before acting.

Part of the **claude-toolbox** marketplace.

## Problem

The same types of decisions come up repeatedly across sessions — error handling strategy, naming conventions, library choices, architecture patterns. Without persistent memory, the agent either silently picks an approach (risking unwanted implementations and reverts) or asks the user to re-decide something they already settled last week.

## Solution

A knowledge base of decisions (`.mdr/decisions/`) with a multi-layered enforcement system that ensures the agent always checks it and populates it through user discussions:

1. **Rules** (`.claude/rules/mdr-protocol.md`) — detailed protocol loaded at session start, survives compaction. Defines the full decision-making flow.
2. **Hooks** (`UserPromptSubmit`, `SubagentStart`) — short `<system-reminder>` injected on every message as reinforcement.
3. **MDR Agent** — dedicated sub-agent (haiku) that handles CHECK and SAVE operations in its own context, keeping the main conversation clean.
4. **Skills** (`mdr-check`, `mdr-save`) — preloaded into the MDR agent, define search and save logic.

## Repository Structure

```
claude-toolbox/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── memory-skill/
│       ├── plugin.json
│       ├── agents/
│       │   └── mdr.md              # MDR sub-agent definition
│       ├── skills/
│       │   ├── mdr-check/SKILL.md  # Search past decisions
│       │   ├── mdr-save/SKILL.md   # Save new decisions
│       │   └── mdr-init/SKILL.md   # Initialize MDR in a project
│       ├── hooks/
│       │   └── mdr-remind.sh       # Short reminder hook
│       ├── rules/
│       │   └── mdr-protocol.md     # Full decision protocol
│       ├── examples/
│       │   └── error-response-format.md
│       ├── search.py               # Search/list index entries
│       └── add-to-index.py         # Add entry to index
├── SPEC.md
└── README.md
```

## Plugin Installation

Add the marketplace to settings:

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

Enable the plugin:

```json
{
  "enabledPlugins": {
    "memory-skill@claude-toolbox": true
  }
}
```

Then run `/mdr-init` in the target project to set up local files and hooks.

## Decision Protocol

The core behavioral contract, enforced via rules + hooks:

```
User gives a task
       │
       ▼
  Agent analyzes the problem
       │
       ▼
  Delegate to mdr agent: CHECK
       │
       ▼
  Relevant MDR found? ──yes──▶ Apply existing decision
       │                        (already approved, no re-asking)
       no
       │
       ▼
  Present ≥2 approaches
  with trade-offs
       │
       ▼
  WAIT for user choice
       │
       ▼
  Discuss implementation
  details with user
       │
       ▼
  Delegate to mdr agent: SAVE
  (agent decides whether to record)
       │
       ▼
  Proceed with the task
```

Key rules:
- Every confirmed choice between alternatives = separate decision
- User rejection or correction = new decision → SAVE before fixing
- Existing MDR = already approved → apply without re-asking
- Agent MUST delegate to mdr agent, MUST NOT judge "worthiness" itself
- Agent MAY use other persistence tools (memory, feedback) for other purposes

## Components

### 1. Rules: `mdr-protocol.md`

Loaded at session start, survives compaction. Contains:
- Core rule (always check existing decisions before acting)
- Step-by-step protocol
- When to delegate SAVE (includes rejections/corrections)
- When NOT to start the protocol (questions, no-choice steps)

### 2. Hook: `mdr-remind.sh`

Fires on `UserPromptSubmit` and `SubagentStart`. Two-line `<system-reminder>` reinforcement. Filters out the mdr agent itself to avoid circular instructions.

### 3. MDR Agent: `mdr.md`

- Model: haiku (fast, cheap)
- Skills preloaded: mdr-check, mdr-save
- Tools: Read, Write, Bash, Grep, Glob
- Two tasks: CHECK (search) and SAVE (record)
- Runs in its own context — does not pollute main conversation

### 4. Skill: `mdr-check`

Purely search-focused. Steps:
1. Check if `.mdr/index.json` exists
2. Search with `search.py` (all or by keyword)
3. If found — return decisions with full content
4. If not found — return "No relevant past decisions found"

Does NOT make decisions about what to do with results. That logic lives in the protocol (rules).

### 5. Skill: `mdr-save`

Records confirmed decisions. Steps:
0. Reusability check — save by default, skip ONLY if decision cannot apply to any other part of the project or future task. When in doubt — save.
1. Search for existing related MDR — update (supersede/refine) if found
2. Create new MDR file + index entry if no related MDR exists
3. Report what was saved/updated

Problem statements must be generalized (category, not instance).

### 6. Skill: `mdr-init`

One-time setup for a project. Copies from plugin to project:
- Scripts → `.claude/mdr/`
- Agent → `.claude/agents/mdr.md`
- Skills → `.claude/skills/`
- Rules → `.claude/rules/`
- Hooks → `.claude/settings.json`
- Creates `.mdr/decisions/` and `index.json`

Re-running is safe: updates files, preserves data.

### 7. Decision File Template

```markdown
# <Problem statement>

## Decision
<What was decided>

## Why
<Reasoning>

## Rejected alternatives

### <Alternative 1>
<Why rejected>
```

### 8. Index Format: `index.json`

```json
[{"id": "<kebab-case-id>", "problem": "<problem statement>"}]
```

### 9. Scripts

**`search.py`** — Pure Python 3, no dependencies. Lists/filters index entries. Output: `id: problem` (one per line). Supports `--full` for content search.

**`add-to-index.py`** — Pure Python 3, no dependencies. Validates kebab-case id, appends to index. Atomic writes (tmp + rename).

## MDR Storage

Scripts in `.claude/mdr/`, decisions in `.mdr/`:

```
<user-project>/
├── .claude/
│   ├── mdr/
│   │   ├── search.py
│   │   ├── add-to-index.py
│   │   └── mdr-remind.sh
│   ├── agents/
│   │   └── mdr.md
│   ├── skills/
│   │   ├── mdr-check/SKILL.md
│   │   └── mdr-save/SKILL.md
│   ├── rules/
│   │   └── mdr-protocol.md
│   └── settings.json (hooks)
└── .mdr/
    ├── index.json
    └── decisions/
        ├── error-response-format.md
        └── ...
```

## Design Decisions

- **Knowledge base first, discussion as mechanism**: The primary goal is a persistent, reusable decision base. Discussions with the user are how it gets populated — not the end goal themselves.
- **Multi-layer enforcement**: Rules (detailed, persistent) + hooks (short, per-message) — neither alone is sufficient.
- **Aggressive tone in rules is intentional**: Rules and hooks use strong language ("FORBIDDEN", "MUST") because softer phrasing degrades LLM compliance. The tone in machine-facing files (rules, hooks) serves a different purpose than human-facing docs (README, SPEC).
- **`<system-reminder>` tags**: Hooks use XML tags that the agent treats as system-level instructions — the strongest influence short of actual system prompt.
- **Dedicated sub-agent**: MDR operations run in a separate context (haiku) to avoid polluting the main conversation with search/save noise.
- **Plugin hooks unreliable**: Plugin-level hooks from `plugin.json` may not load. `mdr-init` copies hooks to local `.claude/settings.json` as a reliable fallback.
- **Reusability filter in sub-agent**: The main agent always delegates SAVE. The mdr agent (not the main agent) decides whether a decision is worth recording. This prevents the main agent from self-filtering.
- **Existing MDR = no re-asking**: Past decisions are already approved. Applying them without confirmation is a feature, not a bug.
- **No categories or tags**: Search by problem description. Keeps index minimal.
- **Generalized problem statements**: "Retry strategy for external API calls" not "retries for service X". Ensures discoverability across contexts.

## Future Ideas

- **`/mdr-import` from GitLab MR comments**: Parse merge request discussions to extract decisions. Use LLM to identify choice-between-alternatives patterns in comment threads, present to user for confirmation, save confirmed ones as MDR.

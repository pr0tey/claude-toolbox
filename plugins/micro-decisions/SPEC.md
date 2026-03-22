# Micro-Decision Records (MDR) — Claude Code Plugin

## Overview

A plugin for Claude Code that builds a **persistent knowledge base of project decisions**. When the same type of choice comes up again — error handling, naming, architecture, tooling — the agent finds and applies the past decision instead of making an inconsistent one or asking the user to repeat themselves.

Discussions with the user are the mechanism for populating the knowledge base: when no prior decision exists, the agent presents options and waits for the user's choice before acting.

Part of the [claude-toolbox](../../README.md) marketplace.

## Problem

The same types of decisions come up repeatedly across sessions — error handling strategy, naming conventions, library choices, architecture patterns. Without persistent memory, the agent either silently picks an approach (risking unwanted implementations and reverts) or asks the user to re-decide something they already settled last week.

## Solution

A knowledge base of decisions (`.mdr/decisions/`) with a multi-layered enforcement system that ensures the agent always checks it and populates it through user discussions:

1. **Rules** (`.claude/rules/mdr-protocol.md`) — detailed protocol loaded at session start, survives compaction. Defines the full decision-making flow.
2. **Hooks** (`UserPromptSubmit`, `SubagentStart`) — short `<system-reminder>` injected on every message as reinforcement.
3. **MDR Agents** — two dedicated sub-agents (haiku), each in its own context to keep the main conversation clean:
   - `mdr-check` — synchronous, searches past decisions before any choice
   - `mdr-save` — `background: true`, records decisions without blocking the main workflow

## Repository Structure

```
plugins/micro-decisions/
├── plugin.json
├── SPEC.md                 # This file
├── README.md               # User-facing docs
├── agents/
│   ├── mdr-check.md        # Search agent (synchronous)
│   └── mdr-save.md         # Save agent (background: true)
├── skills/
│   └── mdr-init/SKILL.md   # Initialize MDR in a project
├── hooks/
│   └── mdr-remind.sh       # Short reminder hook
├── rules/
│   └── mdr-protocol.md     # Full decision protocol
└── examples/
    └── error-response-format.md

tests/micro-decisions/
└── e2e/
    └── test_mdr_protocol.py   # E2E test suite (13 scenarios)
```

## Plugin Installation

```shell
/plugin marketplace add pr0tey/claude-toolbox
/plugin install micro-decisions@claude-toolbox
/reload-plugins
```

Then run `/micro-decisions:mdr-init` in the target project to set up local files and hooks.

For team-wide setup via `settings.json`, see the [Claude Code docs](https://code.claude.com/docs/en/discover-plugins#configure-team-marketplaces).

## Decision Protocol

The core behavioral contract, enforced via rules + hooks:

```
User gives a task
       │
       ▼
  Agent analyzes the problem
       │
       ▼
  Delegate to mdr-check agent
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
  Proceed with the task immediately
       │
       ▼
  Delegate to mdr-save agent
  (background: true, non-blocking)
```

Key rules:
- Every confirmed choice between alternatives = separate decision
- User rejection or correction = new decision → delegate to mdr-save agent (background), then fix
- Existing MDR = already approved → apply without re-asking
- Agent MUST delegate to mdr-save agent, MUST NOT judge "worthiness" itself
- Agent MAY use other persistence tools (memory, feedback) for other purposes

## Components

### 1. Rules: `mdr-protocol.md`

Loaded at session start, survives compaction. Contains:
- Core rule (always check existing decisions before acting)
- Step-by-step protocol
- When to delegate SAVE (includes rejections/corrections)
- When NOT to start the protocol (questions, no-choice steps)

### 2. Hook: `mdr-remind.sh`

Fires on `UserPromptSubmit` and `SubagentStart`. Two-line `<system-reminder>` reinforcement. Filters out mdr-check and mdr-save agents to avoid circular instructions. Uses a grep fallback when `agent_type` field is missing or empty from the JSON input.

### 3. MDR Agents

**`mdr-check.md`** — search agent (synchronous)
- Model: haiku (fast, cheap)
- Tools: Read, Grep, Glob
- Runs in foreground — caller waits for search results
- Extracts 2-3 technical keywords from the caller's problem description
- Matches by category of decision, not surface context

**`mdr-save.md`** — save agent (`background: true`)
- Model: haiku (fast, cheap)
- Tools: Read, Write, Edit, Grep, Glob
- Runs in background automatically — caller proceeds immediately
- Step 1 (check for existing related MDR) is mandatory — must read every matched file before creating a new one
- Prefers Edit over Write when updating existing MDRs to avoid content loss

### 4. Skill: `mdr-init` (user-invocable)

One-time setup for a project. Copies from plugin to project:
- Scripts → `.claude/mdr/`
- Agents → `.claude/agents/mdr-check.md`, `.claude/agents/mdr-save.md`
- Rules → `.claude/rules/`
- Hooks → `.claude/settings.json`
- Creates `.mdr/decisions/`

Re-running is safe: updates files, preserves data.

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
```

## MDR Storage

Hooks in `.claude/mdr/`, decisions in `.mdr/`:

```
<user-project>/
├── .claude/
│   ├── mdr/
│   │   └── mdr-remind.sh
│   ├── agents/
│   │   ├── mdr-check.md
│   │   └── mdr-save.md
│   ├── rules/
│   │   └── mdr-protocol.md
│   └── settings.json (hooks)
└── .mdr/
    └── decisions/
        ├── error-response-format.md
        └── ...
```

## Design Decisions

- **Knowledge base first, discussion as mechanism**: The primary goal is a persistent, reusable decision base. Discussions with the user are how it gets populated — not the end goal themselves.
- **Multi-layer enforcement**: Rules (detailed, persistent) + hooks (short, per-message) — neither alone is sufficient.
- **Aggressive tone in rules is intentional**: Rules and hooks use strong language ("FORBIDDEN", "MUST") because softer phrasing degrades LLM compliance. The tone in machine-facing files (rules, hooks) serves a different purpose than human-facing docs (README, SPEC).
- **`<system-reminder>` tags**: Hooks use XML tags that the agent treats as system-level instructions — the strongest influence short of actual system prompt.
- **Two dedicated sub-agents**: CHECK (synchronous) and SAVE (`background: true`) run in separate contexts (haiku). CHECK blocks because the caller needs the result before deciding. SAVE runs in background to avoid blocking the main workflow.
- **Plugin hooks unreliable**: Plugin-level hooks from `plugin.json` may not load. `mdr-init` copies hooks to local `.claude/settings.json` as a reliable fallback.
- **Reusability filter in sub-agent**: The main agent always delegates SAVE. The mdr-save agent (not the main agent) decides whether a decision is worth recording. This prevents the main agent from self-filtering.
- **Existing MDR = no re-asking**: Past decisions are already approved. Applying them without confirmation is a feature, not a bug.
- **No index file**: Decisions are discovered by agents using Glob/Grep on `.mdr/decisions/*.md`. Each file = one decision, title = problem statement. No shared JSON index means no git merge conflicts when multiple branches add decisions.
- **No search script**: Agents use built-in tools (Glob, Grep, Read) to find and read decisions. This eliminates a Python dependency and simplifies the plugin — agents already have the tools they need.
- **Generalized problem statements**: "Retry strategy for external API calls" not "retries for service X". Ensures discoverability across contexts.

## Testing

E2E tests in `tests/micro-decisions/e2e/test_mdr_protocol.py` run Claude Code headlessly against a synthetic project with the MDR plugin installed. Each test creates a temporary project, runs one or more Claude turns, and verifies protocol behavior.

**Test suites:**

| Suite | Tests | What it covers |
|-------|-------|----------------|
| `smoke` | 4 | Core flows: check existing, save new, update, user rejection |
| `corner` | 7 | Edge cases: questions, two decisions per session, partial match, missing directory, refinement updates, duplicate skip, reusability skip |
| `realistic` | 2 | Coding tasks with no MDR hints in the prompt |

**Run:**
```bash
make test              # all 13 tests
make test-mdr-smoke    # smoke only
make test-mdr-corner   # corner cases only
make test-mdr-realistic # realistic scenarios only
```

Single test: `python3 tests/micro-decisions/e2e/test_mdr_protocol.py <test_name>`

**Requirements:** Claude Code CLI installed and authenticated, ~$1-2 per full run (sub-agents use haiku).

**Artifacts:** Failed tests dump traces to `tests/micro-decisions/e2e/test-artifacts/` for debugging.

## Future Ideas

- **`/mdr-import` from GitLab MR comments**: Parse merge request discussions to extract decisions. Use LLM to identify choice-between-alternatives patterns in comment threads, present to user for confirmation, save confirmed ones as MDR.

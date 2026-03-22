# micro-decisions

A persistent knowledge base of project decisions. The same choice never needs to be made twice — Claude remembers what was decided and applies it consistently across sessions.

1. **Checks** existing decisions before acting
2. **Applies** a past decision if one exists — no need to re-discuss
3. **Discusses** options with the user when no prior decision exists
4. **Saves** the outcome for future reference

Decisions are stored in your project at `.mdr/decisions/`.

## Setup

### 1. Install

```shell
/plugin marketplace add pr0tey/claude-toolbox
/plugin install micro-decisions@claude-toolbox
/reload-plugins
```

### 2. Initialize in your project

```shell
/micro-decisions:mdr-init
```

This copies agents, rules, and hooks into your project and creates `.mdr/decisions/`.

### 3. Restart Claude Code

Hooks and rules only load at session start.

## Verify it works

After restarting, ask Claude:

> What MDR rules are active?

Claude should mention the MDR protocol and decision-checking behavior. If it does not, check that `/mdr-init` completed successfully and that you restarted the session.

## How it works in practice

**Before** (without the plugin) — Claude silently picks an approach:

```
You:    Add error handling to the API
Claude: I've added error handling. Errors return {"message": "..."} with a 500 status.
        [already committed the code]
```

**After** (with the plugin) — Claude checks past decisions and discusses new ones:

```
You:    Add error handling to the API
Claude: I checked existing decisions — found one:
        "How to structure error responses in the API"
        → Use RFC 7807 Problem Details with envelope wrapper.
        Applying this decision.

        [writes code using the agreed format]
```

When no prior decision exists:

```
You:    Add retry logic for external API calls
Claude: No existing decision found for retry strategies.
        Here are the options:

        1. Exponential backoff with jitter (resilient, standard)
        2. Fixed interval retry (simple, predictable)
        3. Circuit breaker pattern (complex, best for high-traffic)

        Which approach do you prefer?
You:    Option 1
Claude: [saves the decision, then implements it]
```

## Git integration

Commit `.mdr/` to your repository. This way, decisions are shared across team members and Claude sessions:

```bash
git add .mdr/
git commit -m "Add decision records"
```

The `.claude/` directory (scripts, rules, hooks) should also be committed so teammates get the same behavior without running `/mdr-init` themselves.

## Recommended: add to CLAUDE.md

For maximum reliability, add this to your project's `CLAUDE.md`:

```markdown
## Decision Records
This project uses micro-decisions plugin for tracking architectural decisions.
When facing a choice between approaches, always check existing MDRs first.
```

This ensures Claude always checks MDRs, even without relying on skill auto-invocation.

## Example MDR

See [examples/error-response-format.md](examples/error-response-format.md) for a sample decision record.

## Troubleshooting

### Manually editing or deleting an MDR

- **Edit:** Open `.mdr/decisions/<id>.md` directly and modify the content.
- **Delete:** Remove the file from `.mdr/decisions/`.

### Two decisions conflict

If two MDRs contradict each other, the newer one should take precedence. Update or remove the outdated MDR.

### Scripts fail with "No MDR decisions directory found"

This is normal on first use — run `/mdr-init` to set up the directory structure.

### Plugin seems inactive after install

Hooks and rules load only at session start. Make sure you:
1. Ran `/mdr-init` in the project
2. Restarted Claude Code after init

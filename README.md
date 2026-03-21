# claude-toolbox

A marketplace of plugins for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Plugins

| Plugin | Description |
|--------|-------------|
| [memory-skill](plugins/memory-skill/) | Track architectural decisions as Micro-Decision Records (MDR) |

## Installation

### 1. Add the marketplace

In your Claude Code settings (`~/.claude/settings.json` or project `.claude/settings.json`):

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

### 2. Enable a plugin

```json
{
  "enabledPlugins": {
    "memory-skill@claude-toolbox": true
  }
}
```

## memory-skill

Builds a project-level knowledge base of decisions. When Claude faces a choice between multiple approaches, it:

1. **Checks** existing decisions via `check-mdr` skill
2. **Applies** a past decision if one exists — or discusses options with the user
3. **Saves** the outcome via `save-mdr` skill for future reference

Decisions are stored in your project at `.claude/mdr/decisions/`.

### Recommended: add to CLAUDE.md

For maximum reliability, add this to your project's `CLAUDE.md`:

```markdown
## Decision Records
This project uses memory-skill plugin for tracking architectural decisions.
When facing a choice between approaches, always check existing MDRs first.
```

This ensures Claude always checks MDRs, even without relying on skill auto-invocation.

## Contributing

To add a new plugin, create a directory under `plugins/` with a `plugin.json` and register it in `.claude-plugin/marketplace.json`.

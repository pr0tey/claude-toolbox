# claude-toolbox

A marketplace of plugins for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Plugins extend Claude's behavior with custom skills, rules, hooks, and sub-agents.

## Concepts

Claude Code's plugin system has several building blocks:

| Concept | What it does |
|---------|-------------|
| **Marketplace** | A GitHub repo that hosts plugins. You register it once in settings. |
| **Plugin** | A bundle of skills, rules, hooks, and agents that extend Claude's behavior. |
| **Skill** | A slash command Claude can execute (e.g., `/mdr-init`). |
| **Rule** | A markdown file loaded at session start as persistent instructions for Claude. |
| **Hook** | A shell script that fires automatically on events (e.g., every user message). |
| **Agent** | A sub-agent (separate Claude instance) a plugin can delegate tasks to. |

## Plugins

| Plugin | Description |
|--------|-------------|
| [micro-decisions](plugins/micro-decisions/) | Persistent knowledge base of project decisions (Micro-Decision Records) |

## Installation

### 1. Add the marketplace

```shell
/plugin marketplace add pr0tey/claude-toolbox
```

### 2. Install a plugin

```shell
/plugin install micro-decisions@claude-toolbox
```

Or use the interactive UI: run `/plugin`, go to **Discover**, and select the plugin.

### 3. Reload

```shell
/reload-plugins
```

For team-wide setup via `settings.json`, see the [Claude Code docs](https://code.claude.com/docs/en/discover-plugins#configure-team-marketplaces).

## Testing

```bash
make test              # all plugin tests
make test-mdr-smoke    # micro-decisions smoke tests only
```

Requires Claude Code CLI installed and authenticated. See individual plugin docs for details.

## Contributing

To add a new plugin, create a directory under `plugins/` with a `plugin.json` and register it in `.claude-plugin/marketplace.json`.

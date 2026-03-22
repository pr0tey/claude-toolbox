---
name: mdr-init
description: Initialize Micro-Decision Records in the current project. Run once to set up scripts, agents, and hooks.
user-invocable: true
allowed-tools: Bash, Read, Write
---

# Initialize MDR in Project

Set up Micro-Decision Records for the current project.

## Steps

1. Create directories:
   ```
   mkdir -p .claude/mdr .claude/agents .claude/rules .mdr/decisions
   ```

2. Copy files from the plugin:
   ```
   # Scripts
   cp "${CLAUDE_PLUGIN_ROOT}/search.py" .claude/mdr/search.py

   # Hooks
   cp "${CLAUDE_PLUGIN_ROOT}/hooks/mdr-remind.sh" .claude/mdr/mdr-remind.sh
   chmod +x .claude/mdr/mdr-remind.sh

   # Agents
   cp "${CLAUDE_PLUGIN_ROOT}/agents/mdr-check.md" .claude/agents/mdr-check.md
   cp "${CLAUDE_PLUGIN_ROOT}/agents/mdr-save.md" .claude/agents/mdr-save.md

   # Rules
   cp "${CLAUDE_PLUGIN_ROOT}/rules/mdr-protocol.md" .claude/rules/mdr-protocol.md
   ```

3. Read `.claude/settings.json` (if it exists). If it already contains `mdr-remind`, skip to step 5. Otherwise, merge the following hooks into the file (create it if needed). Preserve any existing settings — only add the hooks:

   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "hooks": [
             {
               "type": "command",
               "command": ".claude/mdr/mdr-remind.sh"
             }
           ]
         }
       ],
       "SubagentStart": [
         {
           "hooks": [
             {
               "type": "command",
               "command": ".claude/mdr/mdr-remind.sh"
             }
           ]
         }
       ]
     }
   }
   ```

4. Inform the user:
   > MDR initialized. Restart your Claude Code session to activate rules.
   > Scripts: `.claude/mdr/`, agents: `.claude/agents/mdr-check.md` + `mdr-save.md`, rules: `.claude/rules/`, decisions: `.mdr/decisions/`, hooks: `.claude/settings.json`.

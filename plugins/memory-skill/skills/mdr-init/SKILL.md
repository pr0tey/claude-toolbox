---
name: mdr-init
description: Initialize Micro-Decision Records in the current project. Run once to set up scripts, skills, agent, and hooks.
user-invocable: true
allowed-tools: Bash, Read, Write
---

# Initialize MDR in Project

Set up Micro-Decision Records for the current project.

## Steps

1. Create directories:
   ```
   mkdir -p .claude/mdr .claude/agents .claude/skills/mdr-check .claude/skills/mdr-save .claude/rules .mdr/decisions
   ```

2. Copy files from the plugin:
   ```
   # Scripts
   cp "$PLUGIN_DIR/search.py" .claude/mdr/search.py
   cp "$PLUGIN_DIR/add-to-index.py" .claude/mdr/add-to-index.py

   # Hooks
   cp "$PLUGIN_DIR/hooks/mdr-remind.sh" .claude/mdr/mdr-remind.sh
   chmod +x .claude/mdr/mdr-remind.sh

   # Agent
   cp "$PLUGIN_DIR/agents/mdr.md" .claude/agents/mdr.md

   # Skills
   cp "$PLUGIN_DIR/skills/mdr-check/SKILL.md" .claude/skills/mdr-check/SKILL.md
   cp "$PLUGIN_DIR/skills/mdr-save/SKILL.md" .claude/skills/mdr-save/SKILL.md

   # Rules
   cp "$PLUGIN_DIR/rules/mdr-protocol.md" .claude/rules/mdr-protocol.md
   ```

3. Create an empty index if it does not exist:
   ```
   [ -f .mdr/index.json ] || echo '[]' > .mdr/index.json
   ```

4. Read `.claude/settings.json` (if it exists). If it already contains `mdr-remind`, skip to step 5. Otherwise, merge the following hooks into the file (create it if needed). Preserve any existing settings — only add the hooks:

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

5. Inform the user:
   > MDR initialized. Restart your Claude Code session to activate rules.
   > Scripts: `.claude/mdr/`, agent: `.claude/agents/mdr.md`, skills: `.claude/skills/`, rules: `.claude/rules/`, decisions: `.mdr/`, hooks: `.claude/settings.json`.

#!/bin/bash
# Skip reminder for mdr agents to avoid circular instructions
INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent_type',''))" 2>/dev/null)
if [ -z "$AGENT_TYPE" ]; then
  echo "$INPUT" | grep -qE '"mdr-check"|"mdr-save"' && exit 0
fi
if [ "$AGENT_TYPE" = "mdr-check" ] || [ "$AGENT_TYPE" = "mdr-save" ]; then
  exit 0
fi

cat <<'EOF'
<system-reminder>
MANDATORY: Before ANY decision → mdr-check agent. After ANY confirmed choice → mdr-save agent, proceed immediately (save runs in background).
User rejection/correction = new decision. Delegate to mdr-save agent first, then fix. Save is non-blocking.
</system-reminder>
EOF

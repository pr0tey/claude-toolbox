#!/bin/bash
# Skip reminder for mdr agent itself to avoid circular instructions
INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent_type',''))" 2>/dev/null)
if [ "$AGENT_TYPE" = "mdr" ]; then
  exit 0
fi

cat <<'EOF'
<system-reminder>
MANDATORY: Before ANY decision → mdr agent CHECK. After ANY confirmed choice → mdr agent SAVE, then proceed.
User rejection/correction = new decision. SAVE before fixing.
</system-reminder>
EOF

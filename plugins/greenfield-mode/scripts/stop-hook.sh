#!/bin/bash
# stop-hook.sh
# Greenfield reminder at session end

set -euo pipefail

CONFIG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/vibe-hacker.json"

# Check if greenfield mode is enabled
if [[ -f "$CONFIG_FILE" ]]; then
    enabled=$(jq -r '.greenfield_mode // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
    if [[ "$enabled" == "true" ]]; then
        # Inject greenfield reminder via systemMessage (Stop has no hookSpecificOutput support)
        cat << 'EOF'
{
  "systemMessage": "GREENFIELD SESSION ENDING: Before completing, verify no backwards-compatibility cruft was introduced. Check for: deprecation comments, legacy/obsolete markers, re-exports for compatibility, _unused variable renames, migration documentation. Delete old code entirely - don't deprecate or comment it out."
}
EOF
        exit 0
    fi
fi

# Greenfield mode not enabled - no output needed
exit 0

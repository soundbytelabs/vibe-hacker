#!/bin/bash
# stop-hook.sh
# Greenfield reminder at session end

set -euo pipefail

# Config resolution: prefer CLAUDE_PROJECT_DIR, fall back to git root
find_config() {
    if [[ -n "${CLAUDE_PROJECT_DIR:-}" && -f "$CLAUDE_PROJECT_DIR/.claude/vibe-hacker.json" ]]; then
        echo "$CLAUDE_PROJECT_DIR/.claude/vibe-hacker.json"
        return
    fi
    local git_root
    git_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    if [[ -n "$git_root" && -f "$git_root/.claude/vibe-hacker.json" ]]; then
        echo "$git_root/.claude/vibe-hacker.json"
        return
    fi
    echo ".claude/vibe-hacker.json"
}

CONFIG_FILE=$(find_config)

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

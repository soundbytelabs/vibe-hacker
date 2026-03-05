#!/bin/bash
# session-start.sh
# Prints greenfield mode status on session start
#
# Exit codes:
#   0 - Always (informational only)

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

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check if greenfield mode is enabled
is_greenfield_enabled() {
    if [[ -f "$CONFIG_FILE" ]]; then
        local enabled
        enabled=$(jq -r '.greenfield_mode // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
        [[ "$enabled" == "true" ]]
    else
        return 1
    fi
}

# Check if strict mode is enabled
is_strict_mode() {
    if [[ -f "$CONFIG_FILE" ]]; then
        local strict
        strict=$(jq -r '.greenfield_strict // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
        [[ "$strict" == "true" ]]
    else
        return 1
    fi
}

main() {
    if is_greenfield_enabled; then
        # Display to user terminal (stderr)
        echo "" >&2
        echo -e "${GREEN}GREENFIELD MODE${NC} ${CYAN}enabled${NC}" >&2
        if is_strict_mode; then
            echo -e "  ${YELLOW}Strict mode: ON${NC} - cruft will block edits" >&2
        else
            echo -e "  Strict mode: off - cruft will warn only" >&2
        fi
        echo -e "  No backwards compatibility needed. Delete, don't deprecate." >&2
        echo "" >&2

        # Inject context into Claude (stdout JSON)
        local context="GREENFIELD MODE ACTIVE: This is a prototype project with zero users. When making changes: DELETE old code entirely (don't deprecate or comment out), NO backwards-compatibility shims or re-exports, NO deprecation comments, NO migration documentation. Clean breaks only."

        # Escape for JSON
        context=$(echo "$context" | jq -Rs '.')

        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${context}
  }
}
EOF
    fi

    exit 0
}

main "$@"

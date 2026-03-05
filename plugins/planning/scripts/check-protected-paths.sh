#!/bin/bash
# check-protected-paths.sh
# Enforces path protection rules configured in vibe-hacker.json
#
# Usage:
#   - As PreToolUse hook: receives JSON on stdin with tool_input.file_path
#   - Direct: ./check-protected-paths.sh <file_path>
#
# Protection tiers:
#   - readonly: Block edit entirely with explanation
#   - guided: Block edit, suggest using a skill instead
#   - remind: Allow edit but show reminder message
#
# Output (for PreToolUse hook):
#   JSON with hookSpecificOutput.permissionDecision = "deny" | "allow"

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

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CONFIG_FILE=$(find_config)

# Colors for stderr messages
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check if protected_paths is configured
has_protected_paths() {
    if [[ -f "$CONFIG_FILE" ]]; then
        local count
        count=$(jq -r '.protected_paths.rules | length // 0' "$CONFIG_FILE" 2>/dev/null || echo "0")
        [[ "$count" -gt 0 ]]
    else
        return 1
    fi
}

# Match a file path against a glob pattern
# Uses bash extended globbing
matches_pattern() {
    local file_path="$1"
    local pattern="$2"

    # Make path relative to project dir for matching
    local rel_path="${file_path#$PROJECT_DIR/}"

    # Enable extended globbing
    shopt -s extglob nullglob

    # Convert glob pattern to regex for matching
    # Handle ** (any path), * (any segment), ? (any char)
    local regex_pattern="$pattern"
    regex_pattern="${regex_pattern//\*\*/.*}"      # ** -> .*
    regex_pattern="${regex_pattern//\*/[^/]*}"     # * -> [^/]*
    regex_pattern="${regex_pattern//\?/.}"          # ? -> .
    regex_pattern="^${regex_pattern}$"

    if [[ "$rel_path" =~ $regex_pattern ]]; then
        return 0
    fi

    return 1
}

# Find matching rule for a file path
# Returns JSON object with tier and message, or empty if no match
find_matching_rule() {
    local file_path="$1"

    if ! has_protected_paths; then
        return
    fi

    local rules_count
    rules_count=$(jq -r '.protected_paths.rules | length' "$CONFIG_FILE")

    for ((i=0; i<rules_count; i++)); do
        local pattern
        local tier
        local message
        local skill

        pattern=$(jq -r ".protected_paths.rules[$i].pattern" "$CONFIG_FILE")
        tier=$(jq -r ".protected_paths.rules[$i].tier" "$CONFIG_FILE")
        message=$(jq -r ".protected_paths.rules[$i].message // \"This path is protected.\"" "$CONFIG_FILE")
        skill=$(jq -r ".protected_paths.rules[$i].skill // empty" "$CONFIG_FILE")

        if matches_pattern "$file_path" "$pattern"; then
            jq -n \
                --arg tier "$tier" \
                --arg message "$message" \
                --arg skill "$skill" \
                --arg pattern "$pattern" \
                '{tier: $tier, message: $message, skill: $skill, pattern: $pattern}'
            return
        fi
    done
}

# Output deny decision for PreToolUse hook
output_deny() {
    local reason="$1"

    jq -n \
        --arg reason "$reason" \
        '{
            hookSpecificOutput: {
                hookEventName: "PreToolUse",
                permissionDecision: "deny",
                permissionDecisionReason: $reason
            }
        }'
}

# Output allow decision (or just exit 0)
output_allow() {
    exit 0
}

# Output allow with reminder context
output_remind() {
    local message="$1"
    local file_path="$2"

    jq -n \
        --arg context "REMINDER for $file_path: $message" \
        '{
            hookSpecificOutput: {
                hookEventName: "PreToolUse",
                additionalContext: $context
            }
        }'
    exit 0
}

main() {
    local file_path=""

    # Get file path from argument or stdin
    if [[ $# -gt 0 ]]; then
        file_path="$1"
    elif [[ ! -t 0 ]]; then
        local input
        input=$(cat)
        file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
    fi

    # No file path = nothing to check
    if [[ -z "$file_path" ]]; then
        output_allow
    fi

    # No config = nothing to enforce
    if ! has_protected_paths; then
        output_allow
    fi

    # Find matching rule
    local rule
    rule=$(find_matching_rule "$file_path")

    if [[ -z "$rule" ]]; then
        output_allow
    fi

    local tier
    local message
    local skill
    local pattern

    tier=$(echo "$rule" | jq -r '.tier')
    message=$(echo "$rule" | jq -r '.message')
    skill=$(echo "$rule" | jq -r '.skill // empty')
    pattern=$(echo "$rule" | jq -r '.pattern')

    case "$tier" in
        readonly)
            # Block with explanation
            local reason="PROTECTED PATH: $file_path

$message

This file matches pattern: $pattern"
            output_deny "$reason"
            exit 0
            ;;

        guided)
            # Block with skill suggestion and planning commands
            local reason="PROTECTED PATH: $file_path

$message"
            if [[ -n "$skill" && "$skill" == "planning" ]]; then
                reason="$reason

To manage planning documents, use the planning skill scripts:

  # Create new documents (auto-numbered)
  python3 \${CLAUDE_PLUGIN_ROOT}/skills/planning/scripts/new.py adr \"Title\"
  python3 \${CLAUDE_PLUGIN_ROOT}/skills/planning/scripts/new.py fdp \"Title\"
  python3 \${CLAUDE_PLUGIN_ROOT}/skills/planning/scripts/new.py ap \"Title\"

  # Archive documents
  python3 \${CLAUDE_PLUGIN_ROOT}/skills/planning/scripts/archive.py ADR-001

  # List documents
  python3 \${CLAUDE_PLUGIN_ROOT}/skills/planning/scripts/list.py"
            elif [[ -n "$skill" ]]; then
                reason="$reason

Use the $skill skill to modify this document."
            fi
            reason="$reason

Pattern: $pattern"
            output_deny "$reason"
            exit 0
            ;;

        remind)
            # Allow but show reminder on stderr and inject context
            echo -e "${YELLOW}REMINDER:${NC} $message" >&2
            echo -e "${CYAN}File:${NC} $file_path" >&2
            output_remind "$message" "$file_path"
            ;;

        *)
            # Unknown tier, allow
            output_allow
            ;;
    esac
}

main "$@"

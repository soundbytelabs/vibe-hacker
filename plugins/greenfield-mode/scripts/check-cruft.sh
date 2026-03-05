#!/bin/bash
# check-cruft.sh
# Detects backwards-compatibility cruft in greenfield projects
#
# Usage:
#   - As PostToolUse hook: receives JSON on stdin with tool_input.file_path
#   - Direct: ./check-cruft.sh [file_path]
#
# Exit codes:
#   0 - No cruft found or greenfield mode disabled (approve)
#   2 - Cruft detected (warn but approve - greenfield is advisory)

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

# Default excludes - config files that contain pattern definitions
DEFAULT_EXCLUDES=(
    '*.json'
    '*.yaml'
    '*.yml'
)

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

# Load exclude patterns from config or use defaults
load_excludes() {
    if [[ -f "$CONFIG_FILE" ]]; then
        local excludes_json
        excludes_json=$(jq -r '.greenfield_exclude // empty' "$CONFIG_FILE" 2>/dev/null || true)

        if [[ -n "$excludes_json" && "$excludes_json" != "null" ]]; then
            local excludes=()
            while IFS= read -r pattern; do
                [[ -n "$pattern" ]] && excludes+=("$pattern")
            done < <(echo "$excludes_json" | jq -r '.[]' 2>/dev/null)

            if [[ ${#excludes[@]} -gt 0 ]]; then
                # Merge with defaults
                EXCLUDE_PATTERNS=("${DEFAULT_EXCLUDES[@]}" "${excludes[@]}")
                return
            fi
        fi
    fi
    EXCLUDE_PATTERNS=("${DEFAULT_EXCLUDES[@]}")
}

# Check if file matches any exclude pattern
is_excluded() {
    local file="$1"
    local basename
    basename=$(basename "$file")

    # Auto-exclude plugin's own directory (meta-documentation)
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
        local normalized_root normalized_file
        normalized_root=$(cd "$CLAUDE_PLUGIN_ROOT" 2>/dev/null && pwd)
        normalized_file=$(cd "$(dirname "$file")" 2>/dev/null && pwd)/$(basename "$file")
        if [[ -n "$normalized_root" && "$normalized_file" == "$normalized_root"* ]]; then
            return 0
        fi
    fi

    shopt -s extglob nullglob
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        # Check against full path and basename
        if [[ "$file" == $pattern ]] || [[ "$basename" == $pattern ]]; then
            return 0
        fi
        # Handle ** glob patterns
        if [[ "$pattern" == *"**"* ]]; then
            # Convert ** to regex-like matching
            local regex_pattern="${pattern//\*\*/.*}"
            regex_pattern="${regex_pattern//\*/[^/]*}"
            if [[ "$file" =~ $regex_pattern ]]; then
                return 0
            fi
        fi
    done
    shopt -u extglob nullglob
    return 1
}

# Check if strict mode is enabled (block instead of warn)
is_strict_mode() {
    if [[ -f "$CONFIG_FILE" ]]; then
        local strict
        strict=$(jq -r '.greenfield_strict // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
        [[ "$strict" == "true" ]]
    else
        return 1
    fi
}

# Exit early if greenfield mode not enabled
if ! is_greenfield_enabled; then
    exit 0
fi

# Default cruft patterns (matched case-insensitively via grep -i)
# Simple readable patterns - no need for [Ll] tricks since grep -i handles it
DEFAULT_PATTERNS=(
    'deprecated'
    'legacy'
    'obsolete'
    'backwards.compat'
    'backward.compat'
    'for compatibility'
    'TODO:.*remove.*migrat'
    'TODO:.*remove.*later'
    'temporary.*shim'
    '_unused'
    're-export'
    'FIXME:.*compat'
)

# Load custom patterns from config or use defaults
load_patterns() {
    if [[ -f "$CONFIG_FILE" ]]; then
        local patterns_json
        patterns_json=$(jq -r '.greenfield_patterns // empty' "$CONFIG_FILE" 2>/dev/null || true)

        if [[ -n "$patterns_json" && "$patterns_json" != "null" ]]; then
            local patterns=()
            while IFS= read -r pattern; do
                [[ -n "$pattern" ]] && patterns+=("$pattern")
            done < <(echo "$patterns_json" | jq -r '.[]' 2>/dev/null)

            if [[ ${#patterns[@]} -gt 0 ]]; then
                CRUFT_PATTERNS=("${patterns[@]}")
                return
            fi
        fi
    fi
    CRUFT_PATTERNS=("${DEFAULT_PATTERNS[@]}")
}

load_patterns
load_excludes

# Colors
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

check_file() {
    local file="$1"
    local found=0

    [[ ! -f "$file" ]] && return 0

    # Check exclusions
    if is_excluded "$file"; then
        return 0
    fi

    # Skip binary files
    if file "$file" 2>/dev/null | grep -q "binary\|executable\|image"; then
        return 0
    fi

    # For markdown files, strip backticked content before checking
    # Backticks indicate meta-references (documenting patterns, not using them)
    local content
    if [[ "$file" == *.md ]]; then
        # Remove fenced code blocks (```...```) and inline code (`...`)
        content=$(sed -e '/^```/,/^```/d' -e 's/`[^`]*`//g' "$file")
    else
        content=$(cat "$file")
    fi

    for pattern in "${CRUFT_PATTERNS[@]}"; do
        if echo "$content" | grep -qi "$pattern" 2>/dev/null; then
            if [[ $found -eq 0 ]]; then
                echo -e "${YELLOW}Potential cruft in: $file${NC}" >&2
                found=1
            fi
            echo -e "  ${YELLOW}→${NC} '$pattern'" >&2
            # Show matches from original file for context
            grep -n -i "$pattern" "$file" 2>/dev/null | head -2 | sed 's/^/    /' >&2
        fi
    done

    return $found
}

main() {
    local file_path=""

    # Get file from args or stdin JSON
    if [[ $# -gt 0 ]]; then
        file_path="$1"
    elif [[ ! -t 0 ]]; then
        local input
        input=$(cat)
        file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
    fi

    if [[ -z "$file_path" || ! -f "$file_path" ]]; then
        exit 0
    fi

    if ! check_file "$file_path"; then
        # Display friendly reminder to user terminal (stderr)
        echo "" >&2
        echo -e "${YELLOW}Greenfield check: Please review the above matches.${NC}" >&2
        echo -e "${YELLOW}If intentional, no action needed. Otherwise, consider removing.${NC}" >&2

        # Build context message for Claude
        local context="Potential cruft detected in $file_path - This is a greenfield project. Please review the flagged patterns (deprecated, legacy, etc). If these are intentional or false positives, no action needed. Otherwise, consider removing backwards-compatibility code since there are no users to migrate."
        context=$(echo "$context" | jq -Rs '.')

        if is_strict_mode; then
            cat <<EOF
{
  "decision": "block",
  "reason": "Potential cruft detected. Please review and address before continuing.",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": ${context}
  }
}
EOF
            exit 0
        else
            cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": ${context}
  }
}
EOF
            exit 0
        fi
    fi

    exit 0
}

main "$@"

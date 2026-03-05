#!/bin/bash
# prime.sh - Context priming for Claude Code sessions
#
# Loads project context from .claude/vibe-hacker.json config.
# Falls back to README.md / CLAUDE.md if no config.
#
# Config resolution (multi-repo aware):
#   1. CLAUDE_PROJECT_DIR (authoritative workspace root when set)
#   2. Git root (standalone repo fallback, prevents parent leakage)
#   3. Current directory (last resort)
#
# Output strategy:
# - stderr: Priming display (for user's terminal)
# - stdout: JSON with additionalContext (for Claude's context injection)

set -euo pipefail

# --- Config Resolution ---

find_config() {
    # CLAUDE_PROJECT_DIR is authoritative — it's the workspace root
    if [[ -n "${CLAUDE_PROJECT_DIR:-}" && -f "$CLAUDE_PROJECT_DIR/.claude/vibe-hacker.json" ]]; then
        echo "$CLAUDE_PROJECT_DIR/.claude/vibe-hacker.json"
        return
    fi

    # Fall back to git root (prevents parent-repo leakage for standalone use)
    local git_root
    git_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    if [[ -n "$git_root" && -f "$git_root/.claude/vibe-hacker.json" ]]; then
        echo "$git_root/.claude/vibe-hacker.json"
        return
    fi

    # Last resort
    echo ".claude/vibe-hacker.json"
}

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR"

CONFIG_FILE=$(find_config)

# --- Collect priming data ---

declare -a FILES=()
INSTRUCTIONS=""

# Check greenfield mode
GREENFIELD="disabled"
if [[ -f "$CONFIG_FILE" ]]; then
    gf=$(jq -r '.greenfield_mode // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
    [[ "$gf" == "true" ]] && GREENFIELD="enabled"
fi

# Check haiku mode
HAIKU="disabled"
if [[ -f "$CONFIG_FILE" ]]; then
    hk=$(jq -r '.priming.haiku // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
    [[ "$hk" == "true" ]] && HAIKU="enabled"
fi

# Load priming config
if [[ -f "$CONFIG_FILE" ]]; then
    INSTRUCTIONS=$(jq -r '.priming.instructions // empty' "$CONFIG_FILE" 2>/dev/null || true)

    while IFS= read -r file; do
        [[ -n "$file" && -f "$file" ]] && FILES+=("$file")
    done < <(jq -r '.priming.files[]? // empty' "$CONFIG_FILE" 2>/dev/null || true)

    while IFS= read -r pattern; do
        if [[ -n "$pattern" ]]; then
            for file in $pattern; do
                [[ -f "$file" ]] && FILES+=("$file")
            done
        fi
    done < <(jq -r '.priming.globs[]? // empty' "$CONFIG_FILE" 2>/dev/null || true)
fi

# Fallback if no files configured
if [[ ${#FILES[@]} -eq 0 ]]; then
    [[ -f ".claude/CLAUDE.md" ]] && FILES+=(".claude/CLAUDE.md")
    [[ -f "README.md" ]] && FILES+=("README.md")

    if [[ ${#FILES[@]} -eq 0 && -d "docs" ]]; then
        while IFS= read -r file; do
            FILES+=("$file")
        done < <(find docs -name "*.md" -type f 2>/dev/null | head -5)
    fi
fi

# Remove duplicates
declare -A seen
UNIQUE=()
for f in "${FILES[@]}"; do
    if [[ -z "${seen[$f]:-}" ]]; then
        seen[$f]=1
        UNIQUE+=("$f")
    fi
done

# --- Multi-repo status ---

collect_repo_status() {
    local repo_path="$1"
    local repo_name
    repo_name=$(basename "$repo_path")

    if [[ ! -d "$repo_path/.git" && ! -f "$repo_path/.git" ]]; then
        echo "$repo_name|not a repo|-|-"
        return
    fi

    local branch dirty last_age last_msg

    branch=$(git -C "$repo_path" branch --show-current 2>/dev/null || echo "detached")

    local changed
    changed=$(git -C "$repo_path" status --porcelain 2>/dev/null | wc -l)
    if [[ "$changed" -eq 0 ]]; then
        dirty="clean"
    else
        dirty="${changed} modified"
    fi

    local last_epoch now_epoch age_seconds
    last_epoch=$(git -C "$repo_path" log -1 --format='%ct' 2>/dev/null || echo "0")
    now_epoch=$(date +%s)
    age_seconds=$((now_epoch - last_epoch))

    if [[ "$last_epoch" -eq 0 ]]; then
        last_age="no commits"
    elif [[ "$age_seconds" -lt 3600 ]]; then
        last_age="$((age_seconds / 60))m ago"
    elif [[ "$age_seconds" -lt 86400 ]]; then
        last_age="$((age_seconds / 3600))h ago"
    else
        last_age="$((age_seconds / 86400))d ago"
    fi

    last_msg=$(git -C "$repo_path" log -1 --format='%s' 2>/dev/null | head -c 50 || echo "")

    echo "$repo_name|$branch|$dirty|$last_age|$last_msg"
}

REPO_STATUS_LINES=()
REPO_STATUS_TEXT=""

if [[ -f "$CONFIG_FILE" ]]; then
    declare -a REPOS=()
    while IFS= read -r repo; do
        [[ -n "$repo" ]] && REPOS+=("$repo")
    done < <(jq -r '.priming.repos[]? // empty' "$CONFIG_FILE" 2>/dev/null || true)

    if [[ ${#REPOS[@]} -gt 0 ]]; then
        for repo in "${REPOS[@]}"; do
            if [[ -d "$repo" ]]; then
                REPO_STATUS_LINES+=("$(collect_repo_status "$repo")")
            fi
        done

        if [[ ${#REPO_STATUS_LINES[@]} -gt 0 ]]; then
            # Find max widths for alignment
            max_name=0
            max_branch=0
            max_dirty=0
            max_age=0
            for line in "${REPO_STATUS_LINES[@]}"; do
                IFS='|' read -r name branch dirty age msg <<< "$line"
                (( ${#name} > max_name )) && max_name=${#name}
                (( ${#branch} > max_branch )) && max_branch=${#branch}
                (( ${#dirty} > max_dirty )) && max_dirty=${#dirty}
                (( ${#age} > max_age )) && max_age=${#age}
            done

            REPO_STATUS_TEXT="WORKSPACE REPOS:"
            for line in "${REPO_STATUS_LINES[@]}"; do
                IFS='|' read -r name branch dirty age msg <<< "$line"
                REPO_STATUS_TEXT+=$'\n'"  $(printf "%-${max_name}s  %-${max_branch}s  %-${max_dirty}s  %-${max_age}s  %s" "$name" "$branch" "$dirty" "$age" "$msg")"
            done
        fi
    fi
fi

# --- Display to terminal (stderr) ---

{
    echo "=== CONTEXT PRIMING ==="
    echo ""

    if [[ -n "$REPO_STATUS_TEXT" ]]; then
        echo "$REPO_STATUS_TEXT"
        echo ""
    fi

    if [[ "$GREENFIELD" == "enabled" ]]; then
        echo "Greenfield mode: ENABLED"
        echo ""
    fi

    if [[ "$HAIKU" == "enabled" ]]; then
        echo "Haiku mode: ENABLED"
        echo ""
    fi

    if [[ -n "$INSTRUCTIONS" ]]; then
        echo "Instructions: $INSTRUCTIONS"
        echo ""
    fi

    echo "Loading ${#UNIQUE[@]} files: ${UNIQUE[*]}"
    echo ""
    echo "=== END PRIMING ==="
} >&2

# --- Build context for Claude (stdout JSON) ---

CONTEXT_PARTS=()

if [[ -n "$REPO_STATUS_TEXT" ]]; then
    CONTEXT_PARTS+=("$REPO_STATUS_TEXT")
fi

if [[ "$GREENFIELD" == "enabled" ]]; then
    CONTEXT_PARTS+=("GREENFIELD MODE: This is a prototype project with zero users. Delete old code entirely, no backwards compatibility needed, no deprecation comments.")
fi

if [[ -n "$INSTRUCTIONS" ]]; then
    CONTEXT_PARTS+=("INSTRUCTIONS: $INSTRUCTIONS")
fi

for file in "${UNIQUE[@]}"; do
    content=$(cat "$file" | jq -Rs '.')
    CONTEXT_PARTS+=("FILE: $file
${content}")
done

if [[ "$HAIKU" == "enabled" ]]; then
    CONTEXT_PARTS+=("HAIKU REQUEST: Please write a creative haiku (5-7-5 syllables) that captures the essence of this project based on the primed content above. This confirms you are ready.")
fi

FULL_CONTEXT=$(printf '%s\n\n' "${CONTEXT_PARTS[@]}" | jq -Rs '.')

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${FULL_CONTEXT}
  }
}
EOF

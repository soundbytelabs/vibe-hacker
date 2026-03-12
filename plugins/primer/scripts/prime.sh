#!/bin/bash
# prime.sh - Context priming for Claude Code sessions
#
# Loads project context from .claude/vibe-hacker.json config.
# Falls back to README.md / CLAUDE.md if no config.
#
# Usage:
#   prime.sh              # Load default priming files
#   prime.sh <focus>      # Load named focus (e.g., "sbl", "hw", "cecrops")
#   prime.sh --list       # List available focuses
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

FOCUS="${1:-}"

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

# --- Focus resolution ---

list_focuses() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "No config file found" >&2
        return 1
    fi

    local focuses
    focuses=$(jq -r '.priming.focuses // empty | keys[]' "$CONFIG_FILE" 2>/dev/null || true)

    if [[ -z "$focuses" ]]; then
        echo "No focuses configured in priming.focuses" >&2
        return 1
    fi

    echo "Available focuses:" >&2
    while IFS= read -r name; do
        local desc
        desc=$(jq -r ".priming.focuses[\"$name\"].instructions // \"(no description)\"" "$CONFIG_FILE" 2>/dev/null || echo "(no description)")
        # Truncate long descriptions
        if [[ ${#desc} -gt 70 ]]; then
            desc="${desc:0:67}..."
        fi
        echo "  $name — $desc" >&2
    done <<< "$focuses"
}

if [[ "$FOCUS" == "--list" ]]; then
    list_focuses
    exit 0
fi

# Validate focus if provided
if [[ -n "$FOCUS" && -f "$CONFIG_FILE" ]]; then
    focus_exists=$(jq -r ".priming.focuses[\"$FOCUS\"] // empty" "$CONFIG_FILE" 2>/dev/null || true)
    if [[ -z "$focus_exists" ]]; then
        echo "Unknown focus: '$FOCUS'" >&2
        echo "" >&2
        list_focuses
        exit 1
    fi
fi

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
    hk=$(jq -r '.priming.haiku // true' "$CONFIG_FILE" 2>/dev/null || echo "true")
    [[ "$hk" == "true" ]] && HAIKU="enabled"
fi

# Load priming config — either from focus or from defaults
if [[ -f "$CONFIG_FILE" ]]; then
    if [[ -n "$FOCUS" ]]; then
        # Focus mode: load from priming.focuses.$FOCUS
        INSTRUCTIONS=$(jq -r ".priming.focuses[\"$FOCUS\"].instructions // empty" "$CONFIG_FILE" 2>/dev/null || true)

        while IFS= read -r file; do
            [[ -n "$file" && -f "$file" ]] && FILES+=("$file")
        done < <(jq -r ".priming.focuses[\"$FOCUS\"].files[]? // empty" "$CONFIG_FILE" 2>/dev/null || true)

        while IFS= read -r pattern; do
            if [[ -n "$pattern" ]]; then
                for file in $pattern; do
                    [[ -f "$file" ]] && FILES+=("$file")
                done
            fi
        done < <(jq -r ".priming.focuses[\"$FOCUS\"].globs[]? // empty" "$CONFIG_FILE" 2>/dev/null || true)
    else
        # Default mode: load from priming.files/globs
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
fi

# Fallback if no files configured (only in default mode)
if [[ ${#FILES[@]} -eq 0 && -z "$FOCUS" ]]; then
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

    if [[ -n "$FOCUS" ]]; then
        # Focus mode: use focus-specific repos, fall back to top-level
        while IFS= read -r repo; do
            [[ -n "$repo" ]] && REPOS+=("$repo")
        done < <(jq -r ".priming.focuses[\"$FOCUS\"].repos[]? // empty" "$CONFIG_FILE" 2>/dev/null || true)

        # Fall back to top-level repos if focus doesn't define any
        if [[ ${#REPOS[@]} -eq 0 ]]; then
            while IFS= read -r repo; do
                [[ -n "$repo" ]] && REPOS+=("$repo")
            done < <(jq -r '.priming.repos[]? // empty' "$CONFIG_FILE" 2>/dev/null || true)
        fi
    else
        while IFS= read -r repo; do
            [[ -n "$repo" ]] && REPOS+=("$repo")
        done < <(jq -r '.priming.repos[]? // empty' "$CONFIG_FILE" 2>/dev/null || true)
    fi

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
    if [[ -n "$FOCUS" ]]; then
        echo "=== CONTEXT PRIMING (focus: $FOCUS) ==="
    else
        echo "=== CONTEXT PRIMING ==="
    fi
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

if [[ -n "$FOCUS" ]]; then
    CONTEXT_PARTS+=("FOCUS: $FOCUS")
fi

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

# If haiku enabled, add request directly to additionalContext.
if [[ "$HAIKU" == "enabled" ]]; then
    CONTEXT_PARTS+=("HAIKU REQUEST: Please write a creative haiku (5-7-5 syllables) that captures the essence of this project based on the primed context. This confirms you are primed and ready.")
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

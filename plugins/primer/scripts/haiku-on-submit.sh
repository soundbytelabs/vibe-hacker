#!/bin/bash
# haiku-on-submit.sh - Emit haiku request on first user prompt after priming
#
# Runs as a UserPromptSubmit hook. Checks for a marker file left by the
# SessionStart prime.sh script. If found, emits the haiku request to stdout
# (which Claude sees and can act on), then removes the marker so it only
# fires once per session.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MARKER="$PROJECT_DIR/.claude/.primer-haiku-pending"

if [[ -f "$MARKER" ]]; then
    rm -f "$MARKER"
    echo "HAIKU REQUEST: Please write a creative haiku (5-7-5 syllables) that captures the essence of this project based on the primed context. This confirms you are primed and ready."
fi

exit 0

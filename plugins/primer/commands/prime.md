Reload project context from configured priming settings.

**Usage:**
- `/prime` — Load all default priming files
- `/prime <focus>` — Load a named focus subset (e.g., `sbl`, `hw`, `cecrops`)
- `/prime --list` — List available focuses

Run: `${CLAUDE_PLUGIN_ROOT}/scripts/prime.sh` (append any arguments from the user)

This loads files configured in `.claude/vibe-hacker.json`. Without arguments, loads `priming.files`. With a focus name, loads `priming.focuses.<name>.files` instead — a narrower context for focused work.

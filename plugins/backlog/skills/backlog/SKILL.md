---
name: backlog
description: Manage project backlogs — capture ideas, track polish items, prioritize work. Use for lightweight task tracking below the formality of planning docs.
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Backlog Skill

Manage lightweight project backlogs. Backlogs are for ideas, polish items, and small improvements — things too informal for FDPs/APs but worth tracking.

## When to Use

- Capturing polish ideas while working ("this could use velocity sensitivity")
- Tracking small improvements that don't warrant a planning document
- Managing a queue of tasks for a specific project or area
- Reviewing what's open and deciding what to tackle next

## Script

All operations go through the management script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py <command> [args...]
```

## Commands

### Create a backlog

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py create <name> "<description>"
```

Example:
```bash
python3 .../manage.py create davis "Polish ideas for Davis voice project"
python3 .../manage.py create sbl-core "Core library improvements"
```

### Add an item

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py add <name> "<item>" [--priority high|med|low] [--notes "<details>"]
```

Examples:
```bash
python3 .../manage.py add davis "Velocity sensitivity on envelope" --priority high --notes "Scale attack time + level"
python3 .../manage.py add davis "LED feedback for active CC page" --priority low
python3 .../manage.py add davis "Investigate chorus on output"
```

### List items

```bash
# List a specific backlog
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py list <name> [--status open|done|dropped]

# List all backlogs (summary)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py list
```

### Mark done

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py done <name> <id>
```

### Drop an item

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py drop <name> <id> ["<reason>"]
```

### Reopen

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py reopen <name> <id>
```

### Edit item text

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py edit <name> <id> "<new text>"
```

### Change priority

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/backlog/scripts/manage.py prioritize <name> <id> high|med|low|none
```

## Review

When the user asks to review a backlog (e.g., `/backlog review davis`), do NOT use the script. Instead:

1. Read the backlog file directly from the configured root (default: `docs/backlogs/<name>.md`)
2. Read relevant project context (roadmap, recent work, related code)
3. Provide analysis:
   - Are any items stale or already done?
   - Are priorities still accurate given current project state?
   - Which items should be tackled next?
   - Are there related items that could be batched?
   - Should any items be promoted to a planning document (FDP/AP)?
4. Suggest concrete next actions

## Configuration

Backlogs are stored in the directory configured in `.claude/vibe-hacker.json`:

```json
{
  "backlog": {
    "root": "docs/backlogs"
  }
}
```

Default root: `docs/backlogs/`

## Conventions

- **Backlog names** are kebab-case identifiers: `davis`, `sbl-core`, `patch-init`
- **Items** are single-line descriptions, optionally with `— notes` appended
- **Priorities**: `high` (do soon), `med` (do eventually), `low` (nice to have), or omitted (unprioritized)
- **IDs** auto-increment and are never reused
- Items move between Open → Done or Open → Dropped. Reopen moves back to Open.
- When adding items mid-task, keep it quick — one-liner capture, move on

## Parsing Arguments

When the user invokes `/backlog`, parse their intent from the arguments:

| User says | Command |
|-----------|---------|
| `/backlog create davis "Davis polish"` | `create davis "Davis polish"` |
| `/backlog add davis "Add velocity"` | `add davis "Add velocity"` |
| `/backlog davis` or `/backlog list davis` | `list davis` |
| `/backlog` or `/backlog list` | `list` (all backlogs) |
| `/backlog done davis 3` | `done davis 3` |
| `/backlog drop davis 3` | `drop davis 3` |
| `/backlog review davis` | Review (inline analysis, no script) |
| `/backlog davis add "thing"` | `add davis "thing"` (flexible order) |

Be flexible with argument order. The user might say `/backlog davis` to mean "show me the davis backlog."

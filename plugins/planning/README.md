# Planning

A Claude Code plugin for structured planning documents with protected paths.

## Features

### Planning Documents (v0.2.1)

Manage ADRs, FDPs, Action Plans, Reports, and Roadmaps with:
- YAML frontmatter for structured metadata
- Document relationships (supersedes, related)
- Append-only addenda for locked documents
- Automatic numbering and lifecycle management

| Type | Purpose | ID Format | Default Dir |
|------|---------|-----------|-------------|
| ADR | Architecture Decision Record | `ADR-001` | `decisions/` |
| FDP | Feature Design Proposal | `FDP-001` | `designs/` |
| AP | Action Plan | `AP-001` | `action-plans/` |
| Report | Reports and analysis | `RPT-001` | `reports/` |
| Roadmap | Project goals | N/A | `roadmap.md` |

### Basic Operations

**Creating documents** (auto-numbered with frontmatter):
```bash
python3 scripts/new.py adr "Use PostgreSQL"
python3 scripts/new.py fdp "User Authentication"
python3 scripts/new.py ap "Implement login"
python3 scripts/new.py report "Q4 Analysis"
```

**Updating status**:
```bash
python3 scripts/update-status.py ADR-001 accepted
python3 scripts/update-status.py FDP-001 "in progress"
python3 scripts/update-status.py RPT-001 published
```

**Listing documents**:
```bash
python3 scripts/list.py
python3 scripts/list.py --type adr
python3 scripts/list.py --type report
```

**Archiving completed documents**:
```bash
python3 scripts/archive.py ADR-001
```

### New in v0.2.1

**Add addenda to locked documents**:
```bash
python3 scripts/append.py ADR-001 "Performance Note" --body "Read replicas work well"
```

**Supersede a document**:
```bash
python3 scripts/supersede.py ADR-001 "Revised Database Strategy"
```

**Link related documents**:
```bash
python3 scripts/relate.py ADR-001 FDP-003 --bidirectional
```

**Migrate existing documents**:
```bash
python3 scripts/vibe-doc.py status
python3 scripts/vibe-doc.py upgrade --dry-run
python3 scripts/vibe-doc.py upgrade
```

### Protected Paths

Control access to files with three protection tiers:

| Tier | Behavior | Use Case |
|------|----------|----------|
| `readonly` | Blocks edits completely | Archives, historical records |
| `guided` | Blocks with skill suggestion | Planning docs |
| `remind` | Warns but allows edit | Templates, configs |

### Roadmap Reminder

PreCompact hook reminds you to update the roadmap before context compaction.

## Installation

```bash
/plugin marketplace add /path/to/vibe-hacker
/plugin install planning@vibe-hacker
```

## Configuration

Create `.claude/vibe-hacker.json` in your project:

```json
{
  "planning": {
    "version": "0.2.1",
    "subdirs": {
      "adr": "decisions",
      "fdp": "designs",
      "ap": "action-plans",
      "report": "reports"
    }
  },
  "protected_paths": {
    "planning_root": "docs/planning",
    "rules": [
      {
        "pattern": "docs/planning/*/archive/**",
        "tier": "readonly",
        "message": "Archives are read-only."
      },
      {
        "pattern": "docs/planning/**/*.md",
        "tier": "remind",
        "skill": "planning",
        "message": "Use the planning skill to manage these."
      }
    ]
  }
}
```

### Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `planning.version` | string | `"0.1.0"` | Schema version |
| `planning.subdirs.adr` | string | `"decisions"` | Subdirectory for ADRs |
| `planning.subdirs.fdp` | string | `"designs"` | Subdirectory for FDPs |
| `planning.subdirs.ap` | string | `"action-plans"` | Subdirectory for Action Plans |
| `planning.subdirs.report` | string | `"reports"` | Subdirectory for Reports |
| `protected_paths.planning_root` | string | `"docs/planning"` | Root for planning docs |
| `protected_paths.rules` | array | `[]` | Protection rules |

## Document Format

All documents use YAML frontmatter:

```yaml
---
type: adr
id: ADR-001
status: accepted
created: 2025-12-13
modified: 2025-12-13
supersedes: null
superseded_by: null
obsoleted_by: null
related: [FDP-003]
---

# ADR-001: Title

## Status
Accepted

...content...

---

## Addenda

### 2025-12-13: Clarification
Additional notes added after acceptance.
```

## Hooks

| Event | Behavior |
|-------|----------|
| PreCompact | Remind to update roadmap |
| PreToolUse (Edit/Write) | Check protected paths |

## Requirements

- [jq](https://jqlang.github.io/jq/) - JSON processor
- Python 3.x - For planning scripts
- PyYAML (optional) - For better YAML handling

## Part of Vibe Hacker

This plugin is part of the [vibe-hacker](https://github.com/mjrskiles/vibe-hacker) plugin collection:

- **greenfield-mode** - Cruft prevention for prototypes
- **primer** - Context priming
- **planning** (this plugin) - ADRs, FDPs, Action Plans, Reports, Roadmap
- **expert-agents** - Code auditors, build/test/arch/size agents
- **backlog** - Lightweight project backlogs
- **briefcase** - Personal thought management

## License

MIT

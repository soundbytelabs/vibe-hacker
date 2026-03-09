# Vibe Hacker

A collection of Claude Code plugins for hacking, development workflows, and greenfield projects.

## Plugins

| Plugin | Description | Use Case |
|--------|-------------|----------|
| [greenfield-mode](plugins/greenfield-mode/) | Prevent backwards-compatibility cruft | Prototype projects |
| [primer](plugins/primer/) | Context priming on session start | Any project |
| [planning](plugins/planning/) | ADRs, FDPs, Action Plans, Reports, Roadmap | Structured planning |
| [expert-agents](plugins/expert-agents/) | Klaus, Librodotus, Shawn + build/test/arch/size agents | Code audits, CI tasks |
| [backlog](plugins/backlog/) | Lightweight project backlogs for ideas and polish items | Task tracking |

## Quick Start

```bash
# Add the vibe-hacker directory as a marketplace
/plugin marketplace add /path/to/vibe-hacker

# Install individual plugins
/plugin install greenfield-mode@vibe-hacker
/plugin install primer@vibe-hacker
/plugin install planning@vibe-hacker
/plugin install expert-agents@vibe-hacker
/plugin install backlog@vibe-hacker
```

## Plugin Overview

### greenfield-mode

Prevents backwards-compatibility cruft in prototype projects.

**Hooks:**
- PostToolUse: Detect legacy patterns in edited files
- Stop: Greenfield reminder

**Config:** `greenfield_mode`, `greenfield_strict`, `greenfield_patterns`

[Full documentation](plugins/greenfield-mode/README.md)

### primer

Context priming - automatically load project files on session start.

**Hooks:**
- SessionStart: Load configured files
- After Compact: Reload files

**Config:** `priming.files`, `priming.globs`, `priming.instructions`

[Full documentation](plugins/primer/README.md)

### planning

Structured planning documents with protected paths.

**Features:**
- ADRs, FDPs, Action Plans, Reports, Roadmap
- YAML frontmatter for structured metadata
- Append-only addenda for locked documents
- Document relationships (supersedes, related)
- Protected path enforcement (readonly/guided/remind tiers)

**Hooks:**
- PreCompact: Roadmap update reminder
- PreToolUse: Protected paths check

**Config:** `planning`, `protected_paths`

[Full documentation](plugins/planning/README.md)

### expert-agents

Domain-specific code auditors with unique personalities.

**Commands:**
- `/klaus` - Embedded systems auditor
- `/librodotus` - Documentation quality auditor
- `/shawn` - Educational mentor

**Config:** None (stateless)

[Full documentation](plugins/expert-agents/README.md)

## Shared Configuration

All plugins read from `.claude/vibe-hacker.json`:

```json
{
  "greenfield_mode": true,
  "greenfield_strict": false,
  "greenfield_patterns": ["deprecated", "legacy", "@deprecated"],
  "priming": {
    "files": ["README.md"],
    "globs": ["docs/planning/action-plans/*.md"],
    "instructions": "Focus on active work."
  },
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
      {"pattern": "docs/planning/*/archive/**", "tier": "readonly"}
    ]
  }
}
```

Each plugin reads only its relevant keys:
- `greenfield-mode` reads: `greenfield_mode`, `greenfield_strict`, `greenfield_patterns`
- `primer` reads: `priming`, `greenfield_mode` (for display)
- `planning` reads: `planning`, `protected_paths`
- `expert-agents` reads: `agents` (build_verifier, test_runner, etc.)
- `backlog` reads: `backlog` (root directory)

## Repository Structure

```
vibe-hacker/
├── plugins/
│   ├── greenfield-mode/      # Cruft prevention
│   ├── primer/               # Context priming
│   ├── planning/             # Planning documents
│   ├── expert-agents/        # Code auditors
│   └── backlog/              # Project backlogs
├── docs/
│   └── planning/             # This project's planning docs
├── templates/
└── README.md
```

## Requirements

- [jq](https://jqlang.github.io/jq/) - JSON processor (greenfield-mode, primer, planning)
- Python 3.x - Planning scripts (planning only)

## License

MIT

## Author

Michael Skiles (michael@soundbytelabs.net)

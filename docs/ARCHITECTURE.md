# Architecture

This document describes the architecture of the Vibe Hacker plugin collection for Claude Code.

## Overview

Vibe Hacker is a collection of six independent Claude Code plugins that share a single configuration file (`.claude/vibe-hacker.json`). Each plugin is self-contained with its own hooks, scripts, skills, and agents.

| Plugin | Purpose |
|--------|---------|
| **greenfield-mode** | Prevent backwards-compatibility cruft in prototype projects |
| **primer** | Automatically load project context on session start |
| **planning** | Manage ADRs, FDPs, Action Plans, Reports with lifecycle and protection |
| **expert-agents** | Domain-specific auditors (Klaus, Librodotus, Shawn) + build/test/arch/size agents |
| **backlog** | Lightweight task tracking for ideas and polish items |
| **briefcase** | Personal thought management with capture, briefing, and tidy |

## Plugin Structure

Each plugin follows the same layout:

```
plugins/<name>/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest (name, version, hooks/skills refs)
├── hooks/
│   └── hooks.json           # Hook configuration (optional)
├── scripts/                 # Shell/Python scripts for hooks (optional)
├── commands/                # Slash command definitions (optional)
├── agents/                  # Agent definitions (optional)
├── skills/                  # Skill definitions (optional)
├── templates/               # Config examples (optional)
└── README.md
```

Plugins are installed independently — you can pick just the ones you need:

```bash
/plugin marketplace add /path/to/vibe-hacker
/plugin install primer@vibe-hacker        # Just context priming
/plugin install planning@vibe-hacker      # Just planning documents
```

## Shared Configuration

All plugins read from a single file: `.claude/vibe-hacker.json` in your project root.

Each plugin reads only its relevant keys:

| Plugin | Config Keys |
|--------|-------------|
| greenfield-mode | `greenfield_mode`, `greenfield_strict`, `greenfield_patterns` |
| primer | `priming` (files, globs, repos, instructions, focuses), `greenfield_mode` |
| planning | `planning` (version, subdirs), `protected_paths` (rules) |
| expert-agents | `agents` (setup, build_verifier, test_runner, arch_auditor, size_tracker) |
| backlog | `backlog` (root directory) |
| briefcase | `briefcase` (root directory) |

## Hook System

Plugins use Claude Code hooks to inject behavior at specific lifecycle points:

```
Session Start ──► primer/prime.sh            Load project context
                  greenfield-mode/session-start.sh   Show greenfield status

Pre-Compact  ──► planning/precompact-roadmap.sh     Remind to update roadmap

Pre-ToolUse  ──► planning/check-protected-paths.sh  Enforce file access tiers

Post-ToolUse ──► greenfield-mode/check-cruft.sh     Detect cruft in edited files

Stop         ──► greenfield-mode/stop-hook.sh       Greenfield review
```

### Hook Output Patterns

Hooks communicate back to Claude Code using specific output patterns:

| Pattern | Effect |
|---------|--------|
| `hookSpecificOutput.additionalContext` | Inject context into Claude's awareness |
| `hookSpecificOutput.permissionDecision` | Allow or deny a tool use |
| `systemMessage` | Display a system message |

## Data Flow

### Session Start
```
SessionStart
    │
    ├── primer/prime.sh
    │   ├── Read .claude/vibe-hacker.json
    │   ├── Load configured files, globs, repos
    │   └── Output contents as additionalContext
    │
    └── greenfield-mode/session-start.sh
        └── Output greenfield reminder if enabled
```

### Code Editing
```
Claude uses Edit/Write tool
    │
    ▼
PreToolUse ──► planning/check-protected-paths.sh
    │
    ├── readonly:  Block (permissionDecision: deny)
    ├── guided:    Block + suggest skill
    ├── remind:    Warn + allow
    └── no match:  Allow
    │
    ▼ (if allowed)
PostToolUse ──► greenfield-mode/check-cruft.sh
    │
    └── Warn if cruft patterns found in edited file
```

## Skills

Skills are interactive capabilities invoked via slash commands:

| Skill | Plugin | Invocation |
|-------|--------|------------|
| Librarian | librarian | `/librarian new fdp "Title"`, `/librarian list` |
| Backlog | backlog | `/backlog add davis "item"`, `/backlog review davis` |
| Briefcase | briefcase | `/briefcase "thought"`, `/briefcase brief` |

Skills use Python scripts for file operations and rely on Claude for analysis tasks (review, brief, tidy, chat).

## Agents

Agents are specialized Claude instances spawned for specific tasks:

| Agent | Plugin | Model | Purpose |
|-------|--------|-------|---------|
| Klaus | expert-agents | Sonnet | Embedded quality audit |
| Librodotus | expert-agents | Sonnet | Documentation audit |
| Shawn | expert-agents | Sonnet | Educational review |
| Brainstorm | expert-agents | Opus | Interactive idea distillery |
| Build Verifier | expert-agents | Haiku | Build all targets |
| Test Runner | expert-agents | Sonnet | Run tests, diagnose failures |
| Arch Auditor | expert-agents | Sonnet | Layer boundary verification |
| Size Tracker | expert-agents | Haiku | Binary size comparison |
| Cruft Auditor | greenfield-mode | Sonnet | Greenfield cruft scan |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CLAUDE_PLUGIN_ROOT` | Path to the specific plugin directory |
| `CLAUDE_PROJECT_DIR` | Path to the project using the plugin |

## Extending

### Adding a new plugin

1. Create a directory under `plugins/`
2. Add `.claude-plugin/plugin.json` with name, version, description
3. Add hooks, skills, agents, or commands as needed
4. Register in `.claude-plugin/marketplace.json` at the repo root
5. Add a README.md

### Adding a hook to an existing plugin

1. Add configuration to the plugin's `hooks/hooks.json`
2. Create the script in the plugin's `scripts/`

### Adding an agent

1. Create a markdown file in the plugin's `agents/` directory
2. Optionally add a matching command in `commands/` for slash-command access

## Design Decisions

See `docs/planning/decision-records/` for architectural decisions:

- **001** - Greenfield mode (why and how)
- **002** - Context priming (session start loading)
- **003** - Script language choice (shell for hooks, Python for complex logic)

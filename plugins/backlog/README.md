# Backlog

A Claude Code plugin for lightweight project backlogs — capturing ideas, polish items, and small improvements.

## What It Does

Backlogs sit between "stray thought" and "formal planning document." Use them to track things too informal for an FDP or Action Plan but worth remembering.

Each backlog is a named list (e.g., `davis`, `sbl-core`) with prioritized items that can be added, completed, dropped, or reviewed.

## Installation

```bash
/plugin marketplace add /path/to/vibe-hacker
/plugin install backlog@vibe-hacker
```

## Usage

```bash
/backlog create davis "Davis voice polish ideas"
/backlog add davis "Add velocity sensitivity" --priority high
/backlog add davis "LED feedback for CC page" --priority low
/backlog davis                    # List items
/backlog done davis 3             # Mark item 3 done
/backlog drop davis 5 "Not needed"
/backlog review davis             # Analyze and prioritize
```

## Commands

| Command | Description |
|---------|-------------|
| `/backlog create <name> "<desc>"` | Create a new backlog |
| `/backlog add <name> "<item>"` | Add an item (optional `--priority high\|med\|low`) |
| `/backlog <name>` or `/backlog list <name>` | List items |
| `/backlog list` | List all backlogs |
| `/backlog done <name> <id>` | Mark item complete |
| `/backlog drop <name> <id>` | Drop an item |
| `/backlog reopen <name> <id>` | Reopen a closed item |
| `/backlog review <name>` | Analyze priorities and suggest next actions |

## Configuration

```json
{
  "backlog": {
    "root": "docs/backlogs"
  }
}
```

Default root: `docs/backlogs/`

## Part of Vibe Hacker

This plugin is part of the [vibe-hacker](https://github.com/mjrskiles/vibe-hacker) plugin collection:

- **greenfield-mode** - Cruft prevention for prototypes
- **primer** - Context priming
- **planning** - ADRs, FDPs, Action Plans, Reports, Roadmap
- **expert-agents** - Code auditors, build/test/arch/size agents
- **backlog** (this plugin) - Lightweight project backlogs
- **briefcase** - Personal thought management

## License

MIT

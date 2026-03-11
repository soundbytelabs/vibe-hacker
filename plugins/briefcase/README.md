# Briefcase

A Claude Code plugin for personal thought management — capture stray ideas, brief on topics, reorganize accumulated thinking.

## What It Does

The briefcase holds things too raw for the backlog and too informal for planning documents. Threads you're pulling on, questions you're chewing on, intuitions that haven't solidified yet.

Claude acts as your "body man" — maintaining the briefcase, triaging new thoughts into the right topic, and synthesizing briefings when you need to recall your own thinking.

## Installation

```bash
/plugin marketplace add /path/to/vibe-hacker
/plugin install briefcase@vibe-hacker
```

## Usage

```bash
/briefcase "Should we narrow platform scope?"     # Quick capture
/briefcase brief                                   # Briefing on all topics
/briefcase brief library-vision                    # Briefing on one topic
/briefcase chat library-vision                     # Conversational exploration
/briefcase tidy                                    # Reorganize suggestions
```

## Commands

| Command | Description |
|---------|-------------|
| `/briefcase "<thought>"` | Capture a thought (auto-triaged to a topic) |
| `/briefcase brief [topic]` | Synthesized briefing (shorter than source material) |
| `/briefcase chat <topic>` | Conversational exploration of a topic |
| `/briefcase list` | List all topics |
| `/briefcase create <topic> "<desc>"` | Create a new topic |
| `/briefcase archive <topic>` | Archive a resolved topic |
| `/briefcase tidy` | Suggest merges, splits, promotions, archives |

## Configuration

```json
{
  "briefcase": {
    "root": "docs/briefcase"
  }
}
```

Default root: `docs/briefcase/`

## Part of Vibe Hacker

This plugin is part of the [vibe-hacker](https://github.com/mjrskiles/vibe-hacker) plugin collection:

- **greenfield-mode** - Cruft prevention for prototypes
- **primer** - Context priming
- **planning** - ADRs, FDPs, Action Plans, Reports, Roadmap
- **expert-agents** - Code auditors, build/test/arch/size agents
- **backlog** - Lightweight project backlogs
- **briefcase** (this plugin) - Personal thought management

## License

MIT

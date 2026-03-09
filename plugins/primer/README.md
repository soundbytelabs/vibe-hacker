# Primer

A Claude Code plugin for context priming - automatically load project files on session start.

## What It Does

- **SessionStart**: Loads configured files into context
- **After Compact**: Reloads files when context is compacted
- **/prime command**: Manual reload anytime

## Installation

```bash
/plugin marketplace add /path/to/vibe-hacker
/plugin install primer@vibe-hacker
```

## Configuration

Create `.claude/vibe-hacker.json` in your project:

```json
{
  "priming": {
    "files": ["README.md", "docs/ARCHITECTURE.md"],
    "globs": ["docs/planning/**/*.md"],
    "instructions": "Focus on the active action plan."
  }
}
```

### Options

| Setting | Type | Description |
|---------|------|-------------|
| `priming.files` | string[] | Default files to load |
| `priming.globs` | string[] | Glob patterns for multiple files |
| `priming.repos` | string[] | Repos to show git status for |
| `priming.instructions` | string | Custom text shown during priming |
| `priming.haiku` | boolean | Generate a haiku after priming (default: false) |
| `priming.focuses` | object | Named focus subsets (see below) |

### Focuses

Define named subsets of files for focused work on a specific area:

```json
{
  "priming": {
    "files": ["README.md", "docs/ARCHITECTURE.md"],
    "focuses": {
      "dsp": {
        "files": ["src/dsp/README.md", "docs/dsp-guide.md"],
        "repos": ["my-dsp-lib"],
        "globs": ["src/dsp/**/*.hpp"],
        "instructions": "Focus on the DSP pipeline."
      },
      "hw": {
        "files": ["hardware/README.md"],
        "repos": ["my-hardware"],
        "instructions": "Focus on hardware drivers."
      }
    }
  }
}
```

Usage:
- `/prime` — Load default `priming.files`
- `/prime dsp` — Load only the `dsp` focus files
- `/prime --list` — List available focuses

Each focus can define its own `files`, `globs`, `repos`, and `instructions`. When a focus is selected, it replaces the defaults — that's the point, narrower context for focused work. If a focus doesn't define `repos`, the top-level `priming.repos` are used as fallback.

### Fallback Behavior

If no config exists, primer falls back to:
1. `.claude/CLAUDE.md` (if exists)
2. `README.md` (if exists)
3. First 5 markdown files in `docs/` (last resort)

## Greenfield Mode Support

If `greenfield_mode: true` is set in config, primer displays a reminder:

```
Greenfield mode: ENABLED

REMINDER: This is a prototype project with no users.
- Delete old code, don't comment it out
- No backwards compatibility needed
- No deprecation comments
```

This works whether or not the greenfield-mode plugin is installed.

## Haiku Mode

Enable `priming.haiku: true` to have Claude write a haiku after priming:

```json
{
  "priming": {
    "haiku": true
  }
}
```

The haiku is generated based on the primed content and serves as:
- A creative summary of the project/context
- Confirmation that Claude is primed and aware

Example output after priming a synth firmware project:
```
Signals flow like streams
Through circuits, music emerges
Code becomes the song
```

## Commands

| Command | Description |
|---------|-------------|
| `/prime` | Reload default project context |
| `/prime <focus>` | Load a named focus subset |
| `/prime --list` | List available focuses |

## Requirements

- [jq](https://jqlang.github.io/jq/) - JSON processor

## Part of Vibe Hacker

This plugin is part of the [vibe-hacker](https://github.com/mjrskiles/vibe-hacker) plugin collection:

- **greenfield-mode** - Cruft prevention for prototypes
- **primer** (this plugin) - Context priming
- **planning** - ADRs, FDPs, Action Plans, Reports, Roadmap
- **expert-agents** - Klaus, Librodotus, Shawn

## License

MIT

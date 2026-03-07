# Expert Agents

A Claude Code plugin with domain-specific agents for code auditing, build verification, testing, and architecture enforcement.

## Agents

### Code Auditors

#### Klaus - Embedded Quality Auditor

Klaus is a pedantic embedded systems expert who audits your code for quality issues. Invoke him after major changes or to review unfamiliar codebases.

**Audit types:**
- `memory` - RAM, stack, globals, allocation patterns
- `timing` - ISRs, blocking calls, timeouts, real-time concerns
- `safety` - Error handling, defensive coding, robustness
- `style` - Code organization, naming, documentation
- `full` - Comprehensive audit (all of the above)

```bash
/klaus memory    # Check for memory issues
/klaus full      # Full codebase audit
```

#### Librodotus - Documentation Quality Auditor

Librodotus is a scholarly documentation purist who ensures your docs are useful, scannable, and accurate.

**Audit types:**
- `readme` - README scannability, 30-second test
- `code` - Source code comments, API documentation
- `architecture` - System docs, decision records
- `freshness` - Staleness check, outdated references
- `full` - Comprehensive audit (all of the above)

```bash
/librodotus readme    # Audit README quality
/librodotus full      # Full documentation audit
```

#### Shawn - Educational Mentor

Shawn is a warm mentor who views projects through an educator's lens.

**Review types:**
- `onboarding` - First five minutes, setup friction, initial success
- `concepts` - Clarity, progression, mental models
- `examples` - Quality, runnability, scaffolding
- `depth` - Challenge gradient, growth pathways
- `full` - Comprehensive educational review

```bash
/shawn onboarding   # How's the first experience?
/shawn full         # Full educational review
```

### Brainstorm

Interactive brainstorming partner. Interviews you about half-formed ideas through a structured process: Capture (diverge) → Explore (probe) → Distill (converge) → Prioritize (contextualize) → Output (synthesize). Explicitly discards tangents. Produces an opinionated summary with concrete next steps.

```bash
/brainstorm ladder filter     # Start with a topic
/brainstorm                   # Open-ended — "what's on your mind?"
```

**Model:** Opus (interactive, needs deep reasoning and project context)

This runs in the main conversation (not as a background subagent) since it requires back-and-forth with the user.

### Build & Test Agents

#### Build Verifier

Builds all project targets for all CMake presets. Reports pass/fail and binary sizes. Reads project-specific build commands from `vibe-hacker.json` config.

```bash
/build-verifier              # Build everything
/build-verifier hello-synth  # Build one project
```

**Model:** Haiku (mechanical task, no reasoning needed)

#### Test Runner

Runs all configured test suites and diagnoses failures. Reads suite commands from `vibe-hacker.json` or discovers tests from project structure.

```bash
/test-runner          # Run all suites
/test-runner unit     # Run matching suite
```

**Model:** Sonnet (needs reasoning to diagnose failures)

#### Architecture Auditor

Verifies layer boundary rules — no upward `#include` dependencies across architectural layers. Reads rules from `vibe-hacker.json` or derives them from architecture docs.

```bash
/arch-auditor          # Audit all layers
/arch-auditor widgets  # Audit one layer
```

**Model:** Sonnet (needs architectural understanding)

#### Size Tracker

Builds firmware targets and compares binary sizes (text/data/bss) against documented baselines. Flags regressions above a configurable threshold.

```bash
/size-tracker              # Measure all baselines
/size-tracker hello-synth  # Measure one target
```

**Model:** Haiku (mechanical task)

## Configuration

Build & test agents read project-specific config from `.claude/vibe-hacker.json` under the `agents` key:

```json
{
  "agents": {
    "setup": "source .venv/bin/activate",
    "build_verifier": {
      "hints": "16 cmake presets across examples/ and debug/",
      "commands": {
        "configure": "cmake --preset {preset} --fresh",
        "build": "cmake --build build/{preset}",
        "size": "arm-none-eabi-size build/{preset}/{name}.elf"
      }
    },
    "test_runner": {
      "suites": [
        {"name": "C++ unit tests", "cmd": "cd test/unit && cmake -B build && cmake --build build && ctest --test-dir build"},
        {"name": "Python tests", "cmd": "pytest"}
      ]
    },
    "arch_auditor": {
      "source_root": "src/mylib",
      "rules": [
        "core/ must NOT include hal/, drivers/",
        "hal/ MAY include core/ (intentional)"
      ]
    },
    "size_tracker": {
      "commands": { "size": "arm-none-eabi-size" },
      "baselines": [
        {"project": "examples/blinker", "preset": "target", "text": 1084}
      ],
      "threshold_pct": 5
    }
  }
}
```

If no config exists, agents fall back to reading `CLAUDE.md` and discovering project structure automatically.

## Installation

```bash
/plugin marketplace add /path/to/vibe-hacker
/plugin install expert-agents@vibe-hacker
```

## Commands

| Command | Description | Model |
|---------|-------------|-------|
| `/klaus [type]` | Embedded quality audit | Sonnet |
| `/librodotus [type]` | Documentation audit | Sonnet |
| `/shawn [type]` | Educational review | Sonnet |
| `/brainstorm [topic]` | Interactive idea distillery | Opus |
| `/build-verifier [filter]` | Build all targets | Haiku |
| `/test-runner [filter]` | Run all test suites | Sonnet |
| `/arch-auditor [filter]` | Check layer boundaries | Sonnet |
| `/size-tracker [filter]` | Binary size comparison | Haiku |

## Part of Vibe Hacker

This plugin is part of the [vibe-hacker](https://github.com/mjrskiles/vibe-hacker) plugin collection.

## License

MIT

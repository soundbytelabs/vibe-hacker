---
description: Build firmware targets and compare binary sizes against baselines
allowed-tools: Bash, Read, Task
argument-hint: [project-filter]
---

# Size Tracking Request

Invoke the size-tracker subagent to measure binary sizes.

**Filter requested**: $ARGUMENTS

If a filter is specified (e.g., a project name), only build and measure matching targets. Otherwise measure all configured baselines.

**Current project context:**
!cat .claude/vibe-hacker.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin).get('agents',{}).get('size_tracker',{}); print(json.dumps(d,indent=2))" 2>/dev/null || echo "No size_tracker config found"

Spawn the size-tracker agent to:
1. Read config for baselines and size commands
2. Build each target
3. Measure text/data/bss via arm-none-eabi-size (or configured command)
4. Compare against baselines and flag regressions

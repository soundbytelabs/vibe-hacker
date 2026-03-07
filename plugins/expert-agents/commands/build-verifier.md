---
description: Build all targets for all CMake presets, report failures and binary sizes
allowed-tools: Bash, Read, Task
argument-hint: [project-filter]
---

# Build Verification Request

Invoke the build-verifier subagent to build all project targets.

**Filter requested**: $ARGUMENTS

If a filter is specified (e.g., a project name or preset), only build matching targets. Otherwise build everything.

**Current project context:**
!cat .claude/vibe-hacker.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin).get('agents',{}).get('build_verifier',{}); print(json.dumps(d,indent=2))" 2>/dev/null || echo "No build_verifier config found"

Spawn the build-verifier agent to:
1. Read config for setup and build commands
2. Build each target for each preset
3. Report pass/fail and binary sizes in a table
4. Summarize any failures

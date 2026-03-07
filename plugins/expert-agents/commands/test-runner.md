---
description: Run all test suites and diagnose failures
allowed-tools: Bash, Read, Grep, Glob, Task
argument-hint: [suite-filter]
---

# Test Runner Request

Invoke the test-runner subagent to execute all test suites.

**Filter requested**: $ARGUMENTS

If a filter is specified (e.g., "unit", "python", a specific test name), only run matching suites. Otherwise run all.

**Current project context:**
!cat .claude/vibe-hacker.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin).get('agents',{}).get('test_runner',{}); print(json.dumps(d,indent=2))" 2>/dev/null || echo "No test_runner config found"

Spawn the test-runner agent to:
1. Read config for setup and test suite commands
2. Run each test suite
3. Report pass/fail with test counts
4. Diagnose any failures with file/line references

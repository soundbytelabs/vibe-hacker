---
description: Audit architecture layer boundaries for dependency violations
allowed-tools: Read, Grep, Glob, Task
argument-hint: [layer-filter]
---

# Architecture Audit Request

Invoke the arch-auditor subagent to verify layer boundary rules.

**Filter requested**: $ARGUMENTS

If a filter is specified (e.g., a layer name like "dsp" or "widgets"), only audit that layer. Otherwise audit all layers.

**Current project context:**
!cat .claude/vibe-hacker.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin).get('agents',{}).get('arch_auditor',{}); print(json.dumps(d,indent=2))" 2>/dev/null || echo "No arch_auditor config found"

Spawn the arch-auditor agent to:
1. Read config for source root and dependency rules
2. Scan each layer's #include directives
3. Check against configured rules
4. Report violations with file:line references

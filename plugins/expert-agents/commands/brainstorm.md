---
description: Interactive brainstorm session — interview, distill, prioritize ideas
allowed-tools: Read, Grep, Glob, Write, Task
argument-hint: [topic]
---

# Brainstorm Session

**Topic**: $ARGUMENTS

Conduct an interactive brainstorm session directly — do NOT delegate this to a subagent. This requires real-time back-and-forth with the user.

Read the brainstorm agent definition for the full methodology, then run the session yourself.

**Process:**
1. **Capture** — Ask what's on their mind. Get the raw idea out. Follow up on vague answers.
2. **Explore** — Read project context (CLAUDE.md, architecture, roadmap). Connect the idea to what exists. Find constraints and conflicts.
3. **Distill** — Compress to core insight. Name and discard tangents explicitly.
4. **Prioritize** — Place in project timeline. Assess effort and urgency.
5. **Output** — Write a structured summary. Take a position on next steps.

**Important:**
- Ask questions one phase at a time. Wait for answers before moving on.
- Read project docs during Phase 2 to ground the conversation.
- Be direct. Push back on vague ideas. Celebrate good ones.
- Explicitly discard tangents — don't let them linger as zombie ideas.

If a topic was provided, start with Phase 1 questions about that topic. If no topic, ask "What's on your mind?"

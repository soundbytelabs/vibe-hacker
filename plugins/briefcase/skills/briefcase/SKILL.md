---
name: briefcase
description: Personal thought management — capture stray ideas, brief on topics, reorganize accumulated thinking. Your body man for project context.
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Briefcase Skill

Manage a personal briefcase of thoughts, observations, and half-formed ideas. The briefcase holds things too raw for the backlog and too informal for planning documents — the threads you're pulling on, the questions you're chewing on, the intuitions that haven't solidified yet.

**You are a body man** — you maintain the briefcase, know what's in it, and can brief the user on their own thinking when asked. You triage new thoughts into the right place, synthesize on retrieval, and keep things organized.

## When to Use

- Quick-capturing a stray thought mid-session ("I wonder if we should narrow platform scope")
- Reviewing what you've been thinking about on a topic
- Getting a briefing on recent thoughts before diving into a decision
- Reorganizing accumulated thinking when topics have grown or merged

## Script

File operations go through the management script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/briefcase/scripts/manage.py <command> [args...]
```

## Commands

### Capture a thought

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/briefcase/scripts/manage.py add "<thought>" [--topic <topic>]
```

If `--topic` is provided, the thought is appended to that topic file. If omitted, you must triage the thought yourself:

1. Read existing topic files with `list`
2. Decide if the thought fits an existing topic or needs a new one
3. If it fits an existing topic, use `add` with `--topic`
4. If it needs a new topic, use `create` first, then `add`
5. If you're unsure, ask the user

Examples:
```bash
python3 .../manage.py add "Should we drop RP2040 support? Most energy is on M7." --topic platform-scope
python3 .../manage.py add "The README doesn't tell the DSP story well enough"
```

### Create a topic

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/briefcase/scripts/manage.py create <topic> "<description>"
```

Examples:
```bash
python3 .../manage.py create library-vision "Thoughts on SBL's direction and identity"
python3 .../manage.py create platform-scope "Should we narrow or broaden platform support?"
```

### List topics

```bash
# List all topics (summary)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/briefcase/scripts/manage.py list

# Show a specific topic's entries
python3 ${CLAUDE_PLUGIN_ROOT}/skills/briefcase/scripts/manage.py list <topic>
```

### Archive a topic

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/briefcase/scripts/manage.py archive <topic>
```

Moves a topic to `archive/` subdirectory. Use when a thought thread has been resolved (became an FDP, was discarded, or just ran its course).

### Rename a topic

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/briefcase/scripts/manage.py rename <old-topic> <new-topic>
```

## Chat

When the user asks to chat about a topic (e.g., `/briefcase chat library-vision`), enter a conversational exploration mode:

1. Read the topic file from the configured root
2. Internalize the entries — understand the arc of thinking, the tensions, the open questions
3. **Start a conversation, not a monologue.** Open with what seems most alive in the topic — the unresolved tension, the most recent thread, or the question that keeps recurring
4. Ask a probing question to pull the thread further. Your job is to help the user think, not to summarize what they already wrote down.
5. As the conversation progresses, **capture new insights back to the topic file** using the `add` script with `--topic`. Don't ask permission for every capture — use judgment. If the user says something that crystallizes a new thought, capture it.
6. If the conversation surfaces something actionable, suggest promoting it (to backlog, FDP, etc.) but don't push — the briefcase is a low-pressure zone.

**Tone:** Thoughtful collaborator, not interviewer. You have context on the project (architecture, roadmap, design philosophy) — connect dots the user might not see between their briefcase thoughts and the broader project state. Push back gently when thinking seems stuck or circular.

**End state:** The topic file should have new entries reflecting what emerged from the conversation. The user should feel like they made progress on their thinking.

## Brief

When the user asks for a briefing (e.g., `/briefcase brief` or `/briefcase brief library-vision`), do NOT use the script. Instead:

1. Read the relevant topic file(s) from the configured root (default: `docs/briefcase/`)
2. If no topic specified, read ALL active topic files
3. **Synthesize, don't regurgitate.** Your job is to:
   - Identify the recurring themes and threads across entries
   - Note how thinking has evolved over time (early entries vs recent)
   - Surface the things that seem most important based on frequency and recency
   - Flag contradictions or tensions between thoughts
   - Suggest which threads seem ripe for action (ready for an FDP, backlog item, or decision)
4. Present the briefing conversationally: "You've been thinking about X. The main thread is Y. You mentioned Z several times. The tension seems to be between A and B."

**Important:** A good brief is *shorter* than the source material. Compress, don't expand. If a topic has 15 entries, the brief should be a paragraph or two, not 15 bullet points.

## Tidy

When the user asks to tidy (e.g., `/briefcase tidy`), do NOT use the script. Instead:

1. Read ALL topic files
2. Analyze the content and suggest reorganization:
   - **Merge:** Topics that have converged (e.g., "platform-scope" and "library-vision" turned out to be the same thread)
   - **Split:** Topics that have grown to cover multiple distinct threads
   - **Promote:** Thoughts that have matured enough to become a backlog item, FDP, or ADR
   - **Archive:** Topics with no entries in the last 30 days, or where the thread has been resolved
3. Present the suggestions and ask for confirmation before making changes
4. Execute approved changes using the script commands

## Configuration

Briefcase files are stored in the directory configured in `.claude/vibe-hacker.json`:

```json
{
  "briefcase": {
    "root": "docs/briefcase"
  }
}
```

Default root: `docs/briefcase/`

## Conventions

- **Topic names** are kebab-case: `library-vision`, `platform-scope`, `dsp-priorities`
- **Entries** are timestamped under `### YYYY-MM-DD` headers within each topic file
- **Multiple entries on the same day** are appended under the same date header
- Topics are markdown files — human-readable, version-trackable, grep-friendly
- The briefcase is for *your* thoughts. Auto-memory is for Claude's learned facts. Don't merge them.

## Parsing Arguments

When the user invokes `/briefcase`, parse their intent from the arguments:

| User says | Action |
|-----------|--------|
| `/briefcase "some thought"` | Capture — triage and add the thought |
| `/briefcase add "thought" --topic foo` | Capture to specific topic |
| `/briefcase brief` | Brief on all topics |
| `/briefcase brief library-vision` | Brief on one topic |
| `/briefcase chat library-vision` | Conversational exploration of a topic |
| `/briefcase topics` or `/briefcase list` | List all topics |
| `/briefcase tidy` | Reorganize suggestions |
| `/briefcase create foo "description"` | Create a new topic |
| `/briefcase archive foo` | Archive a topic |

The most common usage is `/briefcase "thought goes here"` — make that path fast and frictionless. Read existing topics, triage, append, confirm. Don't ask unnecessary questions.

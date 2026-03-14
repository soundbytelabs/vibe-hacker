---
name: librarian
description: Manage planning documents (ADRs, FDPs, action plans, reports). Use when creating, archiving, or listing planning docs. Enforces proper numbering and structure.
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Librarian Skill

Manage planning documents with proper structure, numbering, and lifecycle.

## Document Types

| Type | Purpose | ID Format | Default Directory |
|------|---------|-----------|-------------------|
| ADR | Architecture Decision Record | `ADR-001` | `decisions/` |
| FDP | Feature Design Proposal | `FDP-001` | `designs/` |
| AP | Action Plan | `AP-001` | `action-plans/` |
| Report | Reports and analysis | `RPT-001` | `reports/` |
| Roadmap | Project goals and vision | N/A | `roadmap.md` |

## Workspace Targeting

This workspace has planning documents in multiple locations. Infer the correct `--project-dir` from conversational context.

| Location | Contents | When to use |
|----------|----------|-------------|
| `docs/planning/` (workspace root) | Cross-cutting ADRs, FDPs, APs, RPTs | Library architecture, shared infrastructure, DSP widgets |
| `sbl-apps/docs/planning/` | App-level FDPs, APs, product briefs | Davis family, app-specific designs |
| `sbl-apps/davis-jr/docs/planning/` | Product-specific reports | Davis Jr. tuning, gain staging |
| `tools/plugins/vibe-hacker/docs/planning/` | Tool ADRs, FDPs, APs | vibe-hacker plugin development |

**Heuristics:**
- Discussing a widget, atom, library feature, or cross-cutting architecture → workspace root (default)
- Discussing Davis Jr., macros, app behavior, product design → `sbl-apps/`
- Discussing vibe-hacker, planning system, plugins → `tools/plugins/vibe-hacker/`
- When ambiguous, ask the user or default to workspace root

Pass the target via `--project-dir`:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/new.py fdp "Title" --project-dir /absolute/path/to/sbl-apps
```

## Document Format (v0.2.1)

All documents have YAML frontmatter for structured metadata:

```yaml
---
type: adr
id: ADR-001
status: proposed
created: 2025-12-13
modified: 2025-12-13
supersedes: null
superseded_by: null
obsoleted_by: null
related: []
---

# ADR-001: Title Here

## Status
Proposed

...content...

---

## Addenda
```

### Frontmatter Fields

| Field | Description |
|-------|-------------|
| `type` | Document type (adr, fdp, ap, report) |
| `id` | Display ID (ADR-001, FDP-002, etc.) |
| `status` | Current lifecycle status |
| `created` | ISO date of creation |
| `modified` | ISO date of last modification |
| `supersedes` | ID of document this replaces |
| `superseded_by` | ID of document that replaced this |
| `obsoleted_by` | ID or reason for obsolescence |
| `related` | List of related document IDs |

### Addenda Section

Documents have an append-only addenda section at the bottom. This allows adding notes, clarifications, and updates to locked documents without modifying the original content.

## Configuration

Configure planning in `.claude/vibe-hacker.json`:

```json
{
  "planning": {
    "version": "0.2.1",
    "subdirs": {
      "adr": "decisions",
      "fdp": "designs",
      "ap": "action-plans",
      "report": "reports"
    }
  },
  "protected_paths": {
    "planning_root": "docs/planning"
  }
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `planning.version` | `0.1.0` | Schema version |
| `planning.subdirs.adr` | `decisions` | Subdirectory for ADRs |
| `planning.subdirs.fdp` | `designs` | Subdirectory for FDPs |
| `planning.subdirs.ap` | `action-plans` | Subdirectory for Action Plans |
| `planning.subdirs.report` | `reports` | Subdirectory for Reports |
| `protected_paths.planning_root` | `docs/planning` | Root directory for all planning docs |

## When to Use This Skill

Use the librarian scripts when:
- Creating a new planning document (ensures proper numbering and frontmatter)
- Updating a document's status (e.g., Proposed → Accepted)
- Adding an addendum to a locked document
- Creating a document that supersedes another
- Archiving a completed or superseded document
- Listing active planning documents

**Do NOT manually create or renumber planning documents.** Always use the scripts.

## Available Scripts

All scripts are in `${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/`.

### Create New Document

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/new.py <type> "<title>" [--project-dir PATH]
```

Types: `adr`, `fdp`, `ap`, `report`

Examples:
```bash
python3 scripts/new.py adr "Use PostgreSQL for persistence"
python3 scripts/new.py fdp "User Authentication System"
python3 scripts/new.py ap "Implement login flow"
python3 scripts/new.py report "Q4 Performance Analysis"
python3 scripts/new.py fdp "Davis Mixer" --project-dir /path/to/sbl-apps
```

### Add Addendum

Add notes or updates to any document, even locked ones:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/append.py <doc-id> "<title>" [--body "<content>"]
```

Examples:
```bash
python3 scripts/append.py ADR-001 "Performance Clarification"
python3 scripts/append.py ADR-001 "Migration note" --body "Use pg_dump for best results"
```

### Supersede Document

Create a new document that supersedes an existing one:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/supersede.py <old-doc-id> "<new-title>"
```

This will:
1. Create a new document of the same type
2. Link the new document to the old (supersedes field)
3. Update the old document (superseded_by field, status)
4. Add an addendum to the old document

Example:
```bash
python3 scripts/supersede.py ADR-001 "Revised Database Strategy"
```

### Add Related Links

Link documents together:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/relate.py <doc-id> <related-ids...> [--bidirectional]
```

Examples:
```bash
python3 scripts/relate.py ADR-001 FDP-003
python3 scripts/relate.py ADR-001 FDP-003 ADR-002 --bidirectional
```

### Update Status

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/update-status.py <doc-id> <new-status>
```

Examples:
```bash
python3 scripts/update-status.py ADR-001 accepted
python3 scripts/update-status.py FDP-002 "in progress"
python3 scripts/update-status.py RPT-001 published
```

Valid statuses by type:
- **ADR**: proposed, accepted, deprecated, superseded
- **FDP**: proposed, in progress, implemented, abandoned
- **AP**: active, completed, abandoned
- **Report**: draft, published, superseded, obsoleted

### Archive Document

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/archive.py <doc-id> [--project-dir PATH]
```

Archiving moves the document to `archive/` and generates an `ARCHIVE.md` index in the type directory listing all archived documents.

Examples:
```bash
python3 scripts/archive.py ADR-001
python3 scripts/archive.py FDP-002
```

To rebuild the archive index without archiving a document:
```bash
python3 scripts/archive.py --regenerate-index [--type TYPE] [--project-dir PATH]
```

### Check Edit Permission

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/edit.py <doc-id> [--force] [--quiet]
```

Checks if a document can be edited based on its status. Outputs the file path if editable.

**Locked statuses** (require `--force` to edit):
- **ADR**: accepted, deprecated, superseded
- **FDP**: implemented, abandoned
- **AP**: completed, abandoned
- **Report**: published, superseded, obsoleted

**Tip**: Use `append.py` to add an addendum instead of force-editing locked documents.

### Review Open Documents

Show all planning documents not in a terminal state, with brief summaries. Use this to audit what's still open and decide what to archive, advance, or abandon.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/review.py [--type TYPE] [--project-dir PATH]
```

Examples:
```bash
python3 scripts/review.py                     # Review all open documents
python3 scripts/review.py --type fdp          # Review open FDPs only
python3 scripts/review.py --project-dir /path/to/sbl-apps  # Review app-level plans
```

Terminal statuses (excluded from review):
- **ADR**: accepted, deprecated, superseded
- **FDP**: implemented, abandoned
- **AP**: completed, abandoned
- **Report**: published, superseded, obsoleted

Documents with non-standard statuses (e.g., "Complete" instead of "Implemented") will show up — that's intentional, as it surfaces docs that need status cleanup.

### List Documents

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/list.py [--type TYPE] [--status STATUS] [--include-archived]
```

Examples:
```bash
python3 scripts/list.py
python3 scripts/list.py --type adr
python3 scripts/list.py --type report
python3 scripts/list.py --status proposed
python3 scripts/list.py --include-archived
```

### Migration (vibe-doc)

Upgrade existing documents to the latest format:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/vibe-doc.py status
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/vibe-doc.py upgrade --dry-run
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/vibe-doc.py upgrade
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/vibe-doc.py changelog 0.2.0
```

## Document Lifecycle

### ADR Lifecycle
```
Proposed → Accepted → [Superseded | Deprecated]
```

- **Proposed**: Under discussion, can be edited
- **Accepted**: Decision made, becomes read-only (use addenda for updates)
- **Superseded**: Replaced by newer ADR, archived
- **Deprecated**: No longer applicable, archived

### FDP Lifecycle
```
Proposed → In Progress → [Implemented | Abandoned]
```

- **Proposed**: Design under review
- **In Progress**: Actively being implemented
- **Implemented**: Complete, archived
- **Abandoned**: Not pursued, archived

### Action Plan Lifecycle
```
Active → [Completed | Abandoned]
```

- **Active**: Work in progress
- **Completed**: All tasks done, archived
- **Abandoned**: Work stopped, archived

### Report Lifecycle
```
Draft → Published → [Superseded | Obsoleted]
```

- **Draft**: Being written, can be edited
- **Published**: Final, read-only (use addenda for updates)
- **Superseded**: Replaced by newer report
- **Obsoleted**: No longer relevant

## Roadmap

The roadmap is a single markdown file tracking project goals at different time horizons:

- **Immediate** (This Week) - Current focus
- **Medium Term** (This Month) - Coming up next
- **Long Term** (This Quarter+) - Vision and direction
- **Recently Completed** - What was just finished

### Initialize Roadmap

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/librarian/scripts/init-roadmap.py
```

A **PreCompact hook** reminds you to update the roadmap before context compaction.

## Protected Paths

Planning documents are configured with protection rules:

- **Archived documents** (`readonly` tier): Cannot be edited
- **Active planning documents** (`remind` tier): Editable with a warning suggesting skill scripts

The `edit.py` script provides additional validation based on document status.

## Templates

Templates are in `${CLAUDE_PLUGIN_ROOT}/skills/librarian/templates/`:
- `adr.md` - Architecture Decision Record
- `fdp.md` - Feature Design Proposal
- `action-plan.md` - Action Plan
- `report.md` - Report
- `roadmap.md` - Project Roadmap

All templates include frontmatter and an addenda section.

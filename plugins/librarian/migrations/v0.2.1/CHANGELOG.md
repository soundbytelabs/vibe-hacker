# Planning v0.2.1 Changelog

## Overview

This release adds structured frontmatter to all planning documents, enabling:
- Machine-parseable metadata
- Document relationships (supersedes, related)
- Append-only addenda for locked documents
- Extensible document types via configuration

## Breaking Changes

- All planning documents now require YAML frontmatter
- New default directory names: `decisions`, `designs`, `action-plans`, `reports`
- Existing projects should add `planning.subdirs` config to map to their directory names

## New Features

### Frontmatter
All documents now have YAML frontmatter with:
- `type`, `id`, `status` - Document identification
- `created`, `modified` - Date tracking
- `supersedes`, `superseded_by`, `obsoleted_by` - Document relationships
- `related` - Links to related documents

### Addenda Section
Documents can have an append-only addenda section at the bottom.
This allows adding notes, clarifications, and updates to locked documents
without modifying the original content.

### New Document Type: Reports
- ID format: `RPT-001`
- Directory: `reports/`
- Lifecycle: Draft → Published → Superseded/Obsoleted

### New Scripts
- `append.py` - Add addenda to any document
- `supersede.py` - Create a document that supersedes another
- `relate.py` - Add related document links

### Configurable Directories
Directory names are configurable via `planning.subdirs` in config, allowing
projects to use their preferred naming conventions.

## Migration

Run `vibe-doc upgrade` to migrate existing documents:
1. Adds frontmatter to all existing documents
2. Updates configuration to v0.2.0 format
3. Adds empty addenda sections to all documents

The migration preserves all existing content.

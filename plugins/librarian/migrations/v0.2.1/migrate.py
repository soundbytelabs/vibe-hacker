#!/usr/bin/env python3
"""
Migration to v0.2.1

Adds frontmatter to all planning documents and updates configuration.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path


def get_project_dir() -> Path:
    """Get the project directory."""
    return Path(os.environ.get('CLAUDE_PROJECT_DIR', '.'))


def get_config_path(project_dir: Path) -> Path:
    """Get path to vibe-hacker.json config file."""
    return project_dir / '.claude' / 'vibe-hacker.json'


def load_config(project_dir: Path) -> dict:
    """Load configuration from vibe-hacker.json."""
    config_path = get_config_path(project_dir)
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(project_dir: Path, config: dict) -> None:
    """Save configuration to vibe-hacker.json."""
    config_path = get_config_path(project_dir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + '\n')


def get_planning_root(config: dict) -> str:
    """Get planning root from config."""
    root = config.get('protected_paths', {}).get('planning_root')
    if root:
        return root
    root = config.get('planning', {}).get('root')
    if root:
        return root
    return 'docs/planning'


def check_applicable(project_dir: Path) -> bool:
    """Check if this migration should run."""
    config = load_config(project_dir)
    version = config.get('planning', {}).get('version', '0.1.0')
    return version < '0.2.0'


def infer_doc_type(filepath: Path, planning_root: Path) -> str | None:
    """Infer document type from file path and name."""
    rel_path = filepath.relative_to(planning_root)
    parts = rel_path.parts

    # Check directory name
    if len(parts) >= 1:
        dir_name = parts[0]
        if dir_name in ('archive',):
            dir_name = parts[1] if len(parts) > 1 else ''

        dir_mappings = {
            'decision-records': 'adr',
            'decisions': 'adr',
            'feature-designs': 'fdp',
            'designs': 'fdp',
            'action-plans': 'ap',
            'reports': 'report',
        }
        if dir_name in dir_mappings:
            return dir_mappings[dir_name]

    # Check filename prefix
    filename = filepath.name
    if filename.startswith('FDP-'):
        return 'fdp'
    elif filename.startswith('AP-'):
        return 'ap'
    elif filename.startswith('RPT-'):
        return 'report'
    elif re.match(r'^\d+-', filename):
        return 'adr'

    return None


def extract_doc_id(filepath: Path, doc_type: str) -> str | None:
    """Extract document ID from filename."""
    filename = filepath.name

    patterns = {
        'adr': (r'^(\d+)-', 'ADR-{:03d}'),
        'fdp': (r'^FDP-(\d+)-', 'FDP-{:03d}'),
        'ap': (r'^AP-(\d+)-', 'AP-{:03d}'),
        'report': (r'^RPT-(\d+)-', 'RPT-{:03d}'),
    }

    if doc_type not in patterns:
        return None

    pattern, format_str = patterns[doc_type]
    match = re.match(pattern, filename)
    if match:
        number = int(match.group(1))
        return format_str.format(number)

    return None


def extract_status_from_content(content: str) -> str:
    """Extract status from ## Status section."""
    match = re.search(r'^## Status\s*\n\s*\n?([^\n#]+)', content, re.MULTILINE)
    if match:
        return match.group(1).strip().lower()
    return 'proposed'


def extract_date_from_content(content: str) -> str | None:
    """Extract date from ## Date or ## Created section."""
    match = re.search(r'^## (?:Date|Created)\s*\n\s*\n?(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def has_frontmatter(content: str) -> bool:
    """Check if content already has frontmatter."""
    return content.startswith('---\n')


def create_frontmatter(doc_type: str, doc_id: str, status: str, created: str) -> str:
    """Create YAML frontmatter string."""
    today = datetime.now().strftime('%Y-%m-%d')
    return f"""---
type: {doc_type}
id: {doc_id}
status: {status}
created: {created}
modified: {today}
supersedes: null
superseded_by: null
obsoleted_by: null
related: []
---

"""


def migrate_document(filepath: Path, planning_root: Path) -> dict:
    """
    Migrate a single document to v0.2.1 format.

    Returns dict with migration details.
    """
    content = filepath.read_text()
    result = {
        'path': str(filepath),
        'status': 'skipped',
        'reason': None,
    }

    # Skip if already has frontmatter
    if has_frontmatter(content):
        result['reason'] = 'already has frontmatter'
        return result

    # Infer document type
    doc_type = infer_doc_type(filepath, planning_root)
    if not doc_type:
        result['reason'] = 'could not determine document type'
        return result

    # Extract document ID
    doc_id = extract_doc_id(filepath, doc_type)
    if not doc_id:
        result['reason'] = 'could not extract document ID'
        return result

    # Extract metadata from content
    status = extract_status_from_content(content)
    created = extract_date_from_content(content) or datetime.now().strftime('%Y-%m-%d')

    # Create frontmatter
    frontmatter = create_frontmatter(doc_type, doc_id, status, created)

    # Add addenda section if not present
    if '\n## Addenda' not in content and '\n## Addenda\n' not in content:
        content = content.rstrip() + '\n\n---\n\n## Addenda\n'

    # Combine frontmatter and content
    new_content = frontmatter + content

    # Write back
    filepath.write_text(new_content)

    result['status'] = 'migrated'
    result['doc_type'] = doc_type
    result['doc_id'] = doc_id
    return result


def find_planning_docs(planning_root: Path) -> list[Path]:
    """Find all markdown files in planning directories."""
    docs = []

    if not planning_root.exists():
        return docs

    # Search all subdirectories
    for md_file in planning_root.rglob('*.md'):
        # Skip templates and roadmap
        if md_file.name == 'template.md':
            continue
        if md_file.name == 'roadmap.md':
            continue
        docs.append(md_file)

    return sorted(docs)


def dry_run(project_dir: Path) -> list[str]:
    """Return list of changes that would be made."""
    changes = []
    config = load_config(project_dir)
    planning_root = project_dir / get_planning_root(config)

    # Config changes
    version = config.get('planning', {}).get('version', '0.1.0')
    if version < '0.2.1':
        changes.append("Update config: planning.version -> 0.2.0")

    # Document changes
    docs = find_planning_docs(planning_root)
    for doc in docs:
        content = doc.read_text()
        if not has_frontmatter(content):
            doc_type = infer_doc_type(doc, planning_root)
            doc_id = extract_doc_id(doc, doc_type) if doc_type else None
            if doc_type and doc_id:
                changes.append(f"Add frontmatter: {doc_id} ({doc.name})")
            else:
                changes.append(f"Skip (unknown type): {doc.name}")

    return changes


def migrate(project_dir: Path) -> bool:
    """Perform the migration. Return True on success."""
    config = load_config(project_dir)
    planning_root = project_dir / get_planning_root(config)

    print(f"Migrating planning documents in: {planning_root}")

    # Migrate documents
    docs = find_planning_docs(planning_root)
    migrated = 0
    skipped = 0
    errors = []

    for doc in docs:
        try:
            result = migrate_document(doc, planning_root)
            if result['status'] == 'migrated':
                print(f"  Migrated: {result.get('doc_id', doc.name)}")
                migrated += 1
            else:
                print(f"  Skipped: {doc.name} ({result.get('reason', 'unknown')})")
                skipped += 1
        except Exception as e:
            errors.append(f"{doc.name}: {e}")

    # Update config version
    if 'planning' not in config:
        config['planning'] = {}
    config['planning']['version'] = '0.2.1'
    save_config(project_dir, config)

    print(f"\nMigration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped: {skipped}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for err in errors:
            print(f"    - {err}")

    return len(errors) == 0


def rollback(project_dir: Path) -> bool:
    """
    Rollback is not supported for this migration.

    The migration adds content (frontmatter) but doesn't remove anything.
    Manual cleanup would be required to rollback.
    """
    print("Rollback not supported for v0.2.1 migration.")
    print("Manual removal of frontmatter would be required.")
    return False


if __name__ == '__main__':
    import sys

    project_dir = get_project_dir()

    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        changes = dry_run(project_dir)
        if changes:
            print("Changes that would be made:")
            for change in changes:
                print(f"  - {change}")
        else:
            print("No changes needed.")
    else:
        if check_applicable(project_dir):
            success = migrate(project_dir)
            sys.exit(0 if success else 1)
        else:
            print("Migration not applicable (already at v0.2.1 or higher)")

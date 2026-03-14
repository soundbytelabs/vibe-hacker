#!/usr/bin/env python3
"""
Archive a planning document.

Usage:
    archive.py <doc-id>
    archive.py --regenerate-index [--type TYPE] [--project-dir PATH]

Examples:
    archive.py ADR-001
    archive.py FDP-002
    archive.py AP-003
    archive.py RPT-001
    archive.py --regenerate-index              # rebuild all archive indexes
    archive.py --regenerate-index --type fdp   # rebuild just feature-designs

This will:
    1. Update the document's status to "archived" in frontmatter and body
    2. Add an "Archived" date to the body
    3. Move the file to the archive/ subdirectory
    4. Generate/update ARCHIVE.md index in the type directory
"""

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from config import (
    get_project_dir,
    get_planning_root,
    get_type_config,
    get_all_types,
)
from frontmatter import parse_frontmatter, render_frontmatter


def parse_doc_id(doc_id: str) -> tuple[str, int]:
    """
    Parse a document ID into type and number.

    Args:
        doc_id: Document ID like 'ADR-001', 'FDP-002', 'AP-001', 'RPT-001'

    Returns:
        Tuple of (doc_type, number)

    Raises:
        ValueError: If ID format is not recognized
    """
    doc_id = doc_id.upper()

    patterns = [
        (r'^ADR-(\d+)$', 'adr'),
        (r'^FDP-(\d+)$', 'fdp'),
        (r'^AP-(\d+)$', 'ap'),
        (r'^RPT-(\d+)$', 'report'),
    ]

    for pattern, doc_type in patterns:
        match = re.match(pattern, doc_id)
        if match:
            return doc_type, int(match.group(1))

    raise ValueError(f"Invalid document ID: {doc_id}. Expected format: ADR-001, FDP-002, AP-003, or RPT-001")


def find_document(doc_type: str, number: int, project_dir: Path) -> Path | None:
    """Find a document by type and number (not in archive)."""
    type_config = get_type_config(doc_type)
    planning_root = project_dir / get_planning_root()
    doc_dir = planning_root / type_config['dir']

    if not doc_dir.exists():
        return None

    # Build pattern based on type config
    prefix = type_config.get('prefix', '')
    if prefix:
        pattern = re.compile(rf'^{re.escape(prefix)}(\d+)-.*\.md$')
    else:
        pattern = re.compile(r'^(\d+)-.*\.md$')

    for f in doc_dir.iterdir():
        if f.is_file():
            match = pattern.match(f.name)
            if match and int(match.group(1)) == number:
                return f

    return None


def update_status_in_content(content: str, new_status: str = "Archived") -> str:
    """Update status in both frontmatter and body."""
    today = date.today().isoformat()

    # Parse frontmatter
    frontmatter, body = parse_frontmatter(content)

    # Update frontmatter if present
    if frontmatter:
        frontmatter['status'] = new_status.lower()
        frontmatter['modified'] = today
        content = render_frontmatter(frontmatter) + body

    # Update body status section
    status_pattern = r'(## Status\s*\n\s*\n?)([^\n#]+)'

    def replace_status(match):
        prefix = match.group(1)
        return f"{prefix}{new_status}"

    content, count = re.subn(status_pattern, replace_status, content)

    # Add Archived date section if not present
    if '## Archived' not in content:
        archived_section = f"\n## Archived\n\n{today}\n"

        # Find position after Status section
        status_match = re.search(r'## Status\s*\n\s*\n?[^\n#]+\n', content)
        if status_match:
            insert_pos = status_match.end()
            content = content[:insert_pos] + archived_section + content[insert_pos:]

    return content


def regenerate_archive_index(type_dir: Path, doc_type: str) -> Path | None:
    """
    Regenerate ARCHIVE.md index from the archive/ subdirectory.

    Scans all .md files in archive/, reads their frontmatter, and writes
    a sorted index table to ARCHIVE.md in the parent type directory.

    Args:
        type_dir: The type directory (e.g., docs/planning/feature-designs/)
        doc_type: Document type key (adr, fdp, ap, report)

    Returns:
        Path to ARCHIVE.md, or None if no archive directory exists
    """
    archive_dir = type_dir / 'archive'
    if not archive_dir.exists():
        return None

    type_config = get_type_config(doc_type)
    type_name = type_config.get('name', doc_type.upper())
    id_format = type_config.get('id_format', '{number:03d}')
    prefix = type_config.get('prefix', '')

    # Build filename patterns — primary (current convention) + fallback (old conventions)
    patterns = []
    if prefix:
        patterns.append(re.compile(rf'^{re.escape(prefix)}(\d+)-.*\.md$'))
    else:
        patterns.append(re.compile(r'^(\d+)-.*\.md$'))
    # Fallback: match any ID-like prefix (e.g., ADR-0001-...) for old naming conventions
    id_prefix = id_format.split('-')[0] if '-' in id_format.split('{')[0] else ''
    if id_prefix:
        patterns.append(re.compile(rf'^{re.escape(id_prefix)}-(\d+)-.*\.md$'))

    # Collect archived document info
    entries = []
    for f in sorted(archive_dir.iterdir()):
        if not f.is_file() or not f.name.endswith('.md'):
            continue

        number = None
        for pat in patterns:
            match = pat.match(f.name)
            if match:
                number = int(match.group(1))
                break
        if number is None:
            continue
        doc_id = id_format.format(number=number)

        # Read frontmatter for metadata
        try:
            content = f.read_text()
            frontmatter, body = parse_frontmatter(content)
        except Exception:
            frontmatter = None
            body = content if 'content' in dir() else ''

        # Extract title from body (first H1), strip any ID prefix like "ADR-001:" or "ADR-0001 —"
        title = ''
        title_match = re.search(r'^#\s+(.+)$', body or content, re.MULTILINE)
        if title_match:
            raw = title_match.group(1).strip()
            # Strip ID prefix patterns: "ADR-001: ", "FDP-0001 — ", "AP-002 - ", etc.
            title = re.sub(r'^[A-Z]+-\d+\s*[:\u2014\-]+\s*', '', raw).strip() or raw
        elif frontmatter and 'id' in frontmatter:
            title = f.stem

        # Extract status and archived date from frontmatter
        status = ''
        archived_date = ''
        if frontmatter:
            status = str(frontmatter.get('status', '')).title()
            archived_date = str(frontmatter.get('modified', ''))

        # Relative path from type_dir to archive file
        rel_path = f'archive/{f.name}'

        entries.append({
            'number': number,
            'id': doc_id,
            'title': title,
            'status': status,
            'archived': archived_date,
            'rel_path': rel_path,
        })

    if not entries:
        # Remove stale index if archive is empty
        index_path = type_dir / 'ARCHIVE.md'
        if index_path.exists():
            index_path.unlink()
        return None

    # Sort by number
    entries.sort(key=lambda e: e['number'])

    # Build ARCHIVE.md
    lines = [
        f'# Archived {type_name}s',
        '',
        f'| ID | Title | Status | Archived | Path |',
        f'|----|-------|--------|----------|------|',
    ]

    for e in entries:
        link = f"[{e['rel_path']}]({e['rel_path']})"
        lines.append(f"| {e['id']} | {e['title']} | {e['status']} | {e['archived']} | {link} |")

    lines.append('')  # trailing newline

    index_path = type_dir / 'ARCHIVE.md'
    index_path.write_text('\n'.join(lines))

    return index_path


def archive_document(doc_id: str, project_dir: Path) -> Path:
    """Archive a planning document and regenerate the archive index."""
    doc_type, number = parse_doc_id(doc_id)

    # Find the document
    filepath = find_document(doc_type, number, project_dir)
    if not filepath:
        raise FileNotFoundError(f"Document not found: {doc_id}")

    # Check if already archived
    if 'archive' in filepath.parts:
        raise ValueError(f"Document is already archived: {filepath}")

    # Update status
    content = filepath.read_text()
    new_content = update_status_in_content(content)
    filepath.write_text(new_content)

    # Create archive directory
    type_dir = filepath.parent
    archive_dir = type_dir / 'archive'
    archive_dir.mkdir(exist_ok=True)

    # Move to archive
    new_path = archive_dir / filepath.name
    if new_path.exists():
        raise FileExistsError(f"Archive destination already exists: {new_path}")

    shutil.move(str(filepath), str(new_path))

    # Regenerate archive index
    index_path = regenerate_archive_index(type_dir, doc_type)
    if index_path:
        print(f"Updated: {index_path}")

    return new_path


def main():
    parser = argparse.ArgumentParser(
        description='Archive a planning document.'
    )
    parser.add_argument(
        'doc_id',
        nargs='?',
        help='Document ID (e.g., ADR-001, FDP-002, AP-003, RPT-001)'
    )
    parser.add_argument(
        '--regenerate-index',
        action='store_true',
        help='Regenerate archive index without archiving a document'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['adr', 'fdp', 'ap', 'report'],
        help='Document type to regenerate index for (with --regenerate-index)'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    if args.regenerate_index:
        all_types = get_all_types()
        types_to_regen = [args.type] if args.type else list(all_types.keys())
        planning_root = args.project_dir / get_planning_root()

        for dtype in types_to_regen:
            type_config = all_types[dtype]
            type_dir = planning_root / type_config['dir']
            if not type_dir.exists():
                continue

            index_path = regenerate_archive_index(type_dir, dtype)
            if index_path:
                print(f"Regenerated: {index_path}")
            else:
                print(f"No archive found for {dtype}")

        sys.exit(0)

    if not args.doc_id:
        parser.error("doc_id is required (or use --regenerate-index)")

    try:
        new_path = archive_document(args.doc_id, args.project_dir)
        print(f"Archived: {new_path}")
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

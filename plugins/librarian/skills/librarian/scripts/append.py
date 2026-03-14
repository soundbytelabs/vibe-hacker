#!/usr/bin/env python3
"""
Append an addendum to a planning document.

Addenda can be added to any document regardless of status.
This allows locked/accepted documents to have clarifications
or updates added without modifying the original content.

Usage:
    append.py <doc-id> "<title>" [--body "<content>"]

Examples:
    append.py ADR-001 "Performance Clarification"
    append.py FDP-003 "Updated timeline" --body "Phase 1 delayed to Q2"
    append.py ADR-001 "Migration note" --body "Use pg_dump for best results"
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from config import get_project_dir, get_planning_root, get_all_types, get_type_config
from frontmatter import (
    parse_frontmatter,
    render_frontmatter,
    has_addenda_section,
    ADDENDA_SEPARATOR,
)


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

    raise ValueError(f"Unrecognized document ID format: {doc_id}")


def find_document(doc_id: str, project_dir: Path) -> Path:
    """
    Find a document by its ID.

    Searches both active and archive directories.

    Args:
        doc_id: Document ID like 'ADR-001'
        project_dir: Project root directory

    Returns:
        Path to the document

    Raises:
        FileNotFoundError: If document not found
    """
    doc_type, number = parse_doc_id(doc_id)
    type_config = get_type_config(doc_type)

    planning_root = project_dir / get_planning_root()
    doc_dir = planning_root / type_config['dir']

    # Build filename pattern
    prefix = type_config.get('prefix', '')
    if prefix:
        pattern = rf'^{re.escape(prefix)}{number:03d}-.*\.md$'
    else:
        pattern = rf'^{number:03d}-.*\.md$'

    regex = re.compile(pattern)

    # Search in main directory
    if doc_dir.exists():
        for f in doc_dir.iterdir():
            if f.is_file() and regex.match(f.name):
                return f

    # Search in archive
    archive_dir = doc_dir / 'archive'
    if archive_dir.exists():
        for f in archive_dir.iterdir():
            if f.is_file() and regex.match(f.name):
                return f

    raise FileNotFoundError(f"Document not found: {doc_id}")


def append_addendum(filepath: Path, title: str, body: str) -> None:
    """
    Append an addendum to a document.

    Args:
        filepath: Path to the document
        title: Title for the addendum
        body: Body content for the addendum
    """
    content = filepath.read_text()
    today = date.today().isoformat()

    # Update modified date in frontmatter if present
    frontmatter, doc_body = parse_frontmatter(content)
    if frontmatter:
        frontmatter['modified'] = today
        content = render_frontmatter(frontmatter) + doc_body

    # Format the addendum entry
    addendum_entry = f"\n### {today}: {title}\n\n{body}\n"

    if has_addenda_section(content):
        # Append to existing addenda section
        new_content = content.rstrip() + addendum_entry
    else:
        # Create addenda section
        new_content = content.rstrip() + ADDENDA_SEPARATOR + addendum_entry.lstrip('\n')

    filepath.write_text(new_content)


def main():
    parser = argparse.ArgumentParser(
        description='Append an addendum to a planning document.'
    )
    parser.add_argument(
        'doc_id',
        help='Document ID (e.g., ADR-001, FDP-002)'
    )
    parser.add_argument(
        'title',
        help='Addendum title'
    )
    parser.add_argument(
        '--body',
        default='',
        help='Addendum body content (optional, can be added later by editing)'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    try:
        filepath = find_document(args.doc_id, args.project_dir)

        # Use placeholder if no body provided
        body = args.body if args.body else '[Add details here]'

        append_addendum(filepath, args.title, body)
        print(f"Added addendum to: {filepath}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

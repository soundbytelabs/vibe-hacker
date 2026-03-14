#!/usr/bin/env python3
"""
Add a related document link to a planning document.

Usage:
    relate.py <doc-id> <related-id> [--bidirectional]

Examples:
    relate.py ADR-001 FDP-003
    relate.py ADR-001 FDP-003 --bidirectional
    relate.py FDP-002 ADR-001 ADR-002 ADR-003

The --bidirectional flag will also add the first document as related
to the second document.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from config import (
    get_project_dir,
    get_planning_root,
    get_type_config,
)
from frontmatter import parse_frontmatter, render_frontmatter


def parse_doc_id(doc_id: str) -> tuple[str, int]:
    """Parse a document ID into type and number."""
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

    raise ValueError(f"Invalid document ID: {doc_id}")


def find_document(doc_type: str, number: int, project_dir: Path) -> Path | None:
    """Find a document by type and number."""
    type_config = get_type_config(doc_type)
    planning_root = project_dir / get_planning_root()
    doc_dir = planning_root / type_config['dir']

    if not doc_dir.exists():
        return None

    prefix = type_config.get('prefix', '')
    if prefix:
        pattern = re.compile(rf'^{re.escape(prefix)}(\d+)-.*\.md$')
    else:
        pattern = re.compile(r'^(\d+)-.*\.md$')

    # Check main directory
    for f in doc_dir.iterdir():
        if f.is_file():
            match = pattern.match(f.name)
            if match and int(match.group(1)) == number:
                return f

    # Check archive
    archive_dir = doc_dir / 'archive'
    if archive_dir.exists():
        for f in archive_dir.iterdir():
            if f.is_file():
                match = pattern.match(f.name)
                if match and int(match.group(1)) == number:
                    return f

    return None


def find_document_by_id(doc_id: str, project_dir: Path) -> Path:
    """Find a document by its full ID."""
    doc_type, number = parse_doc_id(doc_id)
    filepath = find_document(doc_type, number, project_dir)
    if not filepath:
        raise FileNotFoundError(f"Document not found: {doc_id}")
    return filepath


def add_related(filepath: Path, related_id: str) -> bool:
    """
    Add a related document ID to a document's frontmatter.

    Returns True if added, False if already present.
    """
    content = filepath.read_text()
    today = date.today().isoformat()

    frontmatter, body = parse_frontmatter(content)

    if not frontmatter:
        print(f"Warning: {filepath} has no frontmatter, skipping", file=sys.stderr)
        return False

    # Get current related list
    related = frontmatter.get('related', [])
    if related is None:
        related = []

    # Normalize to uppercase for comparison
    related_upper = [r.upper() for r in related]
    related_id_upper = related_id.upper()

    if related_id_upper in related_upper:
        return False  # Already related

    # Add the new related ID
    related.append(related_id_upper)
    frontmatter['related'] = related
    frontmatter['modified'] = today

    # Write back
    new_content = render_frontmatter(frontmatter) + body
    filepath.write_text(new_content)

    return True


def relate_documents(
    doc_id: str,
    related_ids: list[str],
    project_dir: Path,
    bidirectional: bool = False
) -> tuple[list[str], list[str]]:
    """
    Add related document links.

    Returns:
        Tuple of (added_ids, already_present_ids)
    """
    # Find the main document
    main_filepath = find_document_by_id(doc_id, project_dir)

    added = []
    already_present = []

    for related_id in related_ids:
        # Verify related document exists
        find_document_by_id(related_id, project_dir)

        # Add to main document
        if add_related(main_filepath, related_id):
            added.append(related_id)
        else:
            already_present.append(related_id)

        # Add bidirectional link if requested
        if bidirectional:
            related_filepath = find_document_by_id(related_id, project_dir)
            add_related(related_filepath, doc_id)

    return added, already_present


def main():
    parser = argparse.ArgumentParser(
        description='Add related document links to a planning document.'
    )
    parser.add_argument(
        'doc_id',
        help='Document ID to add relations to (e.g., ADR-001)'
    )
    parser.add_argument(
        'related_ids',
        nargs='+',
        help='IDs of related documents (e.g., FDP-003 ADR-002)'
    )
    parser.add_argument(
        '--bidirectional', '-b',
        action='store_true',
        help='Also add reverse links (related docs will link back)'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    try:
        added, already_present = relate_documents(
            args.doc_id,
            args.related_ids,
            args.project_dir,
            args.bidirectional
        )

        if added:
            print(f"Added relations to {args.doc_id}: {', '.join(added)}")
            if args.bidirectional:
                print(f"Also added reverse links from: {', '.join(added)}")

        if already_present:
            print(f"Already related: {', '.join(already_present)}")

        if not added and not already_present:
            print("No changes made.")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

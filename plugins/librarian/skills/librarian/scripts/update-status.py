#!/usr/bin/env python3
"""
Update the status of a planning document.

Usage:
    update-status.py <doc-id> <new-status>

Examples:
    update-status.py ADR-001 accepted
    update-status.py FDP-002 "in progress"
    update-status.py AP-003 completed
    update-status.py RPT-001 published

Valid statuses are determined by each document type's configuration.
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
    get_valid_statuses,
    is_archive_trigger,
)
from frontmatter import parse_frontmatter, render_frontmatter, extract_status_from_body


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


def extract_current_status(filepath: Path) -> str:
    """Extract current status from a document (frontmatter or body)."""
    content = filepath.read_text()

    # Try frontmatter first
    frontmatter, body = parse_frontmatter(content)
    if frontmatter and 'status' in frontmatter:
        return frontmatter['status']

    # Fallback to body parsing
    status = extract_status_from_body(content)
    if status:
        return status

    return 'Unknown'


def update_status_in_content(content: str, new_status: str) -> str:
    """Update status in both frontmatter and body."""
    today = date.today().isoformat()

    # Parse frontmatter
    frontmatter, body = parse_frontmatter(content)

    # Update frontmatter if present
    if frontmatter:
        frontmatter['status'] = new_status.lower()
        frontmatter['modified'] = today
        new_content = render_frontmatter(frontmatter) + body
    else:
        new_content = content

    # Update body status section
    status_pattern = r'(## Status\s*\n\s*\n?)([^\n#]+)'
    formatted_status = new_status.title()

    def replace_status(match):
        prefix = match.group(1)
        return f"{prefix}{formatted_status}"

    new_content, count = re.subn(status_pattern, replace_status, new_content)

    if count == 0:
        raise ValueError("Could not find Status section in document")

    return new_content


def validate_status(doc_type: str, new_status: str) -> str | None:
    """Validate status is valid for document type. Returns error message or None."""
    valid = get_valid_statuses(doc_type)
    normalized = new_status.lower().strip()

    if normalized not in [s.lower() for s in valid]:
        type_config = get_type_config(doc_type)
        type_name = type_config.get('name', doc_type.upper())
        return f"Invalid status '{new_status}' for {type_name}. Valid statuses: {', '.join(valid)}"

    return None


def update_document_status(doc_id: str, new_status: str, project_dir: Path) -> tuple[Path, str, bool]:
    """
    Update the status of a planning document.

    Returns:
        tuple of (filepath, old_status, should_archive)
    """
    doc_type, number = parse_doc_id(doc_id)

    # Validate status
    error = validate_status(doc_type, new_status)
    if error:
        raise ValueError(error)

    # Find the document
    filepath = find_document(doc_type, number, project_dir)
    if not filepath:
        raise FileNotFoundError(f"Document not found: {doc_id}")

    # Check if already archived
    if 'archive' in filepath.parts:
        raise ValueError(f"Cannot update archived document: {filepath}")

    # Get current status
    old_status = extract_current_status(filepath)

    # Update status
    content = filepath.read_text()
    new_content = update_status_in_content(content, new_status)
    filepath.write_text(new_content)

    # Check if should suggest archiving
    should_archive = is_archive_trigger(doc_type, new_status)

    return filepath, old_status, should_archive


def main():
    parser = argparse.ArgumentParser(
        description='Update the status of a planning document.'
    )
    parser.add_argument(
        'doc_id',
        help='Document ID (e.g., ADR-001, FDP-002, AP-003, RPT-001)'
    )
    parser.add_argument(
        'status',
        help='New status (e.g., accepted, "in progress", completed, published)'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    try:
        filepath, old_status, should_archive = update_document_status(
            args.doc_id, args.status, args.project_dir
        )
        print(f"Updated: {filepath}")
        print(f"Status: {old_status} -> {args.status.title()}")

        if should_archive:
            print(f"\nNote: This document is now {args.status.title()}.")
            print(f"Consider archiving it with: python3 archive.py {args.doc_id}")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

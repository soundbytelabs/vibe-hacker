#!/usr/bin/env python3
"""
Validate and enable editing of a planning document.

This script checks if a document can be edited based on its status and type,
then outputs the file path for editing if allowed.

Usage:
    edit.py <doc-id> [--force]

Examples:
    edit.py ADR-001        # Check if editable, output path
    edit.py FDP-002        # Check if editable, output path
    edit.py ADR-001 --force  # Force edit even if locked (outputs warning)

Exit codes:
    0 - Document is editable, path printed to stdout
    1 - Document cannot be edited (locked status or archived)
    2 - Document not found or other error
"""

import argparse
import re
import sys
from pathlib import Path

from config import (
    get_project_dir,
    get_planning_root,
    get_all_types,
    get_type_config,
    is_status_editable,
)
from frontmatter import parse_frontmatter, extract_status_from_body


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


def find_document(doc_type: str, number: int, project_dir: Path, include_archive: bool = True) -> Path | None:
    """Find a document by type and number."""
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

    # Check main directory first
    for f in doc_dir.iterdir():
        if f.is_file():
            match = pattern.match(f.name)
            if match and int(match.group(1)) == number:
                return f

    # Check archive if requested
    if include_archive:
        archive_dir = doc_dir / 'archive'
        if archive_dir.exists():
            for f in archive_dir.iterdir():
                if f.is_file():
                    match = pattern.match(f.name)
                    if match and int(match.group(1)) == number:
                        return f

    return None


def extract_status(filepath: Path) -> str:
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


def is_archived(filepath: Path) -> bool:
    """Check if document is in archive directory."""
    return 'archive' in filepath.parts


def get_unlock_instruction(doc_type: str, status: str) -> str:
    """Get instruction for how to modify a locked document."""
    status_lower = status.lower()

    instructions = {
        'adr': {
            'accepted': "To modify an accepted ADR, create a new ADR that supersedes it, or add an addendum.",
            'deprecated': "Deprecated ADRs are read-only. Create a new ADR or add an addendum.",
            'superseded': "Superseded ADRs are read-only. Edit the superseding ADR or add an addendum.",
        },
        'fdp': {
            'implemented': "Implemented FDPs are read-only. Create a new FDP or add an addendum.",
            'abandoned': "Abandoned FDPs are read-only. Create a new FDP to revisit.",
        },
        'ap': {
            'completed': "Completed action plans are read-only. Create a new AP for follow-up work.",
            'abandoned': "Abandoned action plans are read-only. Create a new AP to revisit.",
        },
        'report': {
            'published': "Published reports are read-only. Create a new report or add an addendum.",
            'superseded': "Superseded reports are read-only. Add an addendum if needed.",
            'obsoleted': "Obsoleted reports are read-only.",
        },
    }

    type_instructions = instructions.get(doc_type, {})
    return type_instructions.get(status_lower, f"Document with status '{status}' is locked.")


def check_editable(doc_type: str, status: str, is_in_archive: bool) -> tuple[bool, str | None]:
    """
    Check if a document is editable.

    Returns:
        tuple of (is_editable, reason_if_locked)
    """
    if is_in_archive:
        return False, "Archived documents are read-only historical records. Add an addendum instead."

    if is_status_editable(doc_type, status):
        return True, None

    return False, get_unlock_instruction(doc_type, status)


def check_document_editable(doc_id: str, project_dir: Path, force: bool = False) -> tuple[Path, bool, str | None]:
    """
    Check if a document can be edited.

    Returns:
        tuple of (filepath, is_editable, message)
    """
    doc_type, number = parse_doc_id(doc_id)

    # Find the document
    filepath = find_document(doc_type, number, project_dir)
    if not filepath:
        raise FileNotFoundError(f"Document not found: {doc_id}")

    # Get status and check if editable
    status = extract_status(filepath)
    in_archive = is_archived(filepath)

    is_editable, reason = check_editable(doc_type, status, in_archive)

    if not is_editable and force:
        return filepath, True, f"WARNING: Forcing edit of locked document. {reason}"

    if not is_editable:
        return filepath, False, reason

    return filepath, True, None


def main():
    all_types = get_all_types()

    parser = argparse.ArgumentParser(
        description='Check if a planning document can be edited and output its path.'
    )
    parser.add_argument(
        'doc_id',
        help='Document ID (e.g., ADR-001, FDP-002, AP-003, RPT-001)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force edit even if document is locked (use with caution)'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Only output the file path, no status messages'
    )

    args = parser.parse_args()

    try:
        filepath, is_editable, message = check_document_editable(
            args.doc_id, args.project_dir, args.force
        )

        if is_editable:
            if message and not args.quiet:
                print(message, file=sys.stderr)
            print(filepath)
            sys.exit(0)
        else:
            if not args.quiet:
                print(f"Error: Cannot edit {args.doc_id}", file=sys.stderr)
                print(f"Status: {extract_status(filepath)}", file=sys.stderr)
                if message:
                    print(f"\n{message}", file=sys.stderr)
                print(f"\nTip: Use 'append.py {args.doc_id} \"<title>\"' to add an addendum instead.", file=sys.stderr)
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()

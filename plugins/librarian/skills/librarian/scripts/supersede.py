#!/usr/bin/env python3
"""
Create a new document that supersedes an existing one.

This script:
1. Creates a new document of the same type
2. Sets the new document's 'supersedes' field to the old document's ID
3. Updates the old document's 'superseded_by' field
4. Updates the old document's status to 'superseded'
5. Adds an addendum to the old document noting the supersession

Usage:
    supersede.py <old-doc-id> "<new-title>"

Examples:
    supersede.py ADR-001 "Revised Database Strategy"
    supersede.py FDP-003 "Updated Authentication Design"
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
    format_doc_id,
)
from frontmatter import (
    parse_frontmatter,
    render_frontmatter,
    has_addenda_section,
    ADDENDA_SEPARATOR,
)
from new import create_document, slugify


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


def update_old_document(filepath: Path, new_doc_id: str) -> None:
    """Update the old document with superseded_by and add addendum."""
    content = filepath.read_text()
    today = date.today().isoformat()

    frontmatter, body = parse_frontmatter(content)

    if frontmatter:
        frontmatter['superseded_by'] = new_doc_id
        frontmatter['status'] = 'superseded'
        frontmatter['modified'] = today
        content = render_frontmatter(frontmatter) + body

    # Update status in body
    status_pattern = r'(## Status\s*\n\s*\n?)([^\n#]+)'
    content = re.sub(status_pattern, r'\1Superseded', content)

    # Add addendum
    addendum_entry = f"\n### {today}: Superseded\n\nThis document has been superseded by {new_doc_id}.\n"

    if has_addenda_section(content):
        content = content.rstrip() + addendum_entry
    else:
        content = content.rstrip() + ADDENDA_SEPARATOR + addendum_entry.lstrip('\n')

    filepath.write_text(content)


def update_new_document(filepath: Path, old_doc_id: str) -> None:
    """Update the new document with supersedes field."""
    content = filepath.read_text()
    today = date.today().isoformat()

    frontmatter, body = parse_frontmatter(content)

    if frontmatter:
        frontmatter['supersedes'] = old_doc_id
        frontmatter['modified'] = today
        content = render_frontmatter(frontmatter) + body
        filepath.write_text(content)


def supersede_document(old_doc_id: str, new_title: str, project_dir: Path) -> tuple[Path, Path]:
    """
    Create a new document that supersedes an existing one.

    Returns:
        Tuple of (new_document_path, old_document_path)
    """
    doc_type, number = parse_doc_id(old_doc_id)

    # Find old document
    old_filepath = find_document(doc_type, number, project_dir)
    if not old_filepath:
        raise FileNotFoundError(f"Document not found: {old_doc_id}")

    # Check if old doc is already superseded
    old_content = old_filepath.read_text()
    old_frontmatter, _ = parse_frontmatter(old_content)
    if old_frontmatter and old_frontmatter.get('superseded_by'):
        existing = old_frontmatter['superseded_by']
        raise ValueError(f"{old_doc_id} is already superseded by {existing}")

    # Create new document
    new_filepath = create_document(doc_type, new_title, project_dir)

    # Extract new document ID from the created file
    new_content = new_filepath.read_text()
    new_frontmatter, _ = parse_frontmatter(new_content)
    new_doc_id = new_frontmatter.get('id') if new_frontmatter else None

    if not new_doc_id:
        # Fallback: extract from filename
        new_filename = new_filepath.name
        type_config = get_type_config(doc_type)
        prefix = type_config.get('prefix', '')
        if prefix:
            match = re.match(rf'^{re.escape(prefix)}(\d+)-', new_filename)
        else:
            match = re.match(r'^(\d+)-', new_filename)
        if match:
            new_doc_id = format_doc_id(doc_type, int(match.group(1)))

    # Update both documents
    update_new_document(new_filepath, old_doc_id)
    update_old_document(old_filepath, new_doc_id)

    return new_filepath, old_filepath


def main():
    parser = argparse.ArgumentParser(
        description='Create a new document that supersedes an existing one.'
    )
    parser.add_argument(
        'old_doc_id',
        help='ID of document to supersede (e.g., ADR-001)'
    )
    parser.add_argument(
        'new_title',
        help='Title for the new document'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    try:
        new_path, old_path = supersede_document(
            args.old_doc_id, args.new_title, args.project_dir
        )
        print(f"Created: {new_path}")
        print(f"Updated: {old_path}")
        print(f"\n{args.old_doc_id} is now superseded by the new document.")

    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

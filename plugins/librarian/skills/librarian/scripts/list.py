#!/usr/bin/env python3
"""
List planning documents.

Usage:
    list.py [--type TYPE] [--status STATUS] [--include-archived]

Examples:
    list.py                     # List all active documents
    list.py --type adr          # List only ADRs
    list.py --type report       # List only Reports
    list.py --status proposed   # List documents with Proposed status
    list.py --include-archived  # Include archived documents
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
)
from frontmatter import parse_frontmatter, extract_status_from_body, extract_title_from_body


def extract_status(filepath: Path) -> str:
    """Extract status from a document (frontmatter or body)."""
    try:
        content = filepath.read_text()

        # Try frontmatter first
        frontmatter, body = parse_frontmatter(content)
        if frontmatter and 'status' in frontmatter:
            status = frontmatter['status']
            # Capitalize for display
            return status.title() if isinstance(status, str) else str(status)

        # Fallback to body parsing
        status = extract_status_from_body(content)
        if status:
            return status

        return 'Unknown'
    except Exception:
        return 'Error'


def extract_title(filepath: Path) -> str:
    """Extract title from a document (frontmatter or body)."""
    try:
        content = filepath.read_text()

        # Try frontmatter ID to find title in body
        frontmatter, body = parse_frontmatter(content)

        # Extract from body (works with or without frontmatter)
        title = extract_title_from_body(body if frontmatter else content)
        if title:
            return title

        return filepath.stem
    except Exception:
        return filepath.stem


def get_number_pattern(doc_type: str) -> re.Pattern:
    """Get regex pattern to extract number from filename."""
    type_config = get_type_config(doc_type)
    prefix = type_config.get('prefix', '')

    if prefix:
        return re.compile(rf'^{re.escape(prefix)}(\d+)-(.*)\.md$')
    else:
        return re.compile(r'^(\d+)-(.*)\.md$')


def list_documents(
    project_dir: Path,
    doc_type: str | None = None,
    status_filter: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """List planning documents."""
    documents = []

    all_types = get_all_types()
    types_to_check = [doc_type] if doc_type else list(all_types.keys())

    planning_root = project_dir / get_planning_root()

    for dtype in types_to_check:
        type_config = all_types.get(dtype)
        if not type_config:
            continue

        doc_dir = planning_root / type_config['dir']

        if not doc_dir.exists():
            continue

        pattern = get_number_pattern(dtype)
        id_format = type_config.get('id_format', '{number:03d}')
        label = type_config.get('name', dtype.upper())

        # Check main directory
        for f in sorted(doc_dir.iterdir()):
            if not f.is_file():
                continue

            match = pattern.match(f.name)
            if not match:
                continue

            number = int(match.group(1))
            status = extract_status(f)
            title = extract_title(f)

            doc_info = {
                'id': id_format.format(number=number),
                'type': label,
                'title': title,
                'status': status,
                'path': str(f.relative_to(project_dir)),
                'archived': False,
            }

            if status_filter and status.lower() != status_filter.lower():
                continue

            documents.append(doc_info)

        # Check archive directory
        if include_archived:
            archive_dir = doc_dir / 'archive'
            if archive_dir.exists():
                for f in sorted(archive_dir.iterdir()):
                    if not f.is_file():
                        continue

                    match = pattern.match(f.name)
                    if not match:
                        continue

                    number = int(match.group(1))
                    status = extract_status(f)
                    title = extract_title(f)

                    doc_info = {
                        'id': id_format.format(number=number),
                        'type': label,
                        'title': title,
                        'status': status,
                        'path': str(f.relative_to(project_dir)),
                        'archived': True,
                    }

                    if status_filter and status.lower() != status_filter.lower():
                        continue

                    documents.append(doc_info)

    return documents


def format_table(documents: list[dict]) -> str:
    """Format documents as a table."""
    if not documents:
        return "No documents found."

    # Calculate column widths
    headers = ['ID', 'Type', 'Status', 'Title']
    widths = [len(h) for h in headers]

    for doc in documents:
        widths[0] = max(widths[0], len(doc['id']))
        widths[1] = max(widths[1], len(doc['type']))
        widths[2] = max(widths[2], len(doc['status']) + (4 if doc['archived'] else 0))
        widths[3] = max(widths[3], min(len(doc['title']), 50))

    # Format header
    header_fmt = ' | '.join(f"{{:<{w}}}" for w in widths)
    separator = '-+-'.join('-' * w for w in widths)

    lines = [
        header_fmt.format(*headers),
        separator,
    ]

    # Format rows
    for doc in documents:
        status = doc['status']
        if doc['archived']:
            status = f"[A] {status}"

        title = doc['title']
        if len(title) > 50:
            title = title[:47] + '...'

        lines.append(header_fmt.format(
            doc['id'],
            doc['type'],
            status,
            title,
        ))

    return '\n'.join(lines)


def main():
    all_types = get_all_types()
    type_choices = list(all_types.keys())

    parser = argparse.ArgumentParser(
        description='List planning documents.'
    )
    parser.add_argument(
        '--type', '-t',
        choices=type_choices,
        help=f'Filter by document type ({", ".join(type_choices)})'
    )
    parser.add_argument(
        '--status', '-s',
        help='Filter by status (e.g., proposed, accepted, active, draft)'
    )
    parser.add_argument(
        '--include-archived', '-a',
        action='store_true',
        help='Include archived documents'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    documents = list_documents(
        args.project_dir,
        doc_type=args.type,
        status_filter=args.status,
        include_archived=args.include_archived,
    )

    print(format_table(documents))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Create a new planning document with auto-numbering.

Usage:
    new.py <type> "<title>"

Types:
    adr    - Architecture Decision Record
    fdp    - Feature Design Proposal
    ap     - Action Plan
    report - Report

Examples:
    new.py adr "Use PostgreSQL for persistence"
    new.py fdp "User Authentication System"
    new.py ap "Implement login flow"
    new.py report "Q4 Performance Analysis"
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path
from string import Template

from config import (
    get_project_dir,
    get_all_types,
    get_type_config,
    get_doc_dir,
    get_template_path,
    format_filename,
)


def slugify(title: str) -> str:
    """Convert title to URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def get_number_pattern(doc_type: str) -> str:
    """Get regex pattern to extract number from filename."""
    type_config = get_type_config(doc_type)
    prefix = type_config.get('prefix', '')

    if prefix:
        # Pattern like FDP-001-slug.md or AP-001-slug.md
        return rf'^{re.escape(prefix)}(\d+)-.*\.md$'
    else:
        # Pattern like 001-slug.md (ADRs)
        return r'^(\d+)-.*\.md$'


def find_next_number(doc_dir: Path, pattern: str) -> int:
    """Find the next available document number."""
    if not doc_dir.exists():
        return 1

    max_num = 0
    regex = re.compile(pattern)

    for f in doc_dir.iterdir():
        if f.is_file():
            match = regex.match(f.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

    # Also check archive directory
    archive_dir = doc_dir / 'archive'
    if archive_dir.exists():
        for f in archive_dir.iterdir():
            if f.is_file():
                match = regex.match(f.name)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)

    return max_num + 1


def load_template(doc_type: str) -> str:
    """Load template content for a document type."""
    template_path = get_template_path(doc_type)

    if template_path and template_path.exists():
        return template_path.read_text()

    # Fallback: try to find template relative to script
    type_config = get_type_config(doc_type)
    template_name = type_config.get('template', f'{doc_type}.md')

    script_dir = Path(__file__).parent.parent / 'templates'
    fallback_path = script_dir / template_name

    if fallback_path.exists():
        return fallback_path.read_text()

    # Try CLAUDE_PLUGIN_ROOT
    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT')
    if plugin_root:
        plugin_path = Path(plugin_root) / 'skills' / 'planning' / 'templates' / template_name
        if plugin_path.exists():
            return plugin_path.read_text()

    raise FileNotFoundError(f"Template not found for type: {doc_type}")


def create_document(doc_type: str, title: str, project_dir: Path) -> Path:
    """Create a new planning document."""
    type_config = get_type_config(doc_type)

    doc_dir = project_dir / get_doc_dir(doc_type)
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Find next number
    pattern = get_number_pattern(doc_type)
    next_num = find_next_number(doc_dir, pattern)

    # Create filename using config format
    slug = slugify(title)
    filename = format_filename(doc_type, next_num, slug)
    filepath = doc_dir / filename

    # Check if file already exists
    if filepath.exists():
        raise FileExistsError(f"File already exists: {filepath}")

    # Read template
    template_content = load_template(doc_type)

    # Substitute variables
    # NUMBER is zero-padded for display in document
    num_str = f"{next_num:03d}"

    template = Template(template_content)
    content = template.safe_substitute(
        NUMBER=num_str,
        TITLE=title,
        DATE=date.today().isoformat(),
    )

    # Write file
    filepath.write_text(content)

    return filepath


def main():
    # Get available types from config
    all_types = get_all_types()
    type_choices = list(all_types.keys())

    parser = argparse.ArgumentParser(
        description='Create a new planning document with auto-numbering.'
    )
    parser.add_argument(
        'type',
        choices=type_choices,
        help=f'Document type ({", ".join(type_choices)})'
    )
    parser.add_argument(
        'title',
        help='Document title'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=get_project_dir(),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    try:
        filepath = create_document(args.type, args.title, args.project_dir)
        print(f"Created: {filepath}")
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

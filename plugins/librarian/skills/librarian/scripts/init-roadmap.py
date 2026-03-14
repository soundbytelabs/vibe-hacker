#!/usr/bin/env python3
"""
Initialize a project roadmap from template.

Usage:
    init-roadmap.py [--force]

Options:
    --force     Overwrite existing roadmap

The roadmap is created at <planning_root>/roadmap.md
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from config import get_planning_root, get_project_dir


def get_template_path() -> Path:
    """Get path to roadmap template."""
    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
    if plugin_root:
        return Path(plugin_root) / 'skills' / 'planning' / 'templates' / 'roadmap.md'
    # Fallback: relative to this script
    return Path(__file__).parent.parent / 'templates' / 'roadmap.md'


def init_roadmap(project_dir: Path, force: bool = False) -> Path:
    """Initialize roadmap from template."""
    planning_root = get_planning_root()
    roadmap_path = project_dir / planning_root / 'roadmap.md'

    if roadmap_path.exists() and not force:
        print(f"Roadmap already exists: {roadmap_path}")
        print("Use --force to overwrite")
        sys.exit(1)

    template_path = get_template_path()
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        sys.exit(1)

    # Read template and substitute date
    content = template_path.read_text()
    content = content.replace('{{DATE}}', date.today().isoformat())

    # Ensure directory exists
    roadmap_path.parent.mkdir(parents=True, exist_ok=True)

    # Write roadmap
    roadmap_path.write_text(content)
    print(f"Created: {roadmap_path.relative_to(project_dir)}")

    return roadmap_path


def main():
    parser = argparse.ArgumentParser(
        description='Initialize project roadmap from template.'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing roadmap'
    )
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')),
        help='Project directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    init_roadmap(args.project_dir, force=args.force)


if __name__ == '__main__':
    main()

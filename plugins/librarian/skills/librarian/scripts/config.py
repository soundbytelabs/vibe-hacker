"""
Shared configuration for planning scripts.

Reads planning configuration from vibe-hacker.json.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

# Current schema version
CURRENT_VERSION = '0.2.0'

# Default planning root if not configured
DEFAULT_PLANNING_ROOT = 'docs/planning'

# Default type definitions (v0.2.0 format)
DEFAULT_TYPES = {
    'adr': {
        'name': 'Architecture Decision Record',
        'dir': 'decisions',
        'prefix': '',
        'filename_format': '{number:03d}-{slug}.md',
        'id_format': 'ADR-{number:03d}',
        'template': 'adr.md',
        'statuses': {
            'initial': 'proposed',
            'editable': ['proposed'],
            'final': ['accepted'],
            'archive_triggers': ['deprecated', 'superseded']
        }
    },
    'fdp': {
        'name': 'Feature Design Proposal',
        'dir': 'designs',
        'prefix': 'FDP-',
        'filename_format': 'FDP-{number:03d}-{slug}.md',
        'id_format': 'FDP-{number:03d}',
        'template': 'fdp.md',
        'statuses': {
            'initial': 'proposed',
            'editable': ['proposed', 'in progress'],
            'final': ['implemented'],
            'archive_triggers': ['implemented', 'abandoned']
        }
    },
    'ap': {
        'name': 'Action Plan',
        'dir': 'action-plans',
        'prefix': 'AP-',
        'filename_format': 'AP-{number:03d}-{slug}.md',
        'id_format': 'AP-{number:03d}',
        'template': 'action-plan.md',
        'statuses': {
            'initial': 'active',
            'editable': ['active'],
            'final': ['completed'],
            'archive_triggers': ['completed', 'abandoned']
        }
    },
    'report': {
        'name': 'Report',
        'dir': 'reports',
        'prefix': 'RPT-',
        'filename_format': 'RPT-{number:03d}-{slug}.md',
        'id_format': 'RPT-{number:03d}',
        'template': 'report.md',
        'statuses': {
            'initial': 'draft',
            'editable': ['draft'],
            'final': ['published'],
            'archive_triggers': ['superseded', 'obsoleted']
        }
    }
}


def get_project_dir() -> Path:
    """Get the project directory."""
    return Path(os.environ.get('CLAUDE_PROJECT_DIR', '.'))


def _get_git_root(project_dir: Path) -> Optional[Path]:
    """Get the git root for the given directory, or None if not in a repo."""
    try:
        result = subprocess.run(
            ['git', '-C', str(project_dir), 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_config_path() -> Path:
    """Get path to vibe-hacker.json config file.

    Resolution order (multi-repo aware):
      1. CLAUDE_PROJECT_DIR (authoritative workspace root when set)
      2. Git root (standalone repo fallback, prevents parent leakage)
      3. Current directory (last resort)
    """
    project_dir = get_project_dir()

    # CLAUDE_PROJECT_DIR is authoritative — it's the workspace root
    workspace_config = project_dir / '.claude' / 'vibe-hacker.json'
    if workspace_config.exists():
        return workspace_config

    # Fall back to git root (prevents parent-repo leakage for standalone use)
    git_root = _get_git_root(project_dir)
    if git_root:
        git_config = git_root / '.claude' / 'vibe-hacker.json'
        if git_config.exists():
            return git_config

    # Last resort
    return workspace_config


def load_config() -> dict:
    """Load configuration from vibe-hacker.json."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config: dict) -> None:
    """Save configuration to vibe-hacker.json."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + '\n')


def get_planning_version() -> str:
    """Get the planning schema version from config."""
    config = load_config()
    return config.get('planning', {}).get('version', '0.1.0')


def get_planning_root() -> str:
    """Get the planning root directory from config."""
    config = load_config()

    # Check protected_paths.planning_root first (as shown in FDP-002)
    planning_root = config.get('protected_paths', {}).get('planning_root')
    if planning_root:
        return planning_root

    # Check top-level planning.root
    planning_root = config.get('planning', {}).get('root')
    if planning_root:
        return planning_root

    return DEFAULT_PLANNING_ROOT


def get_type_config(doc_type: str) -> dict:
    """
    Get the full configuration for a document type.

    Args:
        doc_type: Document type key (adr, fdp, ap, report)

    Returns:
        Type configuration dictionary
    """
    config = load_config()
    planning_config = config.get('planning', {})
    subdirs = planning_config.get('subdirs', {})

    default = DEFAULT_TYPES.get(doc_type, {}).copy()

    # Override dir from subdirs config if present
    if doc_type in subdirs:
        default['dir'] = subdirs[doc_type]

    return default


def get_all_types() -> dict:
    """
    Get configuration for all document types.

    Returns:
        Dictionary mapping type keys to their configurations
    """
    config = load_config()
    planning_config = config.get('planning', {})
    subdirs = planning_config.get('subdirs', {})

    # Start with defaults
    types = {k: v.copy() for k, v in DEFAULT_TYPES.items()}

    # Apply subdirs overrides
    for type_key, subdir in subdirs.items():
        if type_key in types:
            types[type_key]['dir'] = subdir

    return types


def get_doc_dir(doc_type: str) -> str:
    """Get the directory path for a document type."""
    planning_root = get_planning_root()
    type_config = get_type_config(doc_type)
    return f"{planning_root}/{type_config['dir']}"


def get_planning_subdirs() -> dict:
    """Get subdirectory names for each document type."""
    types = get_all_types()
    return {key: cfg['dir'] for key, cfg in types.items()}


def is_status_editable(doc_type: str, status: str) -> bool:
    """
    Check if a document with given status can be edited.

    Args:
        doc_type: Document type key
        status: Current status (case-insensitive)

    Returns:
        True if document can be edited
    """
    type_config = get_type_config(doc_type)
    statuses = type_config.get('statuses', {})
    editable = statuses.get('editable', [])
    return status.lower() in [s.lower() for s in editable]


def is_archive_trigger(doc_type: str, status: str) -> bool:
    """
    Check if a status should trigger an archive suggestion.

    Args:
        doc_type: Document type key
        status: Current status (case-insensitive)

    Returns:
        True if status suggests archiving
    """
    type_config = get_type_config(doc_type)
    statuses = type_config.get('statuses', {})
    triggers = statuses.get('archive_triggers', [])
    return status.lower() in [s.lower() for s in triggers]


def get_valid_statuses(doc_type: str) -> list:
    """
    Get all valid statuses for a document type.

    Args:
        doc_type: Document type key

    Returns:
        List of valid status strings
    """
    type_config = get_type_config(doc_type)
    statuses = type_config.get('statuses', {})

    all_statuses = set()
    all_statuses.add(statuses.get('initial', ''))
    all_statuses.update(statuses.get('editable', []))
    all_statuses.update(statuses.get('final', []))
    all_statuses.update(statuses.get('archive_triggers', []))
    all_statuses.discard('')

    return sorted(all_statuses)


def format_doc_id(doc_type: str, number: int) -> str:
    """
    Format a document ID using the type's id_format.

    Args:
        doc_type: Document type key
        number: Document number

    Returns:
        Formatted ID string (e.g., "ADR-001")
    """
    type_config = get_type_config(doc_type)
    id_format = type_config.get('id_format', '{number:03d}')
    return id_format.format(number=number)


def format_filename(doc_type: str, number: int, slug: str) -> str:
    """
    Format a document filename using the type's filename_format.

    Args:
        doc_type: Document type key
        number: Document number
        slug: URL-friendly title slug

    Returns:
        Formatted filename (e.g., "001-my-title.md")
    """
    type_config = get_type_config(doc_type)
    filename_format = type_config.get('filename_format', '{number:03d}-{slug}.md')
    return filename_format.format(number=number, slug=slug)


def get_template_path(doc_type: str) -> Optional[Path]:
    """
    Get the path to a document type's template.

    Args:
        doc_type: Document type key

    Returns:
        Path to template file or None if not found
    """
    type_config = get_type_config(doc_type)
    template_name = type_config.get('template')
    if not template_name:
        return None

    plugin_root = Path(os.environ.get('CLAUDE_PLUGIN_ROOT', '.'))
    template_path = plugin_root / 'skills' / 'planning' / 'templates' / template_name

    if template_path.exists():
        return template_path

    return None

"""
Frontmatter parsing and rendering utilities for planning documents.

Provides functions to parse YAML frontmatter from markdown documents
and render frontmatter back to YAML format.
"""

import re
from datetime import datetime
from typing import Optional

# Try to import yaml, fall back to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Frontmatter delimiters
FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)

# Addenda section markers
ADDENDA_SEPARATOR = "\n\n---\n\n## Addenda\n"
ADDENDA_PATTERN = re.compile(r'\n---\n\n## Addenda\n', re.IGNORECASE)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Extract frontmatter and body from a markdown document.

    Args:
        content: Full document content

    Returns:
        Tuple of (frontmatter_dict, body_content)
        Returns ({}, content) if no frontmatter found
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    frontmatter_text = match.group(1)
    body = content[match.end():]

    if HAS_YAML:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            return frontmatter or {}, body
        except yaml.YAMLError:
            return {}, content
    else:
        # Basic fallback parsing for simple key: value pairs
        frontmatter = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                # Handle null/empty values
                if value.lower() in ('null', '~', ''):
                    value = None
                # Handle lists (basic)
                elif value.startswith('[') and value.endswith(']'):
                    items = value[1:-1].split(',')
                    value = [item.strip().strip('"\'') for item in items if item.strip()]
                # Strip quotes
                elif value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                frontmatter[key] = value
        return frontmatter, body


def render_frontmatter(data: dict) -> str:
    """
    Render a frontmatter dictionary to YAML string with delimiters.

    Args:
        data: Dictionary of frontmatter fields

    Returns:
        YAML frontmatter string including --- delimiters
    """
    if HAS_YAML:
        # Custom representer for None to output 'null'
        def represent_none(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:null', 'null')

        yaml.add_representer(type(None), represent_none)
        yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return f"---\n{yaml_content}---\n"
    else:
        # Basic fallback rendering
        lines = ['---']
        for key, value in data.items():
            if value is None:
                lines.append(f"{key}: null")
            elif isinstance(value, list):
                if not value:
                    lines.append(f"{key}: []")
                else:
                    lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
            else:
                lines.append(f"{key}: {value}")
        lines.append('---')
        return '\n'.join(lines) + '\n'


def update_frontmatter(content: str, updates: dict) -> str:
    """
    Update specific fields in a document's frontmatter.

    Args:
        content: Full document content
        updates: Dictionary of fields to update

    Returns:
        Updated document content
    """
    frontmatter, body = parse_frontmatter(content)
    frontmatter.update(updates)
    return render_frontmatter(frontmatter) + body


def get_frontmatter_field(content: str, field: str, default=None):
    """
    Get a specific field from document frontmatter.

    Args:
        content: Full document content
        field: Field name to retrieve
        default: Default value if field not found

    Returns:
        Field value or default
    """
    frontmatter, _ = parse_frontmatter(content)
    return frontmatter.get(field, default)


def has_frontmatter(content: str) -> bool:
    """Check if document has frontmatter."""
    return bool(FRONTMATTER_PATTERN.match(content))


def has_addenda_section(content: str) -> bool:
    """Check if document has an addenda section."""
    return bool(ADDENDA_PATTERN.search(content))


def append_addendum(content: str, title: str, body: str) -> str:
    """
    Add an addendum to a document.

    Creates the addenda section if it doesn't exist.
    Updates the modified date in frontmatter.

    Args:
        content: Full document content
        title: Title for the addendum (without date)
        body: Addendum content

    Returns:
        Updated document content
    """
    date = datetime.now().strftime("%Y-%m-%d")
    addendum_entry = f"\n### {date}: {title}\n\n{body}\n"

    # Update modified date in frontmatter
    frontmatter, doc_body = parse_frontmatter(content)
    if frontmatter:
        frontmatter['modified'] = date
        content = render_frontmatter(frontmatter) + doc_body

    if has_addenda_section(content):
        # Append to existing addenda section
        return content.rstrip() + addendum_entry
    else:
        # Create addenda section
        return content.rstrip() + ADDENDA_SEPARATOR + addendum_entry.lstrip('\n')


def create_frontmatter(
    doc_type: str,
    doc_id: str,
    status: str,
    created: Optional[str] = None,
    supersedes: Optional[str] = None,
    related: Optional[list] = None
) -> dict:
    """
    Create a standard frontmatter dictionary for a new document.

    Args:
        doc_type: Document type (adr, fdp, ap, report)
        doc_id: Display ID (ADR-001, FDP-002, etc.)
        status: Initial status
        created: Creation date (defaults to today)
        supersedes: ID of document this supersedes (optional)
        related: List of related document IDs (optional)

    Returns:
        Frontmatter dictionary
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        'type': doc_type,
        'id': doc_id,
        'status': status,
        'created': created or today,
        'modified': today,
        'supersedes': supersedes,
        'superseded_by': None,
        'obsoleted_by': None,
        'related': related or [],
    }


def extract_status_from_body(content: str) -> Optional[str]:
    """
    Extract status from the ## Status section in document body.

    Args:
        content: Document content (body only, no frontmatter)

    Returns:
        Status string or None if not found
    """
    # Look for ## Status section
    status_match = re.search(r'^## Status\s*\n+([^\n#]+)', content, re.MULTILINE)
    if status_match:
        return status_match.group(1).strip()
    return None


def extract_title_from_body(content: str) -> Optional[str]:
    """
    Extract title from the H1 heading in document body.

    Args:
        content: Document content

    Returns:
        Title string (without ID prefix) or None if not found
    """
    # Look for # heading, optionally with ID prefix
    title_match = re.search(r'^# (?:(?:ADR|FDP|AP|RPT)-\d+:\s*)?(.+)$', content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    return None


def extract_date_from_body(content: str) -> Optional[str]:
    """
    Extract date from ## Date or ## Created section in document body.

    Args:
        content: Document content

    Returns:
        Date string (ISO format) or None if not found
    """
    # Look for ## Date or ## Created section
    date_match = re.search(r'^## (?:Date|Created)\s*\n+(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
    if date_match:
        return date_match.group(1)
    return None

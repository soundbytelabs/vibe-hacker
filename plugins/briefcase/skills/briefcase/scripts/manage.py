#!/usr/bin/env python3
"""Briefcase management script for vibe-hacker.

Manages a personal briefcase of topic-organized markdown files for capturing
thoughts, observations, and half-formed ideas.

Usage:
    manage.py create <topic> "<description>"
    manage.py add "<thought>" [--topic <topic>]
    manage.py list [<topic>]
    manage.py archive <topic>
    manage.py rename <old-topic> <new-topic>
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def find_project_root():
    """Walk up from CWD to find .claude/vibe-hacker.json."""
    p = Path.cwd()
    while p != p.parent:
        if (p / ".claude" / "vibe-hacker.json").exists():
            return p
        p = p.parent
    return Path.cwd()


def load_config():
    """Load briefcase config from .claude/vibe-hacker.json."""
    config_path = find_project_root() / ".claude" / "vibe-hacker.json"
    if config_path.exists():
        with open(config_path) as f:
            full = json.load(f)
            return full.get("briefcase", {})
    return {}


def briefcase_root():
    """Get the briefcase root directory."""
    config = load_config()
    root = config.get("root", "docs/briefcase")
    return find_project_root() / root


def topic_path(name: str) -> Path:
    """Get path to a specific topic file."""
    return briefcase_root() / f"{name}.md"


def archive_path(name: str) -> Path:
    """Get path to archived topic file."""
    return briefcase_root() / "archive" / f"{name}.md"


# --- Topic file parsing ---

def parse_topic(path: Path) -> dict:
    """Parse a topic file into structured data.

    Returns dict with keys: title, description, entries.
    Each entry is {date: str, lines: [str]}.
    """
    text = path.read_text()
    lines = text.split("\n")

    title = ""
    description = ""
    entries = []
    current_date = None
    current_lines = []
    in_entries = False

    for line in lines:
        stripped = line.strip()

        # Title
        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
            continue

        # Entries section
        if stripped == "## Entries":
            in_entries = True
            continue

        if not in_entries:
            # Description is text between title and ## Entries
            if title and stripped:
                description = stripped
            continue

        # Date headers within entries
        date_match = re.match(r"^### (\d{4}-\d{2}-\d{2})$", stripped)
        if date_match:
            # Save previous entry
            if current_date:
                entries.append({"date": current_date, "lines": current_lines})
            current_date = date_match.group(1)
            current_lines = []
            continue

        if current_date is not None:
            current_lines.append(line)

    # Save last entry
    if current_date:
        entries.append({"date": current_date, "lines": current_lines})

    return {
        "title": title,
        "description": description,
        "entries": entries,
    }


def write_topic(path: Path, title: str, description: str, entries: list):
    """Write a topic file from structured data."""
    lines = [f"# {title}", ""]
    if description:
        lines.append(description)
    lines.extend(["", "## Entries", ""])

    for entry in entries:
        lines.append(f"### {entry['date']}")
        lines.extend(entry["lines"])
        # Ensure blank line between entries
        if entry["lines"] and entry["lines"][-1].strip():
            lines.append("")

    path.write_text("\n".join(lines))


# --- Commands ---

def cmd_create(args):
    """Create a new topic."""
    path = topic_path(args.topic)
    if path.exists():
        print(f"Error: Topic '{args.topic}' already exists at {path}")
        sys.exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)

    title = args.topic.replace("-", " ").title()
    write_topic(path, title, args.description, [])
    print(f"Created topic: {path}")


def cmd_add(args):
    """Add a thought to a topic."""
    if args.topic:
        path = topic_path(args.topic)
        if not path.exists():
            print(f"Error: Topic '{args.topic}' not found. Create it first with: manage.py create {args.topic} \"description\"")
            sys.exit(1)
    else:
        # No topic specified — list existing topics so the agent can triage
        root = briefcase_root()
        if root.exists():
            topics = sorted(f.stem for f in root.glob("*.md"))
            if topics:
                print("Existing topics (choose one or create new):")
                for t in topics:
                    data = parse_topic(topic_path(t))
                    entry_count = len(data["entries"])
                    desc = data["description"]
                    print(f"  {t} — {entry_count} entries" + (f" — {desc}" if desc else ""))
            else:
                print("No topics exist yet. Create one first.")
        else:
            print("No briefcase directory yet. Create a topic first.")
        sys.exit(2)  # Exit 2 = needs triage (not an error, just incomplete)

    today = date.today().isoformat()
    data = parse_topic(path)

    # Check if today's date already has an entry
    today_entry = None
    for entry in data["entries"]:
        if entry["date"] == today:
            today_entry = entry
            break

    if today_entry:
        # Append to existing date
        # Add blank line before new thought if there's existing content
        content_lines = [l for l in today_entry["lines"] if l.strip()]
        if content_lines:
            today_entry["lines"].append("")
        today_entry["lines"].append(args.thought)
        today_entry["lines"].append("")
    else:
        # New date entry
        data["entries"].append({
            "date": today,
            "lines": ["", args.thought, ""],
        })

    write_topic(path, data["title"], data["description"], data["entries"])
    print(f"Added to '{args.topic}': {args.thought}")


def cmd_list(args):
    """List topics or show a specific topic."""
    root = briefcase_root()

    if args.topic:
        # Show specific topic
        path = topic_path(args.topic)
        if not path.exists():
            print(f"Error: Topic '{args.topic}' not found.")
            sys.exit(1)

        data = parse_topic(path)
        print(f"# {data['title']}")
        if data["description"]:
            print(f"\n{data['description']}")
        print(f"\n{len(data['entries'])} entries")

        for entry in data["entries"]:
            print(f"\n### {entry['date']}")
            for line in entry["lines"]:
                if line.strip():
                    print(f"  {line.strip()}")
    else:
        # List all topics
        if not root.exists():
            print("No briefcase found.")
            return

        files = sorted(root.glob("*.md"))
        if not files:
            print("No topics found.")
            return

        print("# Briefcase Topics\n")
        for f in files:
            data = parse_topic(f)
            entry_count = len(data["entries"])
            desc = data["description"]
            # Find most recent entry date
            if data["entries"]:
                last_date = data["entries"][-1]["date"]
                date_info = f", last: {last_date}"
            else:
                date_info = ""
            print(f"  **{f.stem}** — {entry_count} entries{date_info}")
            if desc:
                print(f"    {desc}")

        # Check for archived topics
        archive_dir = root / "archive"
        if archive_dir.exists():
            archived = sorted(archive_dir.glob("*.md"))
            if archived:
                print(f"\n  ({len(archived)} archived topics in archive/)")


def cmd_archive(args):
    """Archive a topic."""
    path = topic_path(args.topic)
    if not path.exists():
        print(f"Error: Topic '{args.topic}' not found.")
        sys.exit(1)

    dest = archive_path(args.topic)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"Error: Archived topic '{args.topic}' already exists.")
        sys.exit(1)

    path.rename(dest)
    print(f"Archived: {args.topic} → {dest}")


def cmd_rename(args):
    """Rename a topic."""
    old = topic_path(args.old_topic)
    if not old.exists():
        print(f"Error: Topic '{args.old_topic}' not found.")
        sys.exit(1)

    new = topic_path(args.new_topic)
    if new.exists():
        print(f"Error: Topic '{args.new_topic}' already exists.")
        sys.exit(1)

    # Update the title inside the file
    data = parse_topic(old)
    new_title = args.new_topic.replace("-", " ").title()
    write_topic(new, new_title, data["description"], data["entries"])
    old.unlink()
    print(f"Renamed: {args.old_topic} → {args.new_topic}")


def main():
    parser = argparse.ArgumentParser(description="Briefcase management")
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p = sub.add_parser("create", help="Create a new topic")
    p.add_argument("topic", help="Topic name (kebab-case)")
    p.add_argument("description", help="Short description of the topic")

    # add
    p = sub.add_parser("add", help="Add a thought")
    p.add_argument("thought", help="The thought to capture")
    p.add_argument("--topic", "-t", default=None, help="Target topic (omit to list existing)")

    # list
    p = sub.add_parser("list", help="List topics or show a topic")
    p.add_argument("topic", nargs="?", default=None, help="Topic name (omit for all)")

    # archive
    p = sub.add_parser("archive", help="Archive a topic")
    p.add_argument("topic", help="Topic name")

    # rename
    p = sub.add_parser("rename", help="Rename a topic")
    p.add_argument("old_topic", help="Current topic name")
    p.add_argument("new_topic", help="New topic name")

    args = parser.parse_args()

    commands = {
        "create": cmd_create,
        "add": cmd_add,
        "list": cmd_list,
        "archive": cmd_archive,
        "rename": cmd_rename,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Backlog management script for vibe-hacker.

Manages lightweight markdown backlogs for capturing ideas, polish items,
and small improvements. Each backlog is a markdown file with YAML frontmatter
for auto-incrementing IDs.

Usage:
    manage.py create <name> "<description>"
    manage.py add <name> "<item>" [--priority high|med|low] [--notes "<notes>"]
    manage.py list [<name>] [--status open|done|dropped] [--all]
    manage.py done <name> <id>
    manage.py drop <name> <id> ["<reason>"]
    manage.py reopen <name> <id>
    manage.py edit <name> <id> "<new-text>"
    manage.py prioritize <name> <id> <priority>
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path


def load_config():
    """Load backlog config from .claude/vibe-hacker.json."""
    config_path = find_project_root() / ".claude" / "vibe-hacker.json"
    if config_path.exists():
        with open(config_path) as f:
            full = json.load(f)
            return full.get("backlog", {})
    return {}


def find_project_root():
    """Walk up from CWD to find .claude/vibe-hacker.json."""
    p = Path.cwd()
    while p != p.parent:
        if (p / ".claude" / "vibe-hacker.json").exists():
            return p
        p = p.parent
    # Fallback to CWD
    return Path.cwd()


def backlog_root():
    """Get the backlog root directory."""
    config = load_config()
    root = config.get("root", "docs/backlogs")
    return find_project_root() / root


def backlog_path(name: str) -> Path:
    """Get path to a specific backlog file."""
    return backlog_root() / f"{name}.md"


# --- Frontmatter parsing ---

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm_text = text[3:end].strip()
    body = text[end + 3:].lstrip("\n")

    metadata = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            # Handle int values
            if value.isdigit():
                value = int(value)
            metadata[key.strip()] = value

    return metadata, body


def write_frontmatter(metadata: dict) -> str:
    """Serialize metadata to YAML frontmatter string."""
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


# --- Item parsing ---

ITEM_RE = re.compile(
    r"^- \*\*#(\d+)\*\*"           # ID
    r"(?: \[(high|med|low)\])?"    # optional priority
    r" (.+?)"                       # item text
    r" \((\d{4}-\d{2}-\d{2})"     # added date
    r"(?:\s*→\s*(\d{4}-\d{2}-\d{2}))?"  # optional completed/dropped date
    r"\)$"
)


def parse_item(line: str) -> dict | None:
    """Parse a backlog item line into a dict."""
    m = ITEM_RE.match(line.strip())
    if not m:
        return None
    return {
        "id": int(m.group(1)),
        "priority": m.group(2),
        "text": m.group(3).strip(),
        "added": m.group(4),
        "closed": m.group(5),
    }


def format_item(item: dict) -> str:
    """Format a backlog item dict into a markdown line."""
    priority = f" [{item['priority']}]" if item.get("priority") else ""
    date_str = item["added"]
    if item.get("closed"):
        date_str += f" → {item['closed']}"
    return f"- **#{item['id']}**{priority} {item['text']} ({date_str})"


# --- Section parsing ---

def parse_backlog(path: Path) -> tuple[dict, list, list, list]:
    """Parse a backlog file into (metadata, open, done, dropped) lists."""
    text = path.read_text()
    metadata, body = parse_frontmatter(text)

    open_items = []
    done_items = []
    dropped_items = []

    current_section = None
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## Open"):
            current_section = "open"
        elif stripped.startswith("## Done"):
            current_section = "done"
        elif stripped.startswith("## Dropped"):
            current_section = "dropped"
        elif stripped.startswith("- **#"):
            item = parse_item(stripped)
            if item:
                if current_section == "open":
                    open_items.append(item)
                elif current_section == "done":
                    done_items.append(item)
                elif current_section == "dropped":
                    dropped_items.append(item)

    return metadata, open_items, done_items, dropped_items


def write_backlog(path: Path, metadata: dict, open_items: list, done_items: list, dropped_items: list):
    """Write a backlog file from structured data."""
    fm = write_frontmatter(metadata)
    name = metadata.get("name", path.stem)
    description = metadata.get("description", "")

    lines = [fm, "", f"# {name.replace('-', ' ').title()} Backlog"]
    if description:
        lines.extend(["", description])

    lines.extend(["", "## Open", ""])
    for item in open_items:
        lines.append(format_item(item))

    lines.extend(["", "## Done", ""])
    for item in done_items:
        lines.append(format_item(item))

    lines.extend(["", "## Dropped", ""])
    for item in dropped_items:
        lines.append(format_item(item))

    lines.append("")  # trailing newline
    path.write_text("\n".join(lines))


# --- Commands ---

def cmd_create(args):
    """Create a new backlog."""
    path = backlog_path(args.name)
    if path.exists():
        print(f"Error: Backlog '{args.name}' already exists at {path}")
        sys.exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    title = args.name.replace("-", " ").title()

    metadata = {
        "type": "backlog",
        "name": args.name,
        "description": args.description,
        "created": today,
        "next_id": 1,
    }

    write_backlog(path, metadata, [], [], [])
    print(f"Created backlog: {path}")


def cmd_add(args):
    """Add an item to a backlog."""
    path = backlog_path(args.name)
    if not path.exists():
        print(f"Error: Backlog '{args.name}' not found. Create it first with: manage.py create {args.name} \"description\"")
        sys.exit(1)

    metadata, open_items, done_items, dropped_items = parse_backlog(path)

    item_id = int(metadata.get("next_id", 1))
    today = date.today().isoformat()

    text = args.item
    if args.notes:
        text += f" — {args.notes}"

    item = {
        "id": item_id,
        "priority": args.priority,
        "text": text,
        "added": today,
        "closed": None,
    }

    # Insert by priority order
    priority_order = {"high": 0, "med": 1, "low": 2, None: 3}
    insert_idx = len(open_items)
    item_rank = priority_order.get(args.priority, 3)
    for i, existing in enumerate(open_items):
        existing_rank = priority_order.get(existing.get("priority"), 3)
        if item_rank < existing_rank:
            insert_idx = i
            break

    open_items.insert(insert_idx, item)
    metadata["next_id"] = item_id + 1

    write_backlog(path, metadata, open_items, done_items, dropped_items)
    priority_str = f" [{args.priority}]" if args.priority else ""
    print(f"Added #{item_id}{priority_str}: {text}")


def cmd_list(args):
    """List backlog items."""
    if args.name:
        # List specific backlog
        path = backlog_path(args.name)
        if not path.exists():
            print(f"Error: Backlog '{args.name}' not found.")
            sys.exit(1)

        metadata, open_items, done_items, dropped_items = parse_backlog(path)
        desc = metadata.get("description", "")

        print(f"# {args.name}" + (f" — {desc}" if desc else ""))

        status = args.status

        if not status or status == "open":
            if open_items:
                print(f"\n## Open ({len(open_items)})")
                for item in open_items:
                    print(f"  {format_item(item)}")
            elif not status:
                print("\n## Open (0)")

        if not status or status == "done":
            if done_items:
                print(f"\n## Done ({len(done_items)})")
                for item in done_items:
                    print(f"  {format_item(item)}")
            elif not status:
                print(f"\n## Done ({len(done_items)})")

        if not status or status == "dropped":
            if dropped_items:
                print(f"\n## Dropped ({len(dropped_items)})")
                for item in dropped_items:
                    print(f"  {format_item(item)}")
            elif not status:
                print(f"\n## Dropped ({len(dropped_items)})")

    else:
        # List all backlogs
        root = backlog_root()
        if not root.exists():
            print("No backlogs found.")
            return

        files = sorted(root.glob("*.md"))
        if not files:
            print("No backlogs found.")
            return

        print("# Backlogs\n")
        for f in files:
            metadata, open_items, done_items, dropped_items = parse_backlog(f)
            name = metadata.get("name", f.stem)
            desc = metadata.get("description", "")
            total = len(open_items) + len(done_items) + len(dropped_items)
            print(f"  **{name}** — {len(open_items)} open, {len(done_items)} done, {len(dropped_items)} dropped ({total} total)")
            if desc:
                print(f"    {desc}")


def _find_and_move(args, from_section: str, to_section: str):
    """Move an item between sections."""
    path = backlog_path(args.name)
    if not path.exists():
        print(f"Error: Backlog '{args.name}' not found.")
        sys.exit(1)

    metadata, open_items, done_items, dropped_items = parse_backlog(path)

    sections = {"open": open_items, "done": done_items, "dropped": dropped_items}
    source = sections[from_section]

    item_id = args.id
    item = None
    for i, it in enumerate(source):
        if it["id"] == item_id:
            item = source.pop(i)
            break

    if not item:
        # Try all sections
        for sec_name, sec_list in sections.items():
            if sec_name == from_section:
                continue
            for i, it in enumerate(sec_list):
                if it["id"] == item_id:
                    print(f"Item #{item_id} is in '{sec_name}', not '{from_section}'.")
                    sys.exit(1)
        print(f"Error: Item #{item_id} not found in backlog '{args.name}'.")
        sys.exit(1)

    today = date.today().isoformat()

    if to_section in ("done", "dropped"):
        item["closed"] = today
        item.pop("priority", None)
        if to_section == "dropped" and hasattr(args, "reason") and args.reason:
            item["text"] += f" — {args.reason}"
    elif to_section == "open":
        item["closed"] = None

    sections[to_section].append(item)

    write_backlog(path, metadata, open_items, done_items, dropped_items)
    return item


def cmd_done(args):
    """Mark an item as done."""
    item = _find_and_move(args, "open", "done")
    print(f"Done: #{item['id']} {item['text']}")


def cmd_drop(args):
    """Drop an item."""
    item = _find_and_move(args, "open", "dropped")
    print(f"Dropped: #{item['id']} {item['text']}")


def cmd_reopen(args):
    """Reopen a done or dropped item."""
    path = backlog_path(args.name)
    if not path.exists():
        print(f"Error: Backlog '{args.name}' not found.")
        sys.exit(1)

    metadata, open_items, done_items, dropped_items = parse_backlog(path)

    item = None
    item_id = args.id
    for i, it in enumerate(done_items):
        if it["id"] == item_id:
            item = done_items.pop(i)
            break
    if not item:
        for i, it in enumerate(dropped_items):
            if it["id"] == item_id:
                item = dropped_items.pop(i)
                break

    if not item:
        for it in open_items:
            if it["id"] == item_id:
                print(f"Item #{item_id} is already open.")
                sys.exit(1)
        print(f"Error: Item #{item_id} not found.")
        sys.exit(1)

    item["closed"] = None
    open_items.append(item)

    write_backlog(path, metadata, open_items, done_items, dropped_items)
    print(f"Reopened: #{item['id']} {item['text']}")


def cmd_edit(args):
    """Edit an item's text."""
    path = backlog_path(args.name)
    if not path.exists():
        print(f"Error: Backlog '{args.name}' not found.")
        sys.exit(1)

    metadata, open_items, done_items, dropped_items = parse_backlog(path)

    item_id = args.id
    found = False
    for section in [open_items, done_items, dropped_items]:
        for item in section:
            if item["id"] == item_id:
                old_text = item["text"]
                item["text"] = args.text
                found = True
                break
        if found:
            break

    if not found:
        print(f"Error: Item #{item_id} not found in backlog '{args.name}'.")
        sys.exit(1)

    write_backlog(path, metadata, open_items, done_items, dropped_items)
    print(f"Edited #{item_id}: {old_text} → {args.text}")


def cmd_prioritize(args):
    """Change an item's priority."""
    path = backlog_path(args.name)
    if not path.exists():
        print(f"Error: Backlog '{args.name}' not found.")
        sys.exit(1)

    metadata, open_items, done_items, dropped_items = parse_backlog(path)

    item_id = args.id
    found = False
    for item in open_items:
        if item["id"] == item_id:
            old_priority = item.get("priority", "none")
            item["priority"] = args.priority if args.priority != "none" else None
            found = True
            break

    if not found:
        print(f"Error: Item #{item_id} not found in open items. Only open items can be prioritized.")
        sys.exit(1)

    # Re-sort by priority
    priority_order = {"high": 0, "med": 1, "low": 2, None: 3}
    open_items.sort(key=lambda x: (priority_order.get(x.get("priority"), 3), x["id"]))

    write_backlog(path, metadata, open_items, done_items, dropped_items)
    print(f"Prioritized #{item_id}: {old_priority} → {args.priority}")


def main():
    parser = argparse.ArgumentParser(description="Backlog management")
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p = sub.add_parser("create", help="Create a new backlog")
    p.add_argument("name", help="Backlog name (used as filename)")
    p.add_argument("description", help="Short description")

    # add
    p = sub.add_parser("add", help="Add an item")
    p.add_argument("name", help="Backlog name")
    p.add_argument("item", help="Item description")
    p.add_argument("--priority", "-p", choices=["high", "med", "low"], default=None)
    p.add_argument("--notes", "-n", default=None, help="Additional notes (appended with —)")

    # list
    p = sub.add_parser("list", help="List items")
    p.add_argument("name", nargs="?", default=None, help="Backlog name (omit for all)")
    p.add_argument("--status", "-s", choices=["open", "done", "dropped"], default=None)
    p.add_argument("--all", "-a", action="store_true", help="Include done and dropped")

    # done
    p = sub.add_parser("done", help="Mark item as done")
    p.add_argument("name", help="Backlog name")
    p.add_argument("id", type=int, help="Item ID")

    # drop
    p = sub.add_parser("drop", help="Drop an item")
    p.add_argument("name", help="Backlog name")
    p.add_argument("id", type=int, help="Item ID")
    p.add_argument("reason", nargs="?", default=None, help="Reason for dropping")

    # reopen
    p = sub.add_parser("reopen", help="Reopen a done/dropped item")
    p.add_argument("name", help="Backlog name")
    p.add_argument("id", type=int, help="Item ID")

    # edit
    p = sub.add_parser("edit", help="Edit item text")
    p.add_argument("name", help="Backlog name")
    p.add_argument("id", type=int, help="Item ID")
    p.add_argument("text", help="New item text")

    # prioritize
    p = sub.add_parser("prioritize", help="Change item priority")
    p.add_argument("name", help="Backlog name")
    p.add_argument("id", type=int, help="Item ID")
    p.add_argument("priority", choices=["high", "med", "low", "none"])

    args = parser.parse_args()

    commands = {
        "create": cmd_create,
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "drop": cmd_drop,
        "reopen": cmd_reopen,
        "edit": cmd_edit,
        "prioritize": cmd_prioritize,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

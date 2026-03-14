#!/usr/bin/env python3
"""
vibe-doc - Planning document migration CLI

Manages versioned migrations for planning documents and configuration.

Usage:
    vibe-doc status              # Show current version and available upgrades
    vibe-doc upgrade             # Upgrade to latest version
    vibe-doc upgrade --dry-run   # Show what would change
    vibe-doc upgrade --to 0.2.0  # Upgrade to specific version
    vibe-doc changelog [version] # Show changelog for a version

Examples:
    vibe-doc status
    vibe-doc upgrade --dry-run
    vibe-doc upgrade
    vibe-doc changelog 0.2.0
"""

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


def get_project_dir() -> Path:
    """Get the project directory."""
    return Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')).resolve()


def get_plugin_root() -> Path:
    """Get the plugin root directory."""
    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT')
    if plugin_root:
        return Path(plugin_root).resolve()
    # Fallback: relative to this script
    return Path(__file__).parent.parent.parent.resolve()


def get_migrations_dir() -> Path:
    """Get the migrations directory."""
    return get_plugin_root() / 'migrations'


def load_manifest() -> dict:
    """Load the migrations manifest."""
    manifest_path = get_migrations_dir() / 'manifest.json'
    if not manifest_path.exists():
        return {'versions': [], 'current': '0.1.0'}
    return json.loads(manifest_path.read_text())


def get_config_path(project_dir: Path) -> Path:
    """Get path to vibe-hacker.json config file."""
    return project_dir / '.claude' / 'vibe-hacker.json'


def load_project_config(project_dir: Path) -> dict:
    """Load project configuration."""
    config_path = get_config_path(project_dir)
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def get_project_version(project_dir: Path) -> str:
    """Get the current planning version for this project."""
    config = load_project_config(project_dir)
    return config.get('planning', {}).get('version', '0.1.0')


def load_migration_module(version: str):
    """Dynamically load a migration module."""
    migrations_dir = get_migrations_dir()
    migrate_path = migrations_dir / f'v{version}' / 'migrate.py'

    if not migrate_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(f'migrate_{version}', migrate_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd_status(args):
    """Show current version and available upgrades."""
    project_dir = get_project_dir()
    manifest = load_manifest()
    current = get_project_version(project_dir)
    latest = manifest.get('current', '0.1.0')

    print(f"Project: {project_dir}")
    print(f"Current version: {current}")
    print(f"Latest version: {latest}")

    if current < latest:
        print(f"\nUpgrade available!")
        print(f"Run 'vibe-doc upgrade' to upgrade to {latest}")

        # Show versions between current and latest
        print("\nVersions to apply:")
        for v in manifest.get('versions', []):
            if v['version'] > current:
                breaking = " (BREAKING)" if v.get('breaking') else ""
                print(f"  {v['version']}: {v['description']}{breaking}")
    else:
        print("\nYou're up to date!")


def cmd_upgrade(args):
    """Upgrade to latest or specified version."""
    project_dir = get_project_dir()
    manifest = load_manifest()
    current = get_project_version(project_dir)
    target = args.to or manifest.get('current', '0.1.0')

    if current >= target:
        print(f"Already at version {current}, no upgrade needed.")
        return 0

    # Find versions to apply
    versions_to_apply = [
        v for v in manifest.get('versions', [])
        if v['version'] > current and v['version'] <= target
    ]

    if not versions_to_apply:
        print(f"No migrations to apply.")
        return 0

    # Dry run mode
    if args.dry_run:
        print("Dry run - showing what would change:\n")
        for v in versions_to_apply:
            print(f"=== Version {v['version']} ===")
            if v.get('migration'):
                module = load_migration_module(v['version'])
                if module and hasattr(module, 'dry_run'):
                    changes = module.dry_run(project_dir)
                    if changes:
                        for change in changes:
                            print(f"  - {change}")
                    else:
                        print("  No changes needed")
                else:
                    print("  Migration script not found or missing dry_run")
            else:
                print("  No migration script (metadata only)")
            print()
        return 0

    # Apply migrations
    print(f"Upgrading from {current} to {target}...\n")

    for v in versions_to_apply:
        print(f"=== Applying {v['version']} ===")

        if v.get('migration'):
            module = load_migration_module(v['version'])
            if module and hasattr(module, 'migrate'):
                success = module.migrate(project_dir)
                if not success:
                    print(f"Migration {v['version']} failed!")
                    return 1
            else:
                print(f"Warning: Migration script not found for {v['version']}")
        else:
            print("No migration needed (metadata update only)")

        print()

    print(f"Successfully upgraded to {target}!")
    return 0


def cmd_changelog(args):
    """Show changelog for a version."""
    version = args.version
    migrations_dir = get_migrations_dir()

    if version:
        changelog_path = migrations_dir / f'v{version}' / 'CHANGELOG.md'
        if changelog_path.exists():
            print(changelog_path.read_text())
        else:
            print(f"No changelog found for version {version}")
            return 1
    else:
        # Show manifest summary
        manifest = load_manifest()
        print("Available versions:\n")
        for v in manifest.get('versions', []):
            breaking = " [BREAKING]" if v.get('breaking') else ""
            print(f"  {v['version']} ({v['date']}){breaking}")
            print(f"    {v['description']}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description='Planning document migration CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # status
    status_parser = subparsers.add_parser('status', help='Show current version and available upgrades')
    status_parser.set_defaults(func=cmd_status)

    # upgrade
    upgrade_parser = subparsers.add_parser('upgrade', help='Upgrade to latest version')
    upgrade_parser.add_argument('--dry-run', '-n', action='store_true',
                                help='Show what would change without making changes')
    upgrade_parser.add_argument('--to', metavar='VERSION',
                                help='Upgrade to specific version')
    upgrade_parser.set_defaults(func=cmd_upgrade)

    # changelog
    changelog_parser = subparsers.add_parser('changelog', help='Show changelog for a version')
    changelog_parser.add_argument('version', nargs='?', help='Version to show (default: list all)')
    changelog_parser.set_defaults(func=cmd_changelog)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args) or 0


if __name__ == '__main__':
    sys.exit(main())

"""
scaffold.py — DevCrew AI Skill Vault scaffold tool.

Creates the vault folder structure safely (idempotent — never overwrites
existing files/folders).

CLI usage:
    python tools/scaffold.py [--dry-run] [--categories] [--config PATH]

Importable API:
    from tools.scaffold import scaffold_vault
    result = scaffold_vault(config, dry_run=False, categories=False)
    # result: {"created": [...], "skipped": [...]}
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional rich import — fall back to plain print gracefully
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.table import Table

    _console = Console()
    _RICH = True
except ImportError:  # pragma: no cover
    _RICH = False
    _console = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORIES: list[str] = [
    "backend-architecture",
    "security-auditing",
    "frontend-frameworks",
    "ai-orchestration",
    "devops",
    "testing",
    "data-engineering",
]

_STATUS_CREATED = "created"
_STATUS_SKIPPED = "skipped (exists)"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _print_table(rows: list[tuple[str, str]]) -> None:
    """Print a two-column status table using rich if available."""
    if _RICH:
        table = Table(title="Scaffold Results", show_header=True, header_style="bold cyan")
        table.add_column("Path", style="dim", no_wrap=True)
        table.add_column("Status")
        for path, status in rows:
            colour = "green" if status == _STATUS_CREATED else "yellow"
            table.add_row(path, f"[{colour}]{status}[/{colour}]")
        _console.print(table)
    else:
        print(f"\n{'Path':<60}  Status")
        print("-" * 75)
        for path, status in rows:
            print(f"{path:<60}  {status}")
        print()


def _ensure_dir(
    path: Path,
    dry_run: bool,
    created: list[str],
    skipped: list[str],
    rows: list[tuple[str, str]],
) -> None:
    """Create *path* if it does not exist; record outcome in lists/rows."""
    label = str(path)
    if path.exists():
        skipped.append(label)
        rows.append((label, _STATUS_SKIPPED))
    else:
        if not dry_run:
            path.mkdir(parents=True, exist_ok=True)
        created.append(label)
        prefix = "[DRY-RUN] Would create" if dry_run else "Created"
        rows.append((label, f"{prefix} directory"))


def _ensure_file(
    path: Path,
    content: str,
    dry_run: bool,
    created: list[str],
    skipped: list[str],
    rows: list[tuple[str, str]],
) -> None:
    """Write *path* with *content* if it does not already exist."""
    label = str(path)
    if path.exists():
        skipped.append(label)
        rows.append((label, _STATUS_SKIPPED))
    else:
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        created.append(label)
        prefix = "[DRY-RUN] Would create" if dry_run else "Created"
        rows.append((label, f"{prefix} file"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scaffold_vault(
    config: dict[str, Any],
    dry_run: bool = False,
    categories: bool = False,
) -> dict[str, list[str]]:
    """Create the vault folder structure idempotently.

    Args:
        config:     Loaded configuration dict (as returned by ``load_config``).
        dry_run:    If *True*, only print what would be created; touch nothing.
        categories: If *True*, also create category skeleton folders inside the
                    skills directory, each with a one-line ``README.md``.

    Returns:
        A dict with two keys:
        - ``"created"`` — list of paths that were (or would be) created.
        - ``"skipped"`` — list of paths that already existed and were left alone.
    """
    vault_cfg: dict[str, Any] = config.get("vault", {})

    skills_dir: Path = Path(vault_cfg["skills_dir"])
    quarantine_dir: Path = Path(vault_cfg["quarantine_dir"])
    staging_dir: Path = Path(vault_cfg["staging_dir"])

    created: list[str] = []
    skipped: list[str] = []
    rows: list[tuple[str, str]] = []

    # Core directories -------------------------------------------------------
    for directory in (skills_dir, quarantine_dir, staging_dir):
        _ensure_dir(directory, dry_run, created, skipped, rows)

    # Category skeleton folders (optional) -----------------------------------
    if categories:
        for cat in CATEGORIES:
            cat_dir = skills_dir / cat
            _ensure_dir(cat_dir, dry_run, created, skipped, rows)

            readme_path = cat_dir / "README.md"
            readable_name = cat.replace("-", " ")
            readme_content = (
                f"# {cat} — Placeholder category for {readable_name} skills.\n"
            )
            _ensure_file(readme_path, readme_content, dry_run, created, skipped, rows)

    # Print results ----------------------------------------------------------
    _print_table(rows)

    return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scaffold",
        description="Create the DevCrew AI Skill Vault folder structure.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without touching the filesystem.",
    )
    parser.add_argument(
        "--categories",
        action="store_true",
        help="Also create category skeleton folders with placeholder README.md files.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to devcrew.config.yaml (default: auto-detect by walking up from cwd).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0 = success, non-zero = error)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Import here to avoid circular imports when used as a library
    try:
        from tools.config import find_config_file, load_config  # type: ignore[import]
    except ImportError:
        try:
            # Allow running from the project root: python tools/scaffold.py
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from tools.config import find_config_file, load_config  # type: ignore[import]
        except ImportError as exc:
            print(f"ERROR: Could not import tools.config — {exc}", file=sys.stderr)
            return 1

    try:
        config_path: Path | None = Path(args.config) if args.config else None
        config: dict[str, Any] = load_config(config_path)
    except FileNotFoundError as exc:
        print(f"ERROR: Config file not found — {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to load config — {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("[DRY-RUN] No files or directories will be created.\n")

    try:
        result = scaffold_vault(config, dry_run=args.dry_run, categories=args.categories)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Scaffold failed — {exc}", file=sys.stderr)
        return 1

    n_created = len(result["created"])
    n_skipped = len(result["skipped"])
    suffix = " (dry-run)" if args.dry_run else ""
    print(f"Done{suffix}: {n_created} created, {n_skipped} already existed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
sync_skills.py — DevCrew AI Skill Vault skill synchronisation tool.

Syncs skills from configured remote sources into the local vault.

CLI usage:
    python tools/sync_skills.py [--source NAME] [--dry-run] [--force]
                                 [--prune] [--config PATH]

Importable API:
    from tools.sync_skills import sync_sources
    summary = sync_sources(config, source_filter=None, dry_run=False,
                           force=False, prune=False)
    # summary: {source_name: {added, updated, unchanged, skipped, quarantined}}
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
import tempfile
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
# Local imports (resolved at call time to support both module and script use)
# ---------------------------------------------------------------------------


def _import_tools() -> tuple[Any, Any, Any, Any, Any]:
    """Import and return (load_config, find_config_file, content_sha256, slugify,
    shallow_clone, download_zip, git_available) lazily.

    Supports running as ``python tools/sync_skills.py`` from the project root.
    """
    import importlib

    try:
        cfg_mod = importlib.import_module("tools.config")
        parse_mod = importlib.import_module("tools.parsing")
        git_mod = importlib.import_module("tools.git_ops")
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        cfg_mod = importlib.import_module("tools.config")
        parse_mod = importlib.import_module("tools.parsing")
        git_mod = importlib.import_module("tools.git_ops")

    return (
        cfg_mod.load_config,
        cfg_mod.find_config_file,
        parse_mod.content_sha256,
        parse_mod.slugify,
        git_mod,
    )


# ---------------------------------------------------------------------------
# .source.json helpers
# ---------------------------------------------------------------------------

_SOURCE_JSON_NAME = ".source.json"


def write_source_json(
    skill_dest: Path,
    *,
    source_name: str,
    repo_url: str,
    ref: str,
    commit_sha: str,
    upstream_path: str,
    license_id: str,
    sha256: str,
) -> None:
    """Write a ``.source.json`` provenance file into *skill_dest*.

    Args:
        skill_dest:    Destination skill directory (must exist).
        source_name:   Name of the configured source.
        repo_url:      Remote repository URL.
        ref:           Branch/tag that was checked out.
        commit_sha:    Commit SHA of the upstream source.
        upstream_path: Relative path of the skill inside the upstream repo.
        license_id:    SPDX license identifier (or ``"UNKNOWN"``).
        sha256:        Content SHA-256 of the skill folder.
    """
    payload: dict[str, str] = {
        "source_name": source_name,
        "repo_url": repo_url,
        "ref": ref,
        "commit_sha": commit_sha,
        "upstream_path": upstream_path,
        "license": license_id,
        "synced_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "content_sha256": sha256,
    }
    dest_file = skill_dest / _SOURCE_JSON_NAME
    dest_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_source_json(skill_dir: Path) -> dict[str, str] | None:
    """Read and parse ``.source.json`` from *skill_dir*, or return *None*."""
    path = skill_dir / _SOURCE_JSON_NAME
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# License detection
# ---------------------------------------------------------------------------

_KNOWN_LICENSE_FILENAMES: list[str] = [
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    "LICENCE",
    "LICENCE.txt",
    "COPYING",
    "LICENSE-MIT",
    "LICENSE-CC-BY-SA-4.0",
]

_SPDX_SIGNATURES: list[tuple[str, str]] = [
    ("Mozilla Public License", "MPL-2.0"),
    ("MIT License", "MIT"),
    ("MIT licence", "MIT"),
    ("Permission is hereby granted, free of charge", "MIT"),
    ("Apache License", "Apache-2.0"),
    ("GNU General Public License", "GPL"),
    ("GNU GENERAL PUBLIC LICENSE", "GPL"),
    ("GNU Lesser General Public License", "LGPL"),
    ("BSD 2-Clause", "BSD-2-Clause"),
    ("BSD 3-Clause", "BSD-3-Clause"),
    ("ISC License", "ISC"),
    ("Attribution-ShareAlike 4.0", "CC-BY-SA-4.0"),
    ("CC-BY-SA-4.0", "CC-BY-SA-4.0"),
    ("CC-BY-SA", "CC-BY-SA-4.0"),
    ("Attribution 4.0", "CC-BY-4.0"),
    ("CC-BY-4.0", "CC-BY-4.0"),
    ("Creative Commons", "CC"),
    ("The Unlicense", "Unlicense"),
    ("CC0", "CC0-1.0"),
]


def detect_license(skill_dir: Path, repo_root: Path) -> str:
    """Detect the SPDX license identifier for a skill.

    Searches for a LICENSE file first inside *skill_dir*, then at *repo_root*.

    Args:
        skill_dir: Directory containing the skill files.
        repo_root: Root directory of the cloned repository.

    Returns:
        An SPDX license identifier string (e.g. ``"MIT"``), or
        ``"UNKNOWN"`` when no licence file is found or the content is
        unrecognised.
    """
    for search_root in (skill_dir, repo_root):
        for name in _KNOWN_LICENSE_FILENAMES:
            candidate = search_root / name
            if candidate.is_file():
                try:
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for signature, spdx in _SPDX_SIGNATURES:
                    if signature in text:
                        return spdx
                # File exists but content is unrecognised
                return "UNKNOWN"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------


def discover_skills(staging_repo: Path, skills_glob: str) -> list[Path]:
    """Return a list of skill *directories* found via *skills_glob*.

    Args:
        staging_repo: Root of the cloned/fetched repository.
        skills_glob:  Glob pattern for SKILL.md files relative to *staging_repo*
                      (e.g. ``"skills/*/SKILL.md"``). Use ``"**/**/SKILL.md"``
                      for recursive discovery across any layout.

    Returns:
        Sorted list of unique parent directories that contain a ``SKILL.md``.
    """
    # Normalize the glob: if it's the catch-all pattern use rglob
    if "**" in skills_glob:
        matches: list[Path] = sorted(
            {p.parent for p in staging_repo.rglob("SKILL.md") if p.is_file()}
        )
    else:
        matches = sorted(
            {p.parent for p in staging_repo.glob(skills_glob) if p.is_file()}
        )
    return matches


# ---------------------------------------------------------------------------
# Atomic copy
# ---------------------------------------------------------------------------


def atomic_copy_skill(src: Path, dest: Path) -> None:
    """Copy the entire *src* skill directory to *dest* atomically.

    Uses a temporary sibling directory followed by an atomic rename so that
    *dest* is never left in a partial state.  Any existing *dest* is replaced.
    Files that cannot be copied due to Windows Unicode path restrictions are
    silently skipped (they will not affect the SKILL.md content).

    Args:
        src:  Source skill directory (must exist).
        dest: Final destination path.

    Raises:
        RuntimeError: On filesystem errors during the copy.
    """
    tmp_path = dest.parent / f".tmp_{dest.name}_{id(src)}"
    if tmp_path.exists():
        shutil.rmtree(tmp_path)

    def _ignore_errors(src_name: str, names: list[str]) -> list[str]:
        """Return names to ignore during copytree (unreadable on Windows)."""
        ignored = [n for n in (".git", "__pycache__", ".pytest_cache") if n in names]
        for name in names:
            if name in ignored:
                continue
            try:
                # Test that we can form the path without error
                Path(src_name) / name
            except (ValueError, OSError):
                ignored.append(name)
        return ignored

    try:
        shutil.copytree(src, tmp_path, ignore=_ignore_errors)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(tmp_path), str(dest))
    except OSError as exc:
        # Clean up on failure
        if tmp_path.exists():
            shutil.rmtree(tmp_path, ignore_errors=True)
        raise RuntimeError(f"Failed to copy skill {src} → {dest}: {exc}") from exc


# ---------------------------------------------------------------------------
# Per-source sync logic
# ---------------------------------------------------------------------------


def _sync_one_source(
    source_cfg: dict[str, Any],
    config: dict[str, Any],
    staging_base: Path,
    skills_dir: Path,
    quarantine_dir: Path,
    dry_run: bool,
    force: bool,
    content_sha256_fn: Any,
    slugify_fn: Any,
    git_mod: Any,
) -> dict[str, Any]:
    """Sync a single configured source.

    Returns a counts dict:
    ``{added, updated, unchanged, skipped, quarantined, warnings}``.
    """
    counts: dict[str, Any] = {
        "added": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "quarantined": 0,
        "warnings": [],
    }

    source_name: str = source_cfg["name"]
    repo_url: str = source_cfg["url"]
    ref: str = source_cfg.get("ref", "main")
    skills_glob: str = source_cfg.get("skills_glob", "**/**/SKILL.md")

    allowed_licenses: list[str] = config.get("allowed_licenses", [])
    on_unknown_license: str = config.get("on_unknown_license", "quarantine")
    on_slug_collision: str = config.get("on_slug_collision", "namespace")

    staging_repo = staging_base / source_name

    # 1. Clone / fetch the source repo -----------------------------------------
    commit_sha = "UNKNOWN"
    sparse_dirs: list[str] | None = source_cfg.get("sparse") or None
    if git_mod.git_available():
        try:
            if sparse_dirs and hasattr(git_mod, "shallow_sparse_clone"):
                commit_sha = git_mod.shallow_sparse_clone(
                    repo_url, staging_repo, ref=ref, sparse_dirs=sparse_dirs
                )
            else:
                commit_sha = git_mod.shallow_clone(repo_url, staging_repo, ref=ref)
        except RuntimeError as exc:
            counts["warnings"].append(f"git clone/fetch failed: {exc}")
            # Attempt zip fallback
            try:
                git_mod.download_zip(repo_url, staging_repo, ref=ref)
            except RuntimeError as exc2:
                raise RuntimeError(
                    f"[{source_name}] Both git clone and zip download failed: {exc2}"
                ) from exc2
    else:
        try:
            git_mod.download_zip(repo_url, staging_repo, ref=ref)
        except RuntimeError as exc:
            raise RuntimeError(
                f"[{source_name}] git not available and zip download failed: {exc}"
            ) from exc

    if staging_repo.is_dir() and git_mod.git_available():
        try:
            commit_sha = git_mod.get_commit_sha(staging_repo)
        except RuntimeError:
            pass  # keep "UNKNOWN"

    # 2. Discover skills -------------------------------------------------------
    skill_dirs = discover_skills(staging_repo, skills_glob)

    # Build a mapping of slug → existing vault source for collision detection
    existing_slugs: dict[str, str] = {}  # slug → source_name
    for d in skills_dir.iterdir() if skills_dir.is_dir() else []:
        if d.is_dir():
            meta = read_source_json(d)
            if meta:
                existing_slugs[d.name] = meta.get("source_name", "")

    # 3. Process each discovered skill -----------------------------------------
    for skill_dir in skill_dirs:
        try:
            _process_one_skill(
                skill_dir=skill_dir,
                source_name=source_name,
                repo_url=repo_url,
                ref=ref,
                commit_sha=commit_sha,
                staging_repo=staging_repo,
                skills_dir=skills_dir,
                quarantine_dir=quarantine_dir,
                existing_slugs=existing_slugs,
                allowed_licenses=allowed_licenses,
                on_unknown_license=on_unknown_license,
                on_slug_collision=on_slug_collision,
                dry_run=dry_run,
                force=force,
                counts=counts,
                content_sha256_fn=content_sha256_fn,
                slugify_fn=slugify_fn,
            )
        except Exception as exc:  # noqa: BLE001
            counts["warnings"].append(
                f"Skipped skill '{skill_dir.name}': {exc}"
            )
            counts["skipped"] += 1

    return counts


def _process_one_skill(
    *,
    skill_dir: Path,
    source_name: str,
    repo_url: str,
    ref: str,
    commit_sha: str,
    staging_repo: Path,
    skills_dir: Path,
    quarantine_dir: Path,
    existing_slugs: dict,
    allowed_licenses: list,
    on_unknown_license: str,
    on_slug_collision: str,
    dry_run: bool,
    force: bool,
    counts: dict,
    content_sha256_fn: Any,
    slugify_fn: Any,
) -> None:
    """Process a single skill directory — licence gate, SHA check, copy."""
    raw_slug = slugify_fn(skill_dir.name)

    # Collision handling
    slug = raw_slug
    if slug in existing_slugs and existing_slugs[slug] != source_name:
        if on_slug_collision == "namespace":
            slug = f"{source_name}--{raw_slug}"
            counts["warnings"].append(
                f"Slug collision for '{raw_slug}' — namespaced to '{slug}'"
            )
        elif on_slug_collision == "skip":
            counts["skipped"] += 1
            counts["warnings"].append(
                f"Slug collision for '{raw_slug}' — skipped (policy=skip)"
            )
            return
        # else: "overwrite" — keep raw slug

    # License check
    license_id = detect_license(skill_dir, staging_repo)

    if license_id == "UNKNOWN" or (
        allowed_licenses and license_id not in allowed_licenses
    ):
        if on_unknown_license == "quarantine":
            if not dry_run:
                q_dest = quarantine_dir / slug
                atomic_copy_skill(skill_dir, q_dest)
                write_source_json(
                    q_dest,
                    source_name=source_name,
                    repo_url=repo_url,
                    ref=ref,
                    commit_sha=commit_sha,
                    upstream_path=str(skill_dir.relative_to(staging_repo)),
                    license_id=license_id,
                    sha256=content_sha256_fn(skill_dir),
                )
            counts["quarantined"] += 1
            return
        elif on_unknown_license == "skip":
            counts["skipped"] += 1
            return
        # else "allow" — fall through

    # Content SHA check
    upstream_sha = content_sha256_fn(skill_dir)
    vault_dest = skills_dir / slug
    existing_meta = read_source_json(vault_dest) if vault_dest.exists() else None

    if (
        existing_meta
        and existing_meta.get("content_sha256") == upstream_sha
        and not force
    ):
        counts["unchanged"] += 1
        return

    is_update = vault_dest.exists()

    if not dry_run:
        atomic_copy_skill(skill_dir, vault_dest)
        write_source_json(
            vault_dest,
            source_name=source_name,
            repo_url=repo_url,
            ref=ref,
            commit_sha=commit_sha,
            upstream_path=str(skill_dir.relative_to(staging_repo)),
            license_id=license_id,
            sha256=upstream_sha,
        )

    if is_update:
        counts["updated"] += 1
    else:
        counts["added"] += 1
    existing_slugs[slug] = source_name


# ---------------------------------------------------------------------------
# Prune logic
# ---------------------------------------------------------------------------


def _prune_vault(
    skills_dir: Path,
    source_name_to_upstream_slugs: dict[str, set[str]],
    dry_run: bool,
) -> list[str]:
    """Remove vault skills that no longer exist upstream.

    Asks for confirmation (unless *dry_run*). Returns list of pruned slugs.
    """
    to_prune: list[tuple[str, Path]] = []  # (slug, path)

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue
        meta = read_source_json(skill_path)
        if not meta:
            continue
        src_name = meta.get("source_name", "")
        upstream_slugs = source_name_to_upstream_slugs.get(src_name, set())
        if skill_path.name not in upstream_slugs:
            to_prune.append((skill_path.name, skill_path))

    if not to_prune:
        return []

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Skills to prune ({len(to_prune)}):")
    for slug, _ in to_prune:
        print(f"  - {slug}")

    if dry_run:
        return [slug for slug, _ in to_prune]

    answer = input("\nProceed with pruning? [y/N] ").strip().lower()
    if answer != "y":
        print("Prune aborted.")
        return []

    pruned: list[str] = []
    for slug, path in to_prune:
        shutil.rmtree(path)
        pruned.append(slug)
        print(f"  Removed: {slug}")
    return pruned


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sync_sources(
    config: dict[str, Any],
    source_filter: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    prune: bool = False,
) -> dict[str, dict[str, Any]]:
    """Sync skills from all configured sources (or a single one) into the vault.

    Args:
        config:        Loaded configuration dict (as returned by ``load_config``).
        source_filter: If given, only the source with this name is processed.
        dry_run:       If *True*, simulate all actions without touching the vault.
        force:         Re-copy skills even when the content SHA is unchanged.
        prune:         After syncing, prompt to remove skills absent from upstream.

    Returns:
        A dict keyed by source name, each value being a counts dict with keys:
        ``added``, ``updated``, ``unchanged``, ``skipped``, ``quarantined``,
        ``warnings`` (list of warning strings).

    Raises:
        ValueError: If *source_filter* does not match any configured source.
    """
    # Lazy imports so the module is importable without tools/ on sys.path
    _, _, content_sha256_fn, slugify_fn, git_mod = _import_tools()

    vault_cfg: dict[str, Any] = config.get("vault", {})
    skills_dir: Path = Path(vault_cfg["skills_dir"])
    quarantine_dir: Path = Path(vault_cfg["quarantine_dir"])
    staging_dir: Path = Path(vault_cfg["staging_dir"])

    sources: list[dict[str, Any]] = config.get("sources", [])

    if source_filter:
        matched = [s for s in sources if s["name"] == source_filter]
        if not matched:
            known = ", ".join(s["name"] for s in sources)
            raise ValueError(
                f"No configured source named {source_filter!r}. Known: {known}"
            )
        sources = matched

    if not dry_run:
        for d in (skills_dir, quarantine_dir, staging_dir):
            d.mkdir(parents=True, exist_ok=True)

    summary: dict[str, dict[str, Any]] = {}
    source_name_to_upstream_slugs: dict[str, set[str]] = {}

    for source_cfg in sources:
        source_name: str = source_cfg["name"]
        try:
            counts = _sync_one_source(
                source_cfg=source_cfg,
                config=config,
                staging_base=staging_dir,
                skills_dir=skills_dir,
                quarantine_dir=quarantine_dir,
                dry_run=dry_run,
                force=force,
                content_sha256_fn=content_sha256_fn,
                slugify_fn=slugify_fn,
                git_mod=git_mod,
            )
            summary[source_name] = counts

            # Track upstream slugs for prune logic
            staging_repo = staging_dir / source_name
            skills_glob = source_cfg.get("skills_glob", "**/**/SKILL.md")
            skill_dirs = discover_skills(staging_repo, skills_glob)
            source_name_to_upstream_slugs[source_name] = {
                slugify_fn(d.name) for d in skill_dirs
            }

        except RuntimeError as exc:
            msg = f"[{source_name}] ERROR: {exc}"
            if _RICH:
                _console.print(f"[bold red]{msg}[/bold red]")
            else:
                print(msg, file=sys.stderr)
            summary[source_name] = {
                "added": 0,
                "updated": 0,
                "unchanged": 0,
                "skipped": 0,
                "quarantined": 0,
                "warnings": [str(exc)],
                "error": True,
            }

    # Prune -------------------------------------------------------------------
    if prune:
        _prune_vault(skills_dir, source_name_to_upstream_slugs, dry_run=dry_run)

    # Print summary table -----------------------------------------------------
    _print_summary(summary, dry_run=dry_run)

    return summary


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _print_summary(
    summary: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> None:
    """Print a per-source summary table."""
    suffix = " (DRY-RUN)" if dry_run else ""

    if _RICH:
        table = Table(
            title=f"Sync Summary{suffix}",
            show_header=True,
            header_style="bold cyan",
        )
        for col in ("Source", "Added", "Updated", "Unchanged", "Skipped", "Quarantined"):
            table.add_column(col)
        for src, counts in summary.items():
            has_error = counts.get("error", False)
            style = "red" if has_error else ""
            table.add_row(
                src,
                str(counts.get("added", 0)),
                str(counts.get("updated", 0)),
                str(counts.get("unchanged", 0)),
                str(counts.get("skipped", 0)),
                str(counts.get("quarantined", 0)),
                style=style,
            )
        _console.print(table)
        for src, counts in summary.items():
            for w in counts.get("warnings", []):
                _console.print(f"  [yellow]⚠ [{src}] {w}[/yellow]")
    else:
        print(f"\nSync Summary{suffix}")
        header = f"{'Source':<30} {'Added':>6} {'Updated':>8} {'Unchanged':>10} {'Skipped':>8} {'Quarantined':>12}"
        print(header)
        print("-" * len(header))
        for src, counts in summary.items():
            print(
                f"{src:<30} {counts.get('added', 0):>6} {counts.get('updated', 0):>8} "
                f"{counts.get('unchanged', 0):>10} {counts.get('skipped', 0):>8} "
                f"{counts.get('quarantined', 0):>12}"
            )
        for src, counts in summary.items():
            for w in counts.get("warnings", []):
                print(f"  WARNING [{src}]: {w}")
        print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync_skills",
        description="Sync skills from configured remote sources into the DevCrew Vault.",
    )
    parser.add_argument(
        "--source",
        metavar="NAME",
        default=None,
        help="Sync only this source (by name). Defaults to all configured sources.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the sync without writing any files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-copy skills even when their content SHA is unchanged.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="After syncing, prompt to remove vault skills absent from upstream.",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Print and save coverage-report.md showing selected/target per module.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to devcrew.config.yaml (default: auto-detect).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0 = success, non-zero = error)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    load_config, find_config_file, *_ = _import_tools()

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
        print("[DRY-RUN] No files will be written.\n")

    # Handle --coverage (standalone: generate report without re-syncing)
    if hasattr(args, "coverage") and args.coverage:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from tools.catalog import generate_coverage_report  # type: ignore
            report_path = generate_coverage_report(config)
            print(f"Coverage report written to: {report_path}")
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: Could not generate coverage report — {exc}", file=sys.stderr)
        return 0

    try:
        sync_sources(
            config,
            source_filter=args.source,
            dry_run=args.dry_run,
            force=args.force,
            prune=args.prune,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Unexpected failure — {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

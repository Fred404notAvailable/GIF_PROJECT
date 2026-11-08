"""
watcher.py — DevCrew AI Skill Vault
=====================================
Real-time file watcher that keeps the SQLite FTS5 registry in sync with the
skills directory.

CLI:
    python tools/watcher.py run               # start watching (blocks)
    python tools/watcher.py scan              # one-shot reindex, then exit
    python tools/watcher.py search "<query>"  # FTS5 search
    python tools/watcher.py list              # list all skills in DB
    python tools/watcher.py show <slug>       # show one skill's details
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ensure tools/ is on the path
# ---------------------------------------------------------------------------
_TOOLS_DIR = Path(__file__).parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from config import load_config  # noqa: E402
from db import (  # noqa: E402
    delete_skill,
    get_connection,
    get_skill,
    init_db,
    list_skills,
    search_skills,
    upsert_skill,
)
from parsing import content_sha256  # noqa: E402
from validate_skills import ValidationResult, validate_skill  # noqa: E402
from catalog import cmd_modules, cmd_module  # noqa: E402

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler  # type: ignore
    from watchdog.observers import Observer  # type: ignore
except ImportError as _exc:  # pragma: no cover
    raise SystemExit(
        "watchdog is required: pip install watchdog"
    ) from _exc

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("devcrew.watcher")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug_from_path(path: Path, skills_dir: Path) -> str | None:
    """
    Resolve the owning skill slug from any path inside the skills directory.

    For example ``skills/my-skill/scripts/foo.py`` → ``"my-skill"``.
    Returns *None* if the path is not inside *skills_dir*.
    """
    try:
        relative = path.relative_to(skills_dir)
    except ValueError:
        return None
    parts = relative.parts
    if not parts:
        return None
    return parts[0]


def _should_ignore(path: Path, ignore_patterns: list[str]) -> bool:
    """Return *True* if the path matches any of the ignore glob patterns or Obsidian files."""
    if ".obsidian" in path.parts:
        return True
    name = path.name
    for pattern in ignore_patterns:
        if name == pattern or pattern in path.parts:
            return True
        # Extension/suffix patterns (e.g. .swp, .tmp, ~)
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True
        if pattern.endswith("*") and name.startswith(pattern[:-1]):
            return True
        if pattern.startswith(".") and name.endswith(pattern):
            return True
        if pattern.endswith("~") and name.endswith("~"):
            return True
    return False


def _build_skill_record(
    slug: str,
    skill_path: Path,
    result: ValidationResult,
    sha: str,
) -> dict[str, Any]:
    """Build a dict suitable for :func:`db.upsert_skill`."""
    import json as _json
    skill_md = skill_path / "SKILL.md"
    name = slug
    description = ""
    license_val = ""
    fm_lic = ""
    body = ""
    frontmatter_json = "{}"
    source_name = ""
    commit_sha = ""

    if skill_md.exists():
        try:
            from parsing import parse_skill_md  # local import to avoid circularity

            fm, body = parse_skill_md(skill_md)
            name = fm.get("name", slug)
            description = fm.get("description", "")
            fm_lic = fm.get("license", "")
            frontmatter_json = _json.dumps(fm, ensure_ascii=False, default=str)
        except (ValueError, OSError):
            fm_lic = ""

    # License resolution order:
    # 1. Skill folder's own LICENSE* file
    # 2. Frontmatter license (if not pointer text like 'Complete terms in...')
    # 3. .source.json (repo-level license)
    try:
        from sync_skills import detect_license
        folder_lic = detect_license(skill_path, skill_path)
        if folder_lic and folder_lic != "UNKNOWN":
            license_val = folder_lic
    except Exception:
        pass

    if not license_val and fm_lic:
        if "complete terms" not in fm_lic.lower() and "license.txt" not in fm_lic.lower():
            license_val = fm_lic

    # Read provenance from .source.json if present
    source_json_path = skill_path / ".source.json"
    if source_json_path.exists():
        try:
            source_data = _json.loads(source_json_path.read_text(encoding="utf-8"))
            source_name = source_data.get("source_name", "")
            commit_sha = source_data.get("commit_sha", "")
            if not license_val:
                license_val = source_data.get("license", "")
        except (ValueError, OSError):
            pass

    return {
        "slug": slug,
        "name": name,
        "description": description,
        "body": body,
        "frontmatter_json": frontmatter_json,
        "license": license_val,
        "source_name": source_name,
        "commit_sha": commit_sha,
        "path": str(skill_path),
        "content_sha256": sha,
        "validation_status": result.status,
        "validation_messages": _json.dumps(result.errors + result.warnings),
        "has_scripts": int((skill_path / "scripts").is_dir()),
        "has_references": int((skill_path / "references").is_dir()),
        "has_assets": int((skill_path / "assets").is_dir()),
    }


# ---------------------------------------------------------------------------
# Debouncer
# ---------------------------------------------------------------------------


class Debouncer:
    """
    Per-slug debounce: collapses multiple rapid events into a single callback
    after *delay_ms* milliseconds of silence.

    Thread-safe.
    """

    def __init__(self, delay_ms: int, callback: Any) -> None:
        self._delay = delay_ms / 1000.0
        self._callback = callback
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def trigger(self, slug: str, *args: Any, **kwargs: Any) -> None:
        """Schedule (or reschedule) a debounced call for *slug*."""
        with self._lock:
            existing = self._timers.get(slug)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(
                self._delay, self._fire, args=(slug,) + args, kwargs=kwargs
            )
            self._timers[slug] = timer
            timer.daemon = True
            timer.start()

    def _fire(self, slug: str, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            self._timers.pop(slug, None)
        self._callback(slug, *args, **kwargs)

    def flush(self) -> None:
        """Cancel all pending timers (call on shutdown)."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------


class Indexer:
    """
    Validates and indexes a skill folder into SQLite.

    Uses a threading.Lock to serialise DB writes.
    Tracks the last-known SHA256 to skip no-op writes.
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._db_lock = threading.Lock()
        self._sha_cache: dict[str, str] = {}
        vault_cfg = config.get("vault", {})
        self._db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/vault.db"))
        self._conn = get_connection(self._db_path)
        init_db(self._conn)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def index_skill(self, slug: str, skill_path: Path, force: bool = False) -> None:
        """
        Validate *skill_path* and upsert the result into the DB.

        Skips the DB write if the content SHA256 is unchanged (unless *force*).
        """
        if not skill_path.exists():
            log.warning("index_skill called on non-existent path: %s", skill_path)
            return

        try:
            sha = content_sha256(skill_path)
        except OSError as exc:
            log.error("[%s] Could not compute SHA256: %s", slug, exc)
            return

        cached_sha = self._sha_cache.get(slug)
        if not force and sha == cached_sha:
            log.debug("[%s] Content unchanged — skipping DB write", slug)
            return

        try:
            result = validate_skill(skill_path, self._config, fix=False)
        except Exception as exc:  # noqa: BLE001
            log.error("[%s] Validation raised unexpected error: %s", slug, exc)
            result = ValidationResult(slug=slug, status="invalid")
            result.errors.append(str(exc))

        record = _build_skill_record(slug, skill_path, result, sha)

        with self._db_lock:
            upsert_skill(self._conn, record)
            # Sync skill_modules table
            try:
                from catalog import sync_skill_modules, load_catalog  # lazy import
                catalog = load_catalog(self._config)
                sync_skill_modules(slug, record, self._conn, catalog, deleted=False)
            except Exception as exc:  # noqa: BLE001
                log.debug("[%s] skill_modules sync skipped: %s", slug, exc)

        self._sha_cache[slug] = sha
        log.info(
            "[%s] Indexed — status=%s errors=%d warnings=%d",
            slug,
            result.status,
            len(result.errors),
            len(result.warnings),
        )

    def remove_skill(self, slug: str) -> None:
        """Remove a skill row from the DB."""
        with self._db_lock:
            delete_skill(self._conn, slug)
            try:
                from catalog import sync_skill_modules, load_catalog  # lazy import
                catalog = load_catalog(self._config)
                sync_skill_modules(slug, {}, self._conn, catalog, deleted=True)
            except Exception as exc:  # noqa: BLE001
                log.debug("[%s] skill_modules cleanup skipped: %s", slug, exc)
        self._sha_cache.pop(slug, None)
        log.info("[%s] Removed from index", slug)

    def reconcile(self, skills_dir: Path) -> None:
        """
        Full vault scan:

        * Upsert every skill folder present on disk.
        * Remove DB rows whose paths no longer exist.
        """
        log.info("Starting reconciliation scan of %s", skills_dir)

        on_disk: set[str] = set()
        if skills_dir.exists():
            for skill_path in sorted(skills_dir.iterdir()):
                if skill_path.is_dir():
                    slug = skill_path.name
                    on_disk.add(slug)
                    self.index_skill(slug, skill_path, force=True)

        with self._db_lock:
            in_db = {row["slug"] for row in list_skills(self._conn)}

        stale = in_db - on_disk
        for slug in stale:
            log.info("[%s] No longer on disk — removing from DB", slug)
            self.remove_skill(slug)

        log.info(
            "Reconciliation complete: %d on-disk, %d removed",
            len(on_disk),
            len(stale),
        )

    def close(self) -> None:
        """Close the underlying DB connection."""
        with self._db_lock:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# File-system event handler
# ---------------------------------------------------------------------------


class SkillEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler for the skills directory.

    Delegates to :class:`Debouncer` → :class:`Indexer`.
    """

    def __init__(
        self,
        skills_dir: Path,
        indexer: Indexer,
        debouncer: Debouncer,
        config: dict,
    ) -> None:
        super().__init__()
        self._skills_dir = skills_dir
        self._indexer = indexer
        self._debouncer = debouncer
        self._config = config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ignore_patterns(self) -> list[str]:
        return self._config.get("watcher", {}).get(
            "ignore_patterns",
            [".swp", "~", ".DS_Store", ".tmp", "__pycache__"],
        )

    def _handle_path(self, raw_path: str, event_type: str, is_directory: bool = False) -> None:
        path = Path(raw_path)

        if _should_ignore(path, self._ignore_patterns()):
            log.debug("Ignoring %s event for %s", event_type, path)
            return

        slug = _slug_from_path(path, self._skills_dir)
        if slug is None:
            return

        skill_path = self._skills_dir / slug
        log.debug(
            "Event=%s path=%s → skill=%s", event_type, path, slug
        )
        self._debouncer.trigger(slug, skill_path, event_type)

    # ------------------------------------------------------------------
    # watchdog callbacks
    # ------------------------------------------------------------------

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_path(event.src_path, "created", event.is_directory)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle_path(event.src_path, "modified", event.is_directory)

    def on_deleted(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)

        if _should_ignore(path, self._ignore_patterns()):
            return

        slug = _slug_from_path(path, self._skills_dir)
        if slug is None:
            return

        skill_path = self._skills_dir / slug

        # If SKILL.md itself (or the entire skill folder) was deleted → remove
        if not skill_path.exists() or path.name == "SKILL.md":
            self._debouncer.trigger(slug, skill_path, "deleted")
        else:
            # A sub-file was deleted; re-index the skill
            self._debouncer.trigger(slug, skill_path, "modified")

    def on_moved(self, event: FileSystemEvent) -> None:
        # Handle source (treat as delete)
        self._handle_path(event.src_path, "moved_from", event.is_directory)
        # Handle destination (treat as create/update)
        self._handle_path(event.dest_path, "moved_to", event.is_directory)


# ---------------------------------------------------------------------------
# Debounce callback
# ---------------------------------------------------------------------------


def _make_debounce_callback(indexer: Indexer, skills_dir: Path):
    """Return the callback invoked after debounce settling."""

    def _callback(slug: str, skill_path: Path, event_type: str) -> None:
        if event_type == "deleted" and not skill_path.exists():
            indexer.remove_skill(slug)
        else:
            if skill_path.exists():
                indexer.index_skill(slug, skill_path)
            else:
                indexer.remove_skill(slug)

    return _callback


# ---------------------------------------------------------------------------
# Config-file watcher (reload on change)
# ---------------------------------------------------------------------------


class ConfigReloadHandler(FileSystemEventHandler):
    """Watch the config file and reload it on changes."""

    def __init__(self, config_path: Path, state: dict) -> None:
        super().__init__()
        self._config_path = config_path
        self._state = state  # mutable dict shared with caller

    def on_modified(self, event: FileSystemEvent) -> None:
        if Path(event.src_path).resolve() == self._config_path.resolve():
            log.info("Config file changed — reloading %s", self._config_path)
            try:
                new_config = load_config(self._config_path)
                self._state["config"] = new_config
                log.info("Config reloaded successfully")
            except Exception as exc:  # noqa: BLE001
                log.error("Failed to reload config: %s", exc)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_run(config: dict, config_path: Path | None) -> None:
    """Start the file watcher (blocks until SIGINT/SIGTERM)."""
    vault_cfg = config.get("vault", {})
    skills_dir = Path(vault_cfg.get("skills_dir", "DevCrew-Vault/skills"))
    debounce_ms = int(config.get("watcher", {}).get("debounce_ms", 500))

    indexer = Indexer(config)
    indexer.reconcile(skills_dir)

    # Shared mutable config state (for config-reload support)
    state: dict[str, Any] = {"config": config}

    def _debounce_callback(slug: str, skill_path: Path, event_type: str) -> None:
        # Always read from the latest config state
        cur_config = state["config"]
        indexer._config = cur_config  # noqa: SLF001  — intentional update
        _make_debounce_callback(indexer, skills_dir)(slug, skill_path, event_type)

    debouncer = Debouncer(delay_ms=debounce_ms, callback=_debounce_callback)
    event_handler = SkillEventHandler(skills_dir, indexer, debouncer, config)

    observer = Observer()
    observer.schedule(event_handler, str(skills_dir), recursive=True)

    mcp_dir = vault_cfg.get("mcp_dir")
    mcp_path = Path(mcp_dir) if mcp_dir else skills_dir.parent / "mcp"
    if mcp_path.exists():
        observer.schedule(event_handler, str(mcp_path), recursive=True)
        log.info("Watching MCP notes: %s", mcp_path)

    # Optionally watch config file
    if config_path is not None and config_path.exists():
        config_handler = ConfigReloadHandler(config_path, state)
        observer.schedule(config_handler, str(config_path.parent), recursive=False)
        log.info("Watching config: %s", config_path)

    observer.start()
    log.info("Watcher started — monitoring %s", skills_dir)

    # Graceful shutdown
    _shutdown = threading.Event()

    def _handle_signal(signum: int, _frame: Any) -> None:
        log.info("Signal %d received — shutting down…", signum)
        _shutdown.set()

    signal.signal(signal.SIGINT, _handle_signal)
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
    except (OSError, ValueError):
        pass  # SIGTERM not available on Windows in some environments

    try:
        while not _shutdown.is_set():
            time.sleep(0.5)
    finally:
        log.info("Flushing pending debounce events…")
        debouncer.flush()
        observer.stop()
        observer.join()
        indexer.close()
        log.info("Watcher stopped cleanly")


def cmd_scan(config: dict) -> None:
    """One-shot: reindex the entire vault, then exit."""
    vault_cfg = config.get("vault", {})
    skills_dir = Path(vault_cfg.get("skills_dir", "DevCrew-Vault/skills"))

    indexer = Indexer(config)
    indexer.reconcile(skills_dir)
    try:
        from catalog import load_catalog, select_skills
        catalog = load_catalog(config)
        select_skills(config, indexer._conn, catalog)
    except Exception as exc:
        log.warning("select_skills after scan failed: %s", exc)
    indexer.close()
    log.info("Scan complete")


def cmd_search(config: dict, query: str) -> None:
    """FTS5 search over indexed skills."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/vault.db"))
    conn = get_connection(db_path)
    init_db(conn)
    results = search_skills(conn, query)
    conn.close()

    if not results:
        print(f"No results for query: {query!r}")
        return

    print(f"\n{len(results)} result(s) for {query!r}:\n")
    for row in results:
        print(f"  [{row.get('slug', '?')}] {row.get('name', '')} — {row.get('description', '')[:80]}")


def cmd_list(config: dict) -> None:
    """List all skills currently in the DB."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/vault.db"))
    conn = get_connection(db_path)
    init_db(conn)
    rows = list_skills(conn)
    conn.close()

    if not rows:
        print("No skills indexed yet.")
        return

    print(f"\n{len(rows)} skill(s) in vault:\n")
    for row in rows:
        status = row.get("validation_status", "?")
        icon = {"valid": "✅", "valid-with-warnings": "⚠️", "invalid": "❌"}.get(status, "?")
        print(f"  {icon} {row.get('slug', '?'):30s}  {row.get('name', '')}")


def cmd_show(config: dict, slug: str) -> None:
    """Show details for a single skill."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/vault.db"))
    conn = get_connection(db_path)
    init_db(conn)
    row = get_skill(conn, slug)
    conn.close()

    if row is None:
        print(f"Skill {slug!r} not found in DB")
        return

    print(f"\n{'=' * 60}")
    print(f"Skill: {row.get('slug')}")
    print(f"{'=' * 60}")
    for key, val in row.items():
        if key in ("errors", "warnings"):
            parsed = json.loads(val) if isinstance(val, str) else val
            print(f"  {key:<20}: {parsed if parsed else '(none)'}")
        else:
            print(f"  {key:<20}: {val}")


def cmd_map(config: dict) -> None:
    """Build the Obsidian map layer."""
    from build_map import MapBuilder
    builder = MapBuilder(config)
    summary = builder.build()
    print(f"Map layer built: {summary['files_to_create']} files generated across {summary['total_selected']} selected skills.")


def cmd_related(config: dict, slug: str) -> None:
    """Show typed relations for a skill."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    from db import list_skill_links
    links = list_skill_links(conn, slug)
    conn.close()

    if not links:
        print(f"No related links found for skill {slug!r}")
        return

    print(f"\nRelated skills for '{slug}':")
    for link in links:
        rel = link.get("relation", "")
        dst = link.get("dst_slug", "")
        reason = link.get("reason", "")
        print(f"  [{rel:<12}] -> {dst:<35} ({reason})")


def cmd_tech(config: dict, tag: str) -> None:
    """Show selected skills tagged with a technology."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    from db import get_skills_by_tech_tag
    slugs = get_skills_by_tech_tag(conn, tag, selected_only=True)
    conn.close()

    if not slugs:
        print(f"No selected skills tagged with {tag!r}")
        return

    print(f"\nSelected skills with technology tag '{tag}' ({len(slugs)} total):")
    for s in slugs:
        print(f"  - {s}")


def cmd_mcp_list(config: dict) -> None:
    """List all MCP servers in the DB."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    from db import list_mcp_servers
    servers = list_mcp_servers(conn)
    conn.close()

    if not servers:
        print("No MCP servers found in DB. Run 'python tools/mcp_sync.py' first.")
        return

    print(f"\nFound {len(servers)} MCP servers in registry.db:\n")
    print(f"{'SLUG':<25} {'STATUS':<12} {'MODULE':<8} {'SCORE':<7} {'CAPABILITY':<14} {'NAME'}")
    print("-" * 90)
    for s in servers:
        slug = s.get("slug") or ""
        status = s.get("status") or ""
        mid = str(s.get("module_id") or "-")
        score = f"{s.get('vetting_score', 0)}/100"
        cap = s.get("capability_class") or "unknown"
        name = s.get("name") or ""
        print(f"{slug:<25} {status:<12} {mid:<8} {score:<7} {cap:<14} {name}")


def cmd_mcp_show(config: dict, slug: str) -> None:
    """Show details for a single MCP server."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    from db import get_mcp_server, list_mcp_links
    row = get_mcp_server(conn, slug)
    links = list_mcp_links(conn, mcp_slug=slug) if row else []
    conn.close()

    if row is None:
        print(f"MCP server {slug!r} not found in DB")
        return

    print(f"\n{'=' * 60}")
    print(f"MCP Server: {row.get('slug')} ({row.get('title')})")
    print(f"{'=' * 60}")
    for key, val in row.items():
        if key in ("snapshot_json",):
            continue
        print(f"  {key:<20}: {val}")

    if links:
        print("\n  Paired Skills (pairs-with):")
        for l in links:
            print(f"    - {l['skill_slug']} ({l.get('reason', '')})")


def cmd_mcp_search(config: dict, query: str) -> None:
    """Search MCP servers using FTS5."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    from db import search_mcp_servers
    results = search_mcp_servers(conn, query)
    conn.close()

    if not results:
        print(f"No MCP servers matched query {query!r}")
        return

    print(f"\nFound {len(results)} matching MCP server(s) for query {query!r}:\n")
    for r in results:
        status = r.get("status", "candidate")
        slug = r.get("slug", "")
        title = r.get("title", "")
        desc = (r.get("description") or "").replace("\n", " ")
        if len(desc) > 70:
            desc = desc[:67] + "..."
        print(f"  [{status:<10}] {slug:<22} {title:<25} {desc}")


def cmd_mcp_pairs(config: dict, skill_slug: str) -> None:
    """List MCP servers that pair with a skill."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    from db import list_mcp_links, get_mcp_server
    links = list_mcp_links(conn, skill_slug=skill_slug)
    servers = [get_mcp_server(conn, l["mcp_slug"]) for l in links]
    conn.close()

    if not links:
        print(f"No MCP servers paired with skill {skill_slug!r}")
        return

    print(f"\nMCP servers pairing with skill '{skill_slug}':\n")
    for l, s in zip(links, servers):
        mcp_slug = l["mcp_slug"]
        reason = l.get("reason", "")
        status = s.get("status") if s else "unknown"
        cap = s.get("capability_class") if s else "unknown"
        print(f"  - {mcp_slug:<22} [{status:<8} | {cap:<10}] ({reason})")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Entry point for the watcher CLI."""
    parser = argparse.ArgumentParser(
        description="DevCrew Skill Vault — file watcher & registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", metavar="PATH", help="Path to devcrew.config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="Start file watcher (blocks)")
    sub.add_parser("scan", help="One-shot vault reindex, then exit")

    sp_search = sub.add_parser("search", help="FTS5 search")
    sp_search.add_argument("query", help="Search query string")

    sub.add_parser("list", help="List all skills in DB")

    sp_show = sub.add_parser("show", help="Show details for one skill")
    sp_show.add_argument("slug", help="Skill slug")

    sub.add_parser("modules", help="Show per-module skill counts")

    sp_module = sub.add_parser("module", help="List skills in a specific module")
    sp_module.add_argument("id", type=int, help="Module number (1-7)")

    sub.add_parser("map", help="Build the Obsidian map layer")

    sp_related = sub.add_parser("related", help="List typed related skills for a slug")
    sp_related.add_argument("slug", help="Skill slug")

    sp_tech = sub.add_parser("tech", help="List selected skills tagged with a technology")
    sp_tech.add_argument("tag", help="Technology tag name")

    sub.add_parser("mcp-list", help="List all MCP servers in DB")

    sp_mcp_show = sub.add_parser("mcp-show", help="Show details for one MCP server")
    sp_mcp_show.add_argument("slug", help="MCP server slug")

    sp_mcp_search = sub.add_parser("mcp-search", help="FTS5 search over MCP servers")
    sp_mcp_search.add_argument("query", help="Search query string")

    sp_mcp_pairs = sub.add_parser("mcp-pairs", help="List MCP servers pairing with a skill")
    sp_mcp_pairs.add_argument("slug", help="Skill slug")

    args = parser.parse_args(argv)

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    if args.command == "run":
        cmd_run(config, config_path)
    elif args.command == "scan":
        cmd_scan(config)
    elif args.command == "search":
        cmd_search(config, args.query)
    elif args.command == "list":
        cmd_list(config)
    elif args.command == "show":
        cmd_show(config, args.slug)
    elif args.command == "modules":
        cmd_modules(config)
    elif args.command == "module":
        cmd_module(config, args.id)
    elif args.command == "map":
        cmd_map(config)
    elif args.command == "related":
        cmd_related(config, args.slug)
    elif args.command == "tech":
        cmd_tech(config, args.tag)
    elif args.command == "mcp-list":
        cmd_mcp_list(config)
    elif args.command == "mcp-show":
        cmd_mcp_show(config, args.slug)
    elif args.command == "mcp-search":
        cmd_mcp_search(config, args.query)
    elif args.command == "mcp-pairs":
        cmd_mcp_pairs(config, args.slug)
    else:
        parser.print_help()



if __name__ == "__main__":
    main()


"""Database layer for the DevCrew AI Skill Vault.

Manages a SQLite database that stores parsed skill metadata together with an
FTS5 virtual table for full-text search.  All public functions accept an open
:class:`sqlite3.Connection` so callers control transaction boundaries and
connection lifetime.

Schema overview
---------------
* **skills** – primary relational table (one row per ingested skill).
* **skills_fts** – FTS5 virtual table mirrored from ``skills`` via triggers.

The database is opened in WAL (Write-Ahead Logging) mode for better
concurrency.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS skills (
  id                  INTEGER PRIMARY KEY,
  slug                TEXT UNIQUE NOT NULL,
  name                TEXT NOT NULL,
  description         TEXT NOT NULL,
  body                TEXT NOT NULL,
  frontmatter_json    TEXT NOT NULL,
  license             TEXT,
  source_name         TEXT,
  commit_sha          TEXT,
  path                TEXT NOT NULL,
  content_sha256      TEXT NOT NULL,
  validation_status   TEXT NOT NULL,
  validation_messages TEXT,
  has_scripts         INTEGER DEFAULT 0,
  has_references      INTEGER DEFAULT 0,
  has_assets          INTEGER DEFAULT 0,
  created_at          TEXT,
  updated_at          TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
  name, description, body,
  content='skills', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS skills_ai AFTER INSERT ON skills BEGIN
  INSERT INTO skills_fts(rowid, name, description, body)
  VALUES (new.id, new.name, new.description, new.body);
END;

CREATE TRIGGER IF NOT EXISTS skills_ad AFTER DELETE ON skills BEGIN
  INSERT INTO skills_fts(skills_fts, rowid, name, description, body)
  VALUES ('delete', old.id, old.name, old.description, old.body);
END;

CREATE TRIGGER IF NOT EXISTS skills_au AFTER UPDATE ON skills BEGIN
  INSERT INTO skills_fts(skills_fts, rowid, name, description, body)
  VALUES ('delete', old.id, old.name, old.description, old.body);
  INSERT INTO skills_fts(rowid, name, description, body)
  VALUES (new.id, new.name, new.description, new.body);
END;

CREATE TABLE IF NOT EXISTS skill_modules (
  slug       TEXT    NOT NULL,
  module_id  INTEGER NOT NULL,
  rank       REAL    DEFAULT 0,
  score      REAL    DEFAULT 0,
  status     TEXT    DEFAULT 'candidate',  -- selected | candidate | alternate
  PRIMARY KEY (slug, module_id),
  FOREIGN KEY (slug) REFERENCES skills(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tech_tags (
  slug TEXT NOT NULL,
  tag  TEXT NOT NULL,
  PRIMARY KEY (slug, tag),
  FOREIGN KEY (slug) REFERENCES skills(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS skill_links (
  src_slug   TEXT NOT NULL,
  dst_slug   TEXT NOT NULL,
  relation   TEXT NOT NULL,  -- complements | alternate-of | precedes
  reason     TEXT DEFAULT '',
  created_by TEXT DEFAULT 'rule',
  PRIMARY KEY (src_slug, dst_slug, relation),
  FOREIGN KEY (src_slug) REFERENCES skills(slug) ON DELETE CASCADE,
  FOREIGN KEY (dst_slug) REFERENCES skills(slug) ON DELETE CASCADE
);
"""

_MCP_DDL = """
CREATE TABLE IF NOT EXISTS mcp_servers(
  id                  INTEGER PRIMARY KEY,
  name                TEXT UNIQUE NOT NULL,
  slug                TEXT UNIQUE NOT NULL,
  title               TEXT,
  description         TEXT,
  version             TEXT,
  approved_version    TEXT,
  repo_url            TEXT,
  license             TEXT,
  publisher           TEXT,
  publisher_verified  INTEGER DEFAULT 0,
  maintainer_class    TEXT DEFAULT 'community',
  transport           TEXT,
  package_types       TEXT,
  requires_secrets    INTEGER DEFAULT 0,
  capability_class    TEXT DEFAULT 'unknown',
  module_id           INTEGER,
  status              TEXT DEFAULT 'candidate',
  vetting_score       INTEGER DEFAULT 0,
  vetting_notes       TEXT,
  last_commit_at      TEXT,
  repo_archived       INTEGER DEFAULT 0,
  content_sha256      TEXT,
  snapshot_json       TEXT,
  retrieved_at        TEXT,
  approved_by         TEXT,
  approved_at         TEXT,
  license_source      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mcp_sync_runs (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at              TEXT NOT NULL,
  finished_at             TEXT,
  pages_fetched           INTEGER NOT NULL DEFAULT 0,
  records_fetched         INTEGER NOT NULL DEFAULT 0,
  unique_server_names     INTEGER NOT NULL DEFAULT 0,
  unique_names_latest     INTEGER NOT NULL DEFAULT 0,
  records_skipped_invalid INTEGER NOT NULL DEFAULT 0,
  skip_reasons_json       TEXT DEFAULT '{}',
  final_cursor            TEXT,
  completed               INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS mcp_fts USING fts5(
  name, title, description,
  content='mcp_servers', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS mcp_ai AFTER INSERT ON mcp_servers BEGIN
  INSERT INTO mcp_fts(rowid, name, title, description)
  VALUES (new.id, new.name, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS mcp_ad AFTER DELETE ON mcp_servers BEGIN
  INSERT INTO mcp_fts(mcp_fts, rowid, name, title, description)
  VALUES ('delete', old.id, old.name, old.title, old.description);
END;

CREATE TRIGGER IF NOT EXISTS mcp_au AFTER UPDATE ON mcp_servers BEGIN
  INSERT INTO mcp_fts(mcp_fts, rowid, name, title, description)
  VALUES ('delete', old.id, old.name, old.title, old.description);
  INSERT INTO mcp_fts(rowid, name, title, description)
  VALUES (new.id, new.name, new.title, new.description);
END;

CREATE TABLE IF NOT EXISTS mcp_links (
  mcp_slug   TEXT NOT NULL,
  skill_slug TEXT NOT NULL,
  relation   TEXT NOT NULL DEFAULT 'pairs-with',
  reason     TEXT DEFAULT '',
  created_by TEXT DEFAULT 'rule',
  PRIMARY KEY (mcp_slug, skill_slug, relation)
);

CREATE TABLE IF NOT EXISTS mcp_tech_tags (
  slug TEXT NOT NULL,
  tag  TEXT NOT NULL,
  PRIMARY KEY (slug, tag)
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a :class:`sqlite3.Row` to a plain :class:`dict`."""
    return dict(row)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection to *db_path* in WAL mode.

    The parent directory of *db_path* is created automatically if it does not
    exist.

    Parameters
    ----------
    db_path:
        Filesystem path to the SQLite database file.  The file is created if
        it does not already exist.

    Returns
    -------
    sqlite3.Connection
        An open connection with ``row_factory`` set to :data:`sqlite3.Row` so
        that rows can be accessed both by index and by column name.
    """
    resolved = Path(db_path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row

    # Enable WAL for improved concurrency and durability.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


def init_mcp_schema(conn: sqlite3.Connection) -> None:
    """Ensure MCP tables, virtual tables, triggers, and links exist."""
    conn.executescript(_MCP_DDL)
    # Ensure license_source column exists in mcp_servers
    cols = [col[1] for col in conn.execute("PRAGMA table_info(mcp_servers)").fetchall()]
    if "license_source" not in cols:
        conn.execute("ALTER TABLE mcp_servers ADD COLUMN license_source TEXT DEFAULT ''")
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    """Initialise the database schema (idempotent).

    Creates the ``skills`` table, the ``skills_fts`` virtual table, the
    three synchronisation triggers, and the MCP catalog tables.
    Safe to call on every startup.

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection` as returned by
        :func:`get_connection`.
    """
    conn.executescript(_DDL)
    conn.commit()
    init_mcp_schema(conn)


def upsert_skill(conn: sqlite3.Connection, skill: dict[str, Any]) -> None:
    """Insert or replace a skill record, preserving its original *created_at*.

    When a skill with the same ``slug`` already exists its ``created_at``
    timestamp is preserved; only ``updated_at`` is refreshed.

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection`.
    skill:
        Dictionary containing skill data.  Required keys:

        ``slug``, ``name``, ``description``, ``body``, ``frontmatter_json``,
        ``path``, ``content_sha256``, ``validation_status``.

        Optional keys: ``license``, ``source_name``, ``commit_sha``,
        ``validation_messages``, ``has_scripts``, ``has_references``,
        ``has_assets``, ``created_at``.

    Raises
    ------
    KeyError
        If any required key is absent from *skill*.
    sqlite3.Error
        On any database error.
    """
    required = {
        "slug", "name", "description", "body", "frontmatter_json",
        "path", "content_sha256", "validation_status",
    }
    missing = required - skill.keys()
    if missing:
        raise KeyError(
            f"upsert_skill: missing required field(s): {', '.join(sorted(missing))}"
        )

    now = _now_iso()

    # Preserve created_at if the row already exists.
    existing = get_skill(conn, skill["slug"])
    created_at = (existing["created_at"] if existing else None) or skill.get("created_at") or now

    # Serialise frontmatter_json if a dict was passed for convenience.
    frontmatter_json = skill["frontmatter_json"]
    if isinstance(frontmatter_json, dict):
        frontmatter_json = json.dumps(frontmatter_json, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO skills (
            slug, name, description, body, frontmatter_json,
            license, source_name, commit_sha, path, content_sha256,
            validation_status, validation_messages,
            has_scripts, has_references, has_assets,
            created_at, updated_at
        ) VALUES (
            :slug, :name, :description, :body, :frontmatter_json,
            :license, :source_name, :commit_sha, :path, :content_sha256,
            :validation_status, :validation_messages,
            :has_scripts, :has_references, :has_assets,
            :created_at, :updated_at
        )
        ON CONFLICT(slug) DO UPDATE SET
            name                = excluded.name,
            description         = excluded.description,
            body                = excluded.body,
            frontmatter_json    = excluded.frontmatter_json,
            license             = excluded.license,
            source_name         = excluded.source_name,
            commit_sha          = excluded.commit_sha,
            path                = excluded.path,
            content_sha256      = excluded.content_sha256,
            validation_status   = excluded.validation_status,
            validation_messages = excluded.validation_messages,
            has_scripts         = excluded.has_scripts,
            has_references      = excluded.has_references,
            has_assets          = excluded.has_assets,
            updated_at          = excluded.updated_at
        """,
        {
            "slug":                skill["slug"],
            "name":                skill["name"],
            "description":         skill["description"],
            "body":                skill["body"],
            "frontmatter_json":    frontmatter_json,
            "license":             skill.get("license"),
            "source_name":         skill.get("source_name"),
            "commit_sha":          skill.get("commit_sha"),
            "path":                str(skill["path"]),
            "content_sha256":      skill["content_sha256"],
            "validation_status":   skill["validation_status"],
            "validation_messages": skill.get("validation_messages"),
            "has_scripts":         int(bool(skill.get("has_scripts", 0))),
            "has_references":      int(bool(skill.get("has_references", 0))),
            "has_assets":          int(bool(skill.get("has_assets", 0))),
            "created_at":          created_at,
            "updated_at":          now,
        },
    )
    conn.commit()


def delete_skill(conn: sqlite3.Connection, slug: str) -> None:
    """Remove a skill (and its FTS entry) from the database.

    If no skill with *slug* exists the call is a no-op.

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection`.
    slug:
        The unique slug identifying the skill to delete.
    """
    conn.execute("DELETE FROM skills WHERE slug = ?", (slug,))
    conn.commit()


def search_skills(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    """Full-text search across skill name, description, and body.

    Uses the FTS5 virtual table for fast keyword matching.  Results are
    ordered by FTS5 relevance rank (best match first).

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection`.
    query:
        FTS5 query string.  Plain words are matched as prefix queries;
        advanced FTS5 syntax (``AND``, ``OR``, ``NOT``, ``"phrase"``) is
        supported.

    Returns
    -------
    list[dict]
        List of matching skill rows as plain dicts, best match first.
        Returns an empty list when nothing matches.

    Raises
    ------
    sqlite3.OperationalError
        If *query* contains invalid FTS5 syntax.
    """
    cursor = conn.execute(
        """
        SELECT s.*
        FROM skills s
        JOIN skills_fts fts ON s.id = fts.rowid
        WHERE skills_fts MATCH ?
        ORDER BY rank
        """,
        (query,),
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def list_skills(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return every skill in the registry, ordered by slug.

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection`.

    Returns
    -------
    list[dict]
        All skill rows as plain dicts, alphabetically ordered by ``slug``.
        Returns an empty list when the registry is empty.
    """
    cursor = conn.execute("SELECT * FROM skills ORDER BY slug")
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_skill(conn: sqlite3.Connection, slug: str) -> dict[str, Any] | None:
    """Fetch a single skill by its unique slug.

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection`.
    slug:
        The unique slug identifying the skill.

    Returns
    -------
    dict or None
        The skill row as a plain dict, or ``None`` if no matching row exists.
    """
    cursor = conn.execute("SELECT * FROM skills WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    return _row_to_dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# skill_modules table — module classification registry
# ---------------------------------------------------------------------------


def upsert_skill_module(
    conn: sqlite3.Connection,
    slug: str,
    module_id: int,
    *,
    rank: float = 0.0,
    score: float = 0.0,
    status: str = "candidate",
) -> None:
    """Insert or replace a skill's module assignment.

    Parameters
    ----------
    conn:       An open :class:`sqlite3.Connection`.
    slug:       Skill slug.
    module_id:  Module number (1-7).
    rank:       Relative rank within module (lower is better, 0 = best).
    score:      Classification score.
    status:     ``"selected"``, ``"candidate"``, or ``"alternate"``.
    """
    conn.execute(
        """
        INSERT INTO skill_modules (slug, module_id, rank, score, status)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(slug, module_id) DO UPDATE SET
            rank   = excluded.rank,
            score  = excluded.score,
            status = excluded.status
        """,
        (slug, module_id, rank, score, status),
    )
    conn.commit()


def delete_skill_module(conn: sqlite3.Connection, slug: str) -> None:
    """Remove all module assignments for *slug*.

    Parameters
    ----------
    conn: An open :class:`sqlite3.Connection`.
    slug: Skill slug whose module rows should be removed.
    """
    conn.execute("DELETE FROM skill_modules WHERE slug = ?", (slug,))
    conn.commit()


def list_skill_modules(
    conn: sqlite3.Connection,
    module_id: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List skill module assignments, optionally filtered.

    Parameters
    ----------
    conn:      An open :class:`sqlite3.Connection`.
    module_id: If given, return only rows for this module.
    status:    If given, return only rows with this status.

    Returns
    -------
    list[dict]
        Rows from ``skill_modules`` joined with ``slug`` and ``name`` from
        ``skills``, ordered by ``module_id``, ``rank``.
    """
    clauses: list[str] = []
    params: list[Any] = []
    if module_id is not None:
        clauses.append("sm.module_id = ?")
        params.append(module_id)
    if status is not None:
        clauses.append("sm.status = ?")
        params.append(status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cursor = conn.execute(
        f"""
        SELECT sm.slug, sm.module_id, sm.rank, sm.score, sm.status,
               s.name, s.description, s.validation_status, s.source_name
        FROM skill_modules sm
        LEFT JOIN skills s ON s.slug = sm.slug
        {where}
        ORDER BY sm.module_id, sm.rank
        """,
        params,
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def module_counts(conn: sqlite3.Connection) -> dict[int, dict[str, int]]:
    """Return per-module counts broken down by status.

    Returns
    -------
    dict[int, dict[str, int]]
        ``{module_id: {"selected": N, "candidate": N, "alternate": N, "total": N}}``
    """
    cursor = conn.execute(
        """
        SELECT module_id, status, COUNT(*) AS cnt
        FROM skill_modules
        GROUP BY module_id, status
        ORDER BY module_id
        """
    )
    result: dict[int, dict[str, int]] = {}
    for row in cursor.fetchall():
        mid = row["module_id"]
        if mid not in result:
            result[mid] = {"selected": 0, "candidate": 0, "alternate": 0, "total": 0}
        result[mid][row["status"]] = row["cnt"]
        result[mid]["total"] += row["cnt"]
    return result


# ---------------------------------------------------------------------------
# Map Layer (tech_tags & skill_links) API
# ---------------------------------------------------------------------------


def init_map_schema(conn: sqlite3.Connection) -> None:
    """Ensure map layer tables exist in the database."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tech_tags (
          slug TEXT NOT NULL,
          tag  TEXT NOT NULL,
          PRIMARY KEY (slug, tag),
          FOREIGN KEY (slug) REFERENCES skills(slug) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS skill_links (
          src_slug   TEXT NOT NULL,
          dst_slug   TEXT NOT NULL,
          relation   TEXT NOT NULL,
          reason     TEXT DEFAULT '',
          created_by TEXT DEFAULT 'rule',
          PRIMARY KEY (src_slug, dst_slug, relation),
          FOREIGN KEY (src_slug) REFERENCES skills(slug) ON DELETE CASCADE,
          FOREIGN KEY (dst_slug) REFERENCES skills(slug) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def set_skill_tech_tags(conn: sqlite3.Connection, slug: str, tags: list[str]) -> None:
    """Replace all tech tags for *slug* with *tags*."""
    with conn:
        conn.execute("DELETE FROM tech_tags WHERE slug = ?", (slug,))
        for tag in tags:
            conn.execute(
                "INSERT OR IGNORE INTO tech_tags (slug, tag) VALUES (?, ?)",
                (slug, tag),
            )


def list_tech_tags(conn: sqlite3.Connection, slug: str | None = None) -> list[dict[str, str]]:
    """List tech tags, optionally filtered by *slug*."""
    if slug:
        cur = conn.execute("SELECT slug, tag FROM tech_tags WHERE slug = ? ORDER BY tag", (slug,))
    else:
        cur = conn.execute("SELECT slug, tag FROM tech_tags ORDER BY tag, slug")
    return [_row_to_dict(r) for r in cur.fetchall()]


def get_skills_by_tech_tag(conn: sqlite3.Connection, tag: str, selected_only: bool = True) -> list[str]:
    """Return skill slugs associated with *tag*."""
    if selected_only:
        cur = conn.execute(
            """
            SELECT t.slug
            FROM tech_tags t
            JOIN skill_modules sm ON t.slug = sm.slug
            WHERE t.tag = ? AND sm.status = 'selected'
            ORDER BY t.slug
            """,
            (tag,),
        )
    else:
        cur = conn.execute(
            "SELECT slug FROM tech_tags WHERE tag = ? ORDER BY slug",
            (tag,),
        )
    return [r[0] for r in cur.fetchall()]


def upsert_skill_link(
    conn: sqlite3.Connection,
    src_slug: str,
    dst_slug: str,
    relation: str,
    reason: str = "",
    created_by: str = "rule",
) -> None:
    """Insert or update a typed relationship link between two skills."""
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO skill_links (src_slug, dst_slug, relation, reason, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (src_slug, dst_slug, relation, reason, created_by),
        )


def list_skill_links(conn: sqlite3.Connection, slug: str | None = None) -> list[dict[str, Any]]:
    """Return outgoing skill links from *slug*, or all links if *slug* is None."""
    if slug:
        cur = conn.execute(
            """
            SELECT src_slug, dst_slug, relation, reason, created_by
            FROM skill_links
            WHERE src_slug = ?
            ORDER BY relation, dst_slug
            """,
            (slug,),
        )
    else:
        cur = conn.execute(
            """
            SELECT src_slug, dst_slug, relation, reason, created_by
            FROM skill_links
            ORDER BY src_slug, relation, dst_slug
            """
        )
    return [_row_to_dict(r) for r in cur.fetchall()]


def clear_skill_links(conn: sqlite3.Connection, created_by: str | None = None) -> None:
    """Remove skill links, optionally filtered by *created_by*."""
    with conn:
        if created_by:
            conn.execute("DELETE FROM skill_links WHERE created_by = ?", (created_by,))
        else:
            conn.execute("DELETE FROM skill_links")


# ---------------------------------------------------------------------------
# MCP Database Operations
# ---------------------------------------------------------------------------


def upsert_mcp_server(conn: sqlite3.Connection, server: dict[str, Any]) -> int:
    """Insert or replace an MCP server record in ``mcp_servers``.

    Returns the integer id of the inserted/updated row.
    """
    fields = [
        "name", "slug", "title", "description", "version", "approved_version",
        "repo_url", "license", "publisher", "publisher_verified",
        "maintainer_class", "transport", "package_types", "requires_secrets",
        "capability_class", "module_id", "status", "vetting_score",
        "vetting_notes", "last_commit_at", "repo_archived", "content_sha256",
        "snapshot_json", "retrieved_at", "approved_by", "approved_at",
        "license_source"
    ]
    vals = [server.get(f) for f in fields]
    placeholders = ", ".join(["?"] * len(fields))
    columns = ", ".join(fields)
    updates = ", ".join([f"{f} = excluded.{f}" for f in fields])

    query = f"""
    INSERT INTO mcp_servers ({columns})
    VALUES ({placeholders})
    ON CONFLICT(name) DO UPDATE SET
      {updates}
    RETURNING id
    """
    with conn:
        cur = conn.execute(query, vals)
        row = cur.fetchone()
        return row[0] if row else 0


def get_mcp_server(conn: sqlite3.Connection, slug_or_name: str) -> dict[str, Any] | None:
    """Fetch a single MCP server by slug or name."""
    cur = conn.execute(
        """
        SELECT * FROM mcp_servers
        WHERE slug = ? OR name = ?
        LIMIT 1
        """,
        (slug_or_name, slug_or_name),
    )
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def list_mcp_servers(
    conn: sqlite3.Connection,
    status: str | None = None,
    module_id: int | None = None,
) -> list[dict[str, Any]]:
    """List MCP servers with optional status and module_id filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if module_id is not None:
        clauses.append("module_id = ?")
        params.append(module_id)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM mcp_servers {where} ORDER BY module_id, vetting_score DESC, name"
    cur = conn.execute(query, params)
    return [_row_to_dict(r) for r in cur.fetchall()]


def search_mcp_servers(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    """Search MCP servers using full-text search (FTS5)."""
    # Tokenize alphanumeric words for FTS5
    tokens = re.findall(r'[a-zA-Z0-9]+', query)
    if not tokens:
        return []
    fts_query = " ".join([f'"{t}"*' for t in tokens])
    cur = conn.execute(
        """
        SELECT s.*
        FROM mcp_fts f
        JOIN mcp_servers s ON f.rowid = s.id
        WHERE mcp_fts MATCH ?
        ORDER BY rank
        LIMIT 50
        """,
        (fts_query,),
    )
    return [_row_to_dict(r) for r in cur.fetchall()]


def upsert_mcp_link(
    conn: sqlite3.Connection,
    mcp_slug: str,
    skill_slug: str,
    relation: str = "pairs-with",
    reason: str = "",
    created_by: str = "rule",
) -> None:
    """Insert or update a link connecting an MCP server to a skill."""
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO mcp_links (mcp_slug, skill_slug, relation, reason, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (mcp_slug, skill_slug, relation, reason, created_by),
        )


def list_mcp_links(
    conn: sqlite3.Connection,
    mcp_slug: str | None = None,
    skill_slug: str | None = None,
) -> list[dict[str, Any]]:
    """Return MCP links filtered by mcp_slug or skill_slug."""
    if mcp_slug and skill_slug:
        cur = conn.execute(
            "SELECT * FROM mcp_links WHERE mcp_slug = ? AND skill_slug = ? ORDER BY relation",
            (mcp_slug, skill_slug),
        )
    elif mcp_slug:
        cur = conn.execute(
            "SELECT * FROM mcp_links WHERE mcp_slug = ? ORDER BY relation, skill_slug",
            (mcp_slug,),
        )
    elif skill_slug:
        cur = conn.execute(
            "SELECT * FROM mcp_links WHERE skill_slug = ? ORDER BY relation, mcp_slug",
            (skill_slug,),
        )
    else:
        cur = conn.execute("SELECT * FROM mcp_links ORDER BY mcp_slug, skill_slug")
    return [_row_to_dict(r) for r in cur.fetchall()]


def clear_mcp_links(conn: sqlite3.Connection, created_by: str | None = None) -> None:
    """Clear MCP links, optionally filtered by created_by."""
    with conn:
        if created_by:
            conn.execute("DELETE FROM mcp_links WHERE created_by = ?", (created_by,))
        else:
            conn.execute("DELETE FROM mcp_links")


def set_mcp_tech_tags(conn: sqlite3.Connection, slug: str, tags: list[str]) -> None:
    """Replace all technology tags for an MCP server."""
    with conn:
        conn.execute("DELETE FROM mcp_tech_tags WHERE slug = ?", (slug,))
        conn.executemany(
            "INSERT OR IGNORE INTO mcp_tech_tags (slug, tag) VALUES (?, ?)",
            [(slug, tag) for tag in tags],
        )


def insert_sync_run(conn: sqlite3.Connection, run_data: dict[str, Any]) -> int:
    """Insert an MCP sync run record in ``mcp_sync_runs``.

    Returns the integer id of the inserted row.
    """
    query = """
    INSERT INTO mcp_sync_runs (
        started_at, finished_at, pages_fetched, records_fetched,
        unique_server_names, unique_names_latest, records_skipped_invalid,
        skip_reasons_json, final_cursor, completed
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with conn:
        cur = conn.execute(query, (
            run_data.get("started_at"),
            run_data.get("finished_at"),
            run_data.get("pages_fetched", 0),
            run_data.get("records_fetched", 0),
            run_data.get("unique_server_names", 0),
            run_data.get("unique_names_latest", 0),
            run_data.get("records_skipped_invalid", 0),
            json.dumps(run_data.get("skip_reasons", {})),
            run_data.get("final_cursor"),
            1 if run_data.get("completed") else 0,
        ))
        return cur.lastrowid or 0


def get_latest_sync_run(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """Fetch the latest MCP sync run record."""
    cur = conn.execute("SELECT * FROM mcp_sync_runs ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    return _row_to_dict(row) if row else None



def get_mcp_tech_tags(conn: sqlite3.Connection, slug: str) -> list[str]:
    """Retrieve technology tags for an MCP server."""
    cur = conn.execute("SELECT tag FROM mcp_tech_tags WHERE slug = ? ORDER BY tag", (slug,))
    return [r[0] for r in cur.fetchall()]



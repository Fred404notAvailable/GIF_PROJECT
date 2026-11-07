"""Parsing utilities for the DevCrew AI Skill Vault.

Provides functions for extracting YAML frontmatter from SKILL.md files,
computing stable content hashes for skill folders, and converting arbitrary
names into URL-safe slugs.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Frontmatter delimiter
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(
    r"^---\r?\n"          # opening fence
    r"(?P<fm>.*?)"        # frontmatter body (non-greedy)
    r"^---\r?\n?"         # closing fence
    r"(?P<body>.*)",      # remainder of the document
    re.DOTALL | re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Slug normalisation
# ---------------------------------------------------------------------------

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_HYPHEN_RE = re.compile(r"-{2,}")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_skill_md(path: Path) -> tuple[dict, str]:
    """Parse a SKILL.md file, extracting its YAML frontmatter and body.

    The file is expected to begin with a YAML frontmatter block delimited by
    ``---`` fences, for example::

        ---
        name: my-skill
        description: Does something useful.
        ---
        Body content goes here.

    Parameters
    ----------
    path:
        Absolute (or resolvable) path to the SKILL.md file.

    Returns
    -------
    tuple[dict, str]
        A two-element tuple ``(frontmatter, body)`` where *frontmatter* is the
        parsed YAML as a plain :class:`dict` and *body* is the remaining
        markdown text (stripped of leading/trailing blank lines).

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file has no valid frontmatter block, or if the frontmatter
        contains invalid YAML.
    """
    resolved = Path(path).resolve()

    if not resolved.is_file():
        raise FileNotFoundError(f"SKILL.md not found: '{resolved}'")

    text = resolved.read_text(encoding="utf-8")

    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError(
            f"No valid YAML frontmatter found in '{resolved}'. "
            "The file must begin with a '---' delimited block."
        )

    raw_frontmatter = match.group("fm")
    body = match.group("body").strip()

    try:
        frontmatter: dict = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML in frontmatter of '{resolved}': {exc}"
        ) from exc

    if not isinstance(frontmatter, dict):
        raise ValueError(
            f"Frontmatter in '{resolved}' must be a YAML mapping, "
            f"got {type(frontmatter).__name__}."
        )

    return frontmatter, body


def content_sha256(folder: Path) -> str:
    """Compute a stable SHA-256 digest of a skill folder's entire content.

    All regular files are discovered recursively, sorted by their path relative
    to *folder*, and fed into the hash in that deterministic order.  For each
    file both the **relative path string** and the **raw file bytes** are
    hashed so that renames and content changes are both detected.

    Files that cannot be read (e.g. due to Windows Unicode path restrictions
    or permission errors) are silently skipped but their path is still included
    in the hash so their presence is recorded.

    Parameters
    ----------
    folder:
        Path to the directory to hash.

    Returns
    -------
    str
        Lowercase hex-encoded SHA-256 digest string (64 characters).

    Raises
    ------
    NotADirectoryError
        If *folder* does not point to a directory.
    """
    resolved = Path(folder).resolve()

    if not resolved.is_dir():
        raise NotADirectoryError(
            f"Expected a directory for content hashing, got: '{resolved}'"
        )

    hasher = hashlib.sha256()

    # Collect all files sorted by relative POSIX path for cross-platform
    # stability.  Use os.walk for more robust Unicode filename handling on
    # Windows than rglob.
    import os
    all_files: list[Path] = []
    try:
        for dirpath, _dirnames, filenames in os.walk(str(resolved)):
            for fname in filenames:
                try:
                    fpath = Path(dirpath) / fname
                    all_files.append(fpath)
                except (ValueError, OSError):
                    continue
    except OSError:
        pass

    all_files.sort(key=lambda p: p.as_posix())

    for file_path in all_files:
        try:
            relative_posix = file_path.relative_to(resolved).as_posix()
        except ValueError:
            relative_posix = file_path.as_posix()

        # Hash the relative path name so renames affect the digest.
        hasher.update(relative_posix.encode("utf-8", errors="replace"))
        hasher.update(b"\x00")  # null separator between path and content

        try:
            hasher.update(file_path.read_bytes())
        except (OSError, ValueError):
            # Unreadable file (Windows Unicode path restriction, permission
            # error, etc.) — record the path but skip file content.
            hasher.update(b"<unreadable>")

        hasher.update(b"\x00")  # null separator between files

    return hasher.hexdigest()


def slugify(name: str) -> str:
    """Convert *name* to a lowercase, hyphen-separated URL-safe slug.

    Rules applied in order:

    1. Lowercase the entire string.
    2. Replace every run of non-alphanumeric characters with a single hyphen.
    3. Collapse any remaining consecutive hyphens into one.
    4. Strip leading and trailing hyphens.

    Parameters
    ----------
    name:
        Arbitrary human-readable skill name, e.g. ``"My Cool Skill (v2)"``.

    Returns
    -------
    str
        A clean slug such as ``"my-cool-skill-v2"``.  Returns an empty string
        if *name* contains no alphanumeric characters.

    Examples
    --------
    >>> slugify("My Cool Skill (v2)")
    'my-cool-skill-v2'
    >>> slugify("  --hello world--  ")
    'hello-world'
    """
    lowered = name.lower()
    hyphenated = _NON_ALNUM_RE.sub("-", lowered)
    collapsed = _MULTI_HYPHEN_RE.sub("-", hyphenated)
    return collapsed.strip("-")

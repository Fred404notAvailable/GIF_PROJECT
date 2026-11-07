"""
git_ops.py — DevCrew AI Skill Vault Git operations helper.

Provides shared Git utilities used by sync_skills and other tools.

Functions
---------
git_available()     — check that the git CLI is on PATH.
get_commit_sha()    — return HEAD commit SHA for a local repo.
shallow_clone()     — shallow-clone (or fetch+ff) a remote repo.
download_zip()      — fallback: download a GitHub archive zip and extract it.

All functions raise ``RuntimeError`` with descriptive messages on failure.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run(
    args: list[str],
    cwd: Path | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run *args* as a subprocess, raising ``RuntimeError`` on non-zero exit."""
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ""
        raise RuntimeError(
            f"Command {args!r} failed (exit {result.returncode}): {stderr}"
        )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def git_available() -> bool:
    """Return *True* if the ``git`` executable is discoverable on PATH.

    Returns:
        bool: ``True`` when git is available, ``False`` otherwise.
    """
    return shutil.which("git") is not None


def get_commit_sha(repo_path: Path) -> str:
    """Return the current HEAD commit SHA for the repository at *repo_path*.

    Args:
        repo_path: Absolute path to a local git repository.

    Returns:
        The full 40-character commit SHA string.

    Raises:
        RuntimeError: If git is not available or the path is not a valid repo.
    """
    if not git_available():
        raise RuntimeError(
            "git executable not found on PATH. Please install Git and retry."
        )
    if not repo_path.is_dir():
        raise RuntimeError(f"Repository path does not exist or is not a directory: {repo_path}")

    result = _run(["git", "rev-parse", "HEAD"], cwd=repo_path)
    sha = result.stdout.strip()
    if not sha:
        raise RuntimeError(f"Could not read HEAD SHA from repository: {repo_path}")
    return sha


def shallow_sparse_clone(
    url: str, dest: Path, ref: str = "main", sparse_dirs: list[str] | None = None
) -> str:
    """Shallow-clone with optional sparse-checkout into *dest*.

    When *sparse_dirs* is provided, only those directories are checked out
    (using ``git sparse-checkout set``).  This is used for large monorepos
    such as ``vercel/next.js`` where only a ``skills/`` subdirectory is needed.

    Args:
        url:         Remote repository URL.
        dest:        Local destination directory.
        ref:         Branch/tag to check out.
        sparse_dirs: If given, list of subdirectories to include (sparse checkout).

    Returns:
        HEAD commit SHA after clone/fetch.

    Raises:
        RuntimeError: If git is unavailable or any git command fails.
    """
    if not git_available():
        raise RuntimeError(
            "git executable not found on PATH. Cannot perform sparse clone."
        )

    git_dir = dest / ".git"
    if git_dir.is_dir():
        # Already cloned — just update
        return shallow_clone(url, dest, ref=ref)

    dest.parent.mkdir(parents=True, exist_ok=True)

    if sparse_dirs:
        # Init bare-ish repo then set up sparse checkout before fetch
        _run(["git", "init", str(dest)])
        _run(["git", "remote", "add", "origin", url], cwd=dest)
        _run(["git", "sparse-checkout", "init", "--cone"], cwd=dest)
        _run(["git", "sparse-checkout", "set"] + sparse_dirs, cwd=dest)
        try:
            _run(
                ["git", "fetch", "--depth", "1", "origin", ref],
                cwd=dest,
            )
            _run(["git", "checkout", f"origin/{ref}"], cwd=dest)
        except RuntimeError:
            # Try branch name without origin/ prefix
            _run(["git", "reset", "--hard", f"origin/{ref}"], cwd=dest)
    else:
        return shallow_clone(url, dest, ref=ref)

    return get_commit_sha(dest)


def shallow_clone(url: str, dest: Path, ref: str = "main") -> str:
    """Shallow-clone *url* into *dest* (or fetch + fast-forward if dest exists).

    Uses ``--depth 1`` to minimise bandwidth.  If *dest* already contains a
    git repository, performs ``git fetch --depth 1`` followed by a
    fast-forward reset instead of a full re-clone.

    Args:
        url:  Remote repository URL (HTTPS or SSH).
        dest: Local destination directory (need not exist yet).
        ref:  Branch name, tag, or commit reference to check out (default: ``"main"``).

    Returns:
        The full 40-character HEAD commit SHA after the clone/fetch.

    Raises:
        RuntimeError: If git is unavailable or any git command fails.
    """
    if not git_available():
        raise RuntimeError(
            "git executable not found on PATH. Cannot perform shallow clone. "
            "Install Git or use download_zip() as a fallback."
        )

    git_dir = dest / ".git"

    if git_dir.is_dir():
        # Repository already exists — fetch latest ref and fast-forward
        try:
            _run(
                ["git", "fetch", "--depth", "1", "origin", ref],
                cwd=dest,
            )
            _run(
                ["git", "reset", "--hard", f"origin/{ref}"],
                cwd=dest,
            )
        except RuntimeError as exc:
            raise RuntimeError(
                f"Failed to update existing clone at {dest} (ref={ref!r}): {exc}"
            ) from exc
    else:
        # Fresh clone
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            _run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    ref,
                    "--single-branch",
                    url,
                    str(dest),
                ]
            )
        except RuntimeError as exc:
            raise RuntimeError(
                f"Failed to clone {url!r} → {dest} (ref={ref!r}): {exc}"
            ) from exc

    return get_commit_sha(dest)


def download_zip(url: str, dest: Path, ref: str = "main") -> Path:
    """Download a GitHub archive zip for *ref* and extract it to *dest*.

    This is the non-git fallback for environments where the git CLI is
    unavailable.  The function constructs the standard GitHub archive URL
    automatically if *url* looks like a GitHub repo URL; otherwise it
    downloads *url* directly.

    Args:
        url:  GitHub repository URL (e.g. ``"https://github.com/owner/repo.git"``)
              or a direct archive URL ending in ``.zip``.
        dest: Local directory where the archive will be extracted.
        ref:  Branch name or tag to download (default: ``"main"``).

    Returns:
        The *dest* path after extraction.

    Raises:
        RuntimeError: On network errors, bad archives, or unexpected formats.
    """
    import urllib.error
    import urllib.request

    # Build archive URL for GitHub repos if a plain repo URL is supplied
    if url.endswith(".zip"):
        archive_url = url
    else:
        # Normalise: strip trailing slash and .git suffix
        base = url.rstrip("/").removesuffix(".git")
        archive_url = f"{base}/archive/refs/heads/{ref}.zip"

    try:
        with urllib.request.urlopen(archive_url, timeout=120) as response:  # noqa: S310
            zip_bytes = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Failed to download archive from {archive_url!r}: {exc}"
        ) from exc

    # Extract to a temporary directory first, then move atomically
    tmp_root = dest.parent / f".tmp_extract_{dest.name}"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmp_root)

        # GitHub archives contain a single top-level folder: <repo>-<ref>/
        inner_dirs = [p for p in tmp_root.iterdir() if p.is_dir()]
        if len(inner_dirs) != 1:
            raise RuntimeError(
                f"Expected exactly one top-level directory in zip archive, "
                f"got: {[d.name for d in inner_dirs]}"
            )
        extracted = inner_dirs[0]

        # Move to final dest (remove old dest if present)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(extracted), str(dest))
    except (zipfile.BadZipFile, KeyError) as exc:
        raise RuntimeError(f"Failed to extract archive from {archive_url!r}: {exc}") from exc
    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)

    return dest

"""Configuration loader for the DevCrew AI Skill Vault.

Provides utilities to locate, parse, and validate ``devcrew.config.yaml``,
resolving all relative vault/source paths to absolute paths anchored at the
config file's parent directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = "devcrew.config.yaml"

REQUIRED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {"vault", "sources", "allowed_licenses", "on_unknown_license", "on_slug_collision"}
)

REQUIRED_VAULT_KEYS: frozenset[str] = frozenset(
    {"skills_dir", "quarantine_dir", "staging_dir", "db_path"}
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_config_file() -> Path:
    """Walk up from the current working directory to find ``devcrew.config.yaml``.

    Traverses parent directories from :func:`Path.cwd` upward until it finds a
    file named ``devcrew.config.yaml``.  Stops at the filesystem root.

    Returns
    -------
    Path
        Absolute path to the located config file.

    Raises
    ------
    FileNotFoundError
        If no ``devcrew.config.yaml`` can be found in the current directory or
        any of its ancestors.
    """
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not find '{CONFIG_FILENAME}' in '{current}' or any parent directory. "
        "Make sure you are running from within a DevCrew project."
    )


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate ``devcrew.config.yaml``, resolving all relative paths.

    If *path* is ``None`` the config file is located automatically via
    :func:`find_config_file`.

    All path-like values inside the ``vault`` section (``skills_dir``,
    ``quarantine_dir``, ``staging_dir``, ``db_path``) are resolved to absolute
    :class:`~pathlib.Path` objects relative to the directory that contains the
    config file.

    Parameters
    ----------
    path:
        Explicit path to ``devcrew.config.yaml``.  When ``None`` the file is
        discovered by walking up from :func:`Path.cwd`.

    Returns
    -------
    dict
        Fully validated and path-resolved configuration dictionary.

    Raises
    ------
    FileNotFoundError
        If the config file cannot be located.
    ValueError
        If the YAML is malformed or required keys are missing.
    """
    config_path = Path(path).resolve() if path is not None else find_config_file()

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Config file not found: '{config_path}'"
        )

    raw_text = config_path.read_text(encoding="utf-8")

    try:
        config: dict[str, Any] = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Failed to parse '{config_path}' as YAML: {exc}"
        ) from exc

    if not isinstance(config, dict):
        raise ValueError(
            f"'{config_path}' must contain a YAML mapping at the top level, "
            f"got {type(config).__name__}."
        )

    _validate_required_keys(config, REQUIRED_TOP_LEVEL_KEYS, context="top-level")

    vault_section = config["vault"]
    if not isinstance(vault_section, dict):
        raise ValueError(
            f"'vault' in '{config_path}' must be a mapping, "
            f"got {type(vault_section).__name__}."
        )

    _validate_required_keys(vault_section, REQUIRED_VAULT_KEYS, context="vault")

    # Resolve all vault paths relative to the config file's directory.
    project_root = config_path.parent
    config["_project_root"] = project_root
    config["_config_path"] = config_path

    for key in REQUIRED_VAULT_KEYS:
        raw_value = vault_section[key]
        if not isinstance(raw_value, str):
            raise ValueError(
                f"'vault.{key}' must be a string path, got {type(raw_value).__name__}."
            )
        resolved = (project_root / raw_value).resolve()
        vault_section[key] = resolved

    # Validate sources list.
    sources = config.get("sources")
    if not isinstance(sources, list):
        raise ValueError(
            f"'sources' in '{config_path}' must be a list, "
            f"got {type(sources).__name__}."
        )

    for idx, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(
                f"'sources[{idx}]' must be a mapping, got {type(source).__name__}."
            )
        for required_source_key in ("name", "url"):
            if required_source_key not in source:
                raise ValueError(
                    f"'sources[{idx}]' is missing required key '{required_source_key}'."
                )
        # Apply defaults for optional source keys
        source.setdefault("ref", "main")
        source.setdefault("skills_glob", "**/**/SKILL.md")

    # Validate scalar policy fields.
    _validate_choice(
        config, "on_unknown_license", ("quarantine", "skip", "allow"), config_path
    )
    _validate_choice(
        config, "on_slug_collision", ("namespace", "skip", "overwrite"), config_path
    )

    return config


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_required_keys(
    mapping: dict[str, Any],
    required: frozenset[str],
    context: str,
) -> None:
    """Raise :class:`ValueError` if any *required* key is absent from *mapping*."""
    missing = required - mapping.keys()
    if missing:
        sorted_missing = ", ".join(f"'{k}'" for k in sorted(missing))
        raise ValueError(
            f"Config is missing required {context} key(s): {sorted_missing}."
        )


def _validate_choice(
    config: dict[str, Any],
    key: str,
    choices: tuple[str, ...],
    config_path: Path,
) -> None:
    """Raise :class:`ValueError` if *config[key]* is not one of *choices*."""
    value = config.get(key)
    if value not in choices:
        raise ValueError(
            f"'{key}' in '{config_path}' must be one of {choices!r}, got {value!r}."
        )

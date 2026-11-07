"""
validate_skills.py — DevCrew AI Skill Vault
============================================
Validates SKILL.md packages against the spec.

CLI:
    python tools/validate_skills.py [--fix] [--report] [--skill SLUG] [--config PATH]

Importable API:
    validate_skill(skill_path, config, fix=False) -> ValidationResult
    validate_all(config, fix=False, skill_filter=None) -> list[ValidationResult]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Local imports — resolved at runtime so the module is importable even when
# running from the project root.
# ---------------------------------------------------------------------------
_TOOLS_DIR = Path(__file__).parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from config import load_config  # noqa: E402
from parsing import parse_skill_md, slugify  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Regex that a valid slug / name must match (single-char variant handled separately)
_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
_NAME_SINGLE_RE = re.compile(r"^[a-z]$")
_CONSECUTIVE_HYPHEN_RE = re.compile(r"--")

#: Relative markdown link pattern:  [label](path)  — does NOT start with http/https/#
_REL_LINK_RE = re.compile(r"\[(?:[^\]]*)\]\((?!https?://|#)([^)]+)\)")

#: Trigger-language keywords for description quality warning
_TRIGGER_WORDS = [
    "use when",
    "trigger",
    "when to use",
    "activate",
    "use this when",
    "invoke when",
]

# Optional frontmatter fields and their expected Python types
_OPTIONAL_FIELD_TYPES: dict[str, type | tuple[type, ...]] = {
    "license": str,
    "compatibility": (str, list),
    "metadata": dict,
    "allowed-tools": list,
}

# ---------------------------------------------------------------------------
# Public data-class
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Outcome of validating a single skill folder."""

    slug: str
    status: str = "valid"  # "valid" | "valid-with-warnings" | "invalid"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.status = "invalid"

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        if self.status == "valid":
            self.status = "valid-with-warnings"

    def add_fix(self, msg: str) -> None:
        self.fixes_applied.append(msg)

    def as_dict(self) -> dict:
        return {
            "slug": self.slug,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "fixes_applied": self.fixes_applied,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    """Read a file as UTF-8 text, falling back to latin-1."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _check_name(name: Any, slug: str, result: ValidationResult) -> None:
    """Validate the ``name`` frontmatter field."""
    if not isinstance(name, str) or not name:
        result.add_error("'name' field is missing or not a non-empty string")
        return

    if len(name) > 64:
        result.add_error(f"'name' exceeds 64 chars (got {len(name)})")

    if not (_NAME_RE.match(name) or _NAME_SINGLE_RE.match(name)):
        result.add_error(
            f"'name' does not match pattern ^[a-z][a-z0-9-]*[a-z0-9]$ or ^[a-z]$ (got {name!r})"
        )
    elif _CONSECUTIVE_HYPHEN_RE.search(name):
        result.add_error(f"'name' contains consecutive hyphens (got {name!r})")

    if name != slug:
        result.add_error(
            f"'name' ({name!r}) does not match folder name / slug ({slug!r})"
        )


def _check_description(description: Any, config: dict, result: ValidationResult) -> None:
    """Validate the ``description`` frontmatter field."""
    validation_cfg: dict = config.get("validation", {})
    max_desc = int(validation_cfg.get("max_description_chars", 1024))

    if not isinstance(description, str) or not description.strip():
        result.add_error("'description' field is missing or empty")
        return

    desc = description.strip()
    if len(desc) > max_desc:
        result.add_error(
            f"'description' exceeds {max_desc} chars (got {len(desc)})"
        )

    lower = desc.lower()
    has_trigger = any(kw in lower for kw in _TRIGGER_WORDS)
    if not has_trigger:
        result.add_warning(
            "'description' lacks trigger language "
            "(e.g. 'use when', 'trigger', 'when to use', 'activate', etc.)"
        )


def _check_optional_fields(frontmatter: dict, result: ValidationResult) -> None:
    """Validate optional frontmatter fields' types."""
    for field_name, expected_type in _OPTIONAL_FIELD_TYPES.items():
        value = frontmatter.get(field_name)
        if value is None:
            continue
        if not isinstance(value, expected_type):
            type_names = (
                " or ".join(t.__name__ for t in expected_type)
                if isinstance(expected_type, tuple)
                else expected_type.__name__
            )
            result.add_error(
                f"Optional field '{field_name}' has wrong type "
                f"(expected {type_names}, got {type(value).__name__})"
            )


def _check_body(body: str, skill_path: Path, config: dict, result: ValidationResult) -> None:
    """Validate the Markdown body of SKILL.md."""
    validation_cfg: dict = config.get("validation", {})
    warn_long = int(validation_cfg.get("warn_long_body_chars", 8000))

    if not body or not body.strip():
        result.add_error("SKILL.md body is empty")
        return

    if len(body) > warn_long:
        result.add_warning(
            f"Body is {len(body)} chars (>{warn_long}); "
            "consider moving large content to references/"
        )

    # Check relative file links
    for match in _REL_LINK_RE.finditer(body):
        rel_path_str = match.group(1).strip()
        # Strip query/anchor fragments that might follow
        rel_path_str = rel_path_str.split("?")[0].split("#")[0]
        if not rel_path_str:
            continue
        target = skill_path / rel_path_str
        if not target.exists():
            result.add_warning(
                f"Referenced file not found: {rel_path_str!r} "
                f"(resolved to {target})"
            )


def _check_safety(skill_path: Path, frontmatter: dict, body: str, config: dict, result: ValidationResult) -> None:
    """
    Safety scan — NEVER execute ingested code.

    * Flag ``safety_patterns`` in ``scripts/`` files.
    * Flag ``prompt_injection_patterns`` anywhere in SKILL.md.
    """
    validation_cfg: dict = config.get("validation", {})
    safety_patterns: list[str] = validation_cfg.get("safety_patterns", [])
    injection_patterns: list[str] = validation_cfg.get("prompt_injection_patterns", [])

    compiled_safety = [re.compile(p, re.IGNORECASE) for p in safety_patterns]
    compiled_injection = [re.compile(p, re.IGNORECASE) for p in injection_patterns]

    # --- scripts/ directory scan ---
    scripts_dir = skill_path / "scripts"
    if scripts_dir.is_dir():
        for script_file in scripts_dir.rglob("*"):
            if not script_file.is_file():
                continue
            try:
                content = _read_text(script_file)
            except OSError:
                continue
            for lineno, line in enumerate(content.splitlines(), start=1):
                for pattern in compiled_safety:
                    if pattern.search(line):
                        result.add_warning(
                            f"[SAFETY] Pattern {pattern.pattern!r} matched in "
                            f"{script_file.relative_to(skill_path)} line {lineno}: {line.strip()!r}"
                        )

    # --- SKILL.md prompt injection scan ---
    skill_md_lines = body.splitlines()
    for lineno, line in enumerate(skill_md_lines, start=1):
        for pattern in compiled_injection:
            if pattern.search(line):
                result.add_warning(
                    f"[INJECTION] Pattern {pattern.pattern!r} matched in "
                    f"SKILL.md line {lineno}: {line.strip()!r}"
                )


# ---------------------------------------------------------------------------
# Fix / normalization helpers
# ---------------------------------------------------------------------------


def _apply_fixes(
    skill_path: Path,
    frontmatter: dict,
    body: str,
    result: ValidationResult,
) -> tuple[dict, str]:
    """
    Apply safe normalizations and return the mutated (frontmatter, body).
    Changes are recorded in ``result.fixes_applied``.
    """
    # 1. Lowercase + slugify name
    original_name = frontmatter.get("name", "")
    if isinstance(original_name, str):
        fixed_name = slugify(original_name)
        if fixed_name != original_name:
            frontmatter["name"] = fixed_name
            result.add_fix(f"Slugified name: {original_name!r} → {fixed_name!r}")

    # 2. Trim description
    description = frontmatter.get("description", "")
    if isinstance(description, str):
        trimmed = description.strip()
        if trimmed != description:
            frontmatter["description"] = trimmed
            result.add_fix("Trimmed whitespace from 'description'")

    # 3. Normalize line endings to LF
    if "\r\n" in body or "\r" in body:
        body = body.replace("\r\n", "\n").replace("\r", "\n")
        result.add_fix("Normalized line endings to LF")

    # 4. Ensure trailing newline
    if body and not body.endswith("\n"):
        body += "\n"
        result.add_fix("Added trailing newline to body")

    # 5. Add license from .source.json if missing
    if "license" not in frontmatter or not frontmatter["license"]:
        source_json = skill_path / ".source.json"
        if source_json.exists():
            try:
                source_data = json.loads(source_json.read_text(encoding="utf-8"))
                license_val = source_data.get("license")
                if license_val:
                    frontmatter["license"] = license_val
                    result.add_fix(f"Added license {license_val!r} from .source.json")
            except (json.JSONDecodeError, OSError):
                pass

    return frontmatter, body


def _write_skill_md(skill_path: Path, frontmatter: dict, body: str) -> None:
    """Serialise frontmatter back to YAML and rewrite SKILL.md."""
    try:
        import yaml  # type: ignore
    except ImportError:
        # Fallback: minimal manual serialisation
        yaml = None  # type: ignore

    if yaml is not None:
        fm_text = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    else:
        # Simple key: value serialisation (no nested structures)
        lines = []
        for k, v in frontmatter.items():
            if isinstance(v, str):
                lines.append(f"{k}: {v}")
            else:
                lines.append(f"{k}: {json.dumps(v)}")
        fm_text = "\n".join(lines) + "\n"

    new_content = f"---\n{fm_text}---\n{body}"
    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(new_content, encoding="utf-8")


def _quarantine_skill(skill_path: Path, slug: str, result: ValidationResult, config: dict) -> None:
    """Move an invalid skill folder to the quarantine directory."""
    vault_cfg: dict = config.get("vault", {})
    q_raw = vault_cfg.get("quarantine_dir")
    if q_raw is None:
        quarantine_dir = skill_path.parent.parent / "_quarantine"
    else:
        quarantine_dir = Path(q_raw)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    dest = quarantine_dir / slug
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(skill_path), str(dest))

    # Write REPORT.md
    report_lines = [
        f"# Validation Report — {slug}\n",
        f"**Status:** {result.status}\n",
        "## Errors\n",
    ]
    if result.errors:
        for err in result.errors:
            report_lines.append(f"- {err}\n")
    else:
        report_lines.append("_None_\n")

    report_lines.append("## Warnings\n")
    if result.warnings:
        for w in result.warnings:
            report_lines.append(f"- {w}\n")
    else:
        report_lines.append("_None_\n")

    (dest / "REPORT.md").write_text("".join(report_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_skill(
    skill_path: Path,
    config: dict,
    fix: bool = False,
) -> ValidationResult:
    """
    Validate a single skill folder.

    Parameters
    ----------
    skill_path:
        Absolute path to the skill folder (e.g. ``vault/skills/my-skill/``).
    config:
        Loaded configuration dictionary (from :func:`config.load_config`).
    fix:
        If *True*, apply safe normalizations to SKILL.md in-place.

    Returns
    -------
    ValidationResult
        Result object containing status, errors, warnings, and applied fixes.
    """
    slug = skill_path.name
    result = ValidationResult(slug=slug)

    skill_md_path = skill_path / "SKILL.md"
    if not skill_md_path.exists():
        result.add_error("SKILL.md is missing from the skill folder")
        return result

    # --- Parse ---
    try:
        frontmatter, body = parse_skill_md(skill_md_path)
    except ValueError as exc:
        result.add_error(f"Frontmatter parse error: {exc}")
        return result

    # --- Validate ---
    _check_name(frontmatter.get("name"), slug, result)
    _check_description(frontmatter.get("description"), config, result)
    _check_optional_fields(frontmatter, result)
    _check_body(body, skill_path, config, result)
    _check_safety(skill_path, frontmatter, body, config, result)

    # --- Fix ---
    if fix:
        frontmatter, body = _apply_fixes(skill_path, frontmatter, body, result)
        if result.fixes_applied:
            _write_skill_md(skill_path, frontmatter, body)

    # --- Quarantine if invalid ---
    if result.status == "invalid":
        try:
            _quarantine_skill(skill_path, slug, result, config)
        except OSError as exc:
            result.errors.append(f"[quarantine] Failed to move skill: {exc}")

    return result


def validate_all(
    config: dict,
    fix: bool = False,
    skill_filter: str | None = None,
) -> list[ValidationResult]:
    """
    Validate every skill in the vault's skills directory.

    Parameters
    ----------
    config:
        Loaded configuration dictionary.
    fix:
        If *True*, apply safe normalizations to each skill in-place.
    skill_filter:
        If given, validate only the skill whose slug matches this string.

    Returns
    -------
    list[ValidationResult]
        One result per skill folder examined.
    """
    vault_cfg: dict = config.get("vault", {})
    skills_dir = Path(vault_cfg.get("skills_dir", "DevCrew-Vault/skills"))

    if not skills_dir.exists():
        return []

    results: list[ValidationResult] = []
    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue
        slug = skill_path.name
        if skill_filter is not None and slug != skill_filter:
            continue
        results.append(validate_skill(skill_path, config, fix=fix))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_summary(results: list[ValidationResult]) -> None:
    total = len(results)
    valid = sum(1 for r in results if r.status == "valid")
    warnings = sum(1 for r in results if r.status == "valid-with-warnings")
    invalid = sum(1 for r in results if r.status == "invalid")

    print(f"\n{'=' * 60}")
    print(f"Skill Vault Validation — {total} skill(s) checked")
    print(f"{'=' * 60}")
    print(f"  ✅  Valid             : {valid}")
    print(f"  ⚠️   Valid w/ warnings : {warnings}")
    print(f"  ❌  Invalid           : {invalid}")
    print(f"{'=' * 60}")

    for r in results:
        icon = {"valid": "✅", "valid-with-warnings": "⚠️ ", "invalid": "❌"}.get(r.status, "?")
        print(f"\n{icon} [{r.slug}] — {r.status}")
        for err in r.errors:
            print(f"    ERROR   : {err}")
        for w in r.warnings:
            print(f"    WARNING : {w}")
        for fix in r.fixes_applied:
            print(f"    FIX     : {fix}")


def _write_report(results: list[ValidationResult], output_path: Path) -> None:
    data = {
        "summary": {
            "total": len(results),
            "valid": sum(1 for r in results if r.status == "valid"),
            "valid_with_warnings": sum(1 for r in results if r.status == "valid-with-warnings"),
            "invalid": sum(1 for r in results if r.status == "invalid"),
        },
        "skills": [r.as_dict() for r in results],
    }
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[report] Written to {output_path}")


def main(argv: list[str] | None = None) -> None:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Validate DevCrew AI Skill Vault SKILL.md packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--fix", action="store_true", help="Apply safe normalizations")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Emit validation-report.json and print human-readable summary",
    )
    parser.add_argument("--skill", metavar="SLUG", help="Validate only one skill by slug")
    parser.add_argument("--config", metavar="PATH", help="Path to devcrew.config.yaml")
    args = parser.parse_args(argv)

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    results = validate_all(config, fix=args.fix, skill_filter=args.skill)

    if args.report:
        _print_summary(results)
        _write_report(results, Path("validation-report.json"))
    else:
        _print_summary(results)

    # Exit non-zero if any skill is invalid
    if any(r.status == "invalid" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()


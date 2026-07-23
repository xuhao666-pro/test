#!/usr/bin/env python3
"""Plan and apply auditable cleanup of versioned SOP Skill packages."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PACKAGE_RE = re.compile(r"^ai-sop-(coordinator|member)-skill-v(\d+(?:\.\d+)*)$")
PACKAGE_TOKEN_RE = re.compile(r"ai-sop-(?:coordinator|member)-skill-v\d+(?:\.\d+)*")
TEXT_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".txt"}
CANONICAL_RETENTION_POLICY = Path(".github/sop-skill-retention.json")
SAFE_CACHE_DIR_NAMES = {
    "__pycache__",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
}
SAFE_CACHE_FILE_NAMES = {".coverage", "coverage.xml"}
SAFE_CACHE_SUFFIXES = {".pyc", ".pyo"}


class CleanupError(RuntimeError):
    pass


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, encoding="utf-8", capture_output=True
    )
    if check and result.returncode != 0:
        raise CleanupError(result.stderr.strip() or result.stdout.strip())
    return result


def version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CleanupError(f"Expected JSON object: {path}")
    return value


def discover_packages(root: Path) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        match = PACKAGE_RE.fullmatch(path.name)
        if not match:
            continue
        role, directory_version = match.groups()
        manifest_path = path / "package-manifest.json"
        manifest = load_json(manifest_path) if manifest_path.is_file() else {}
        manifest_version = str(manifest.get("package_version") or directory_version)
        if manifest_version != directory_version:
            raise CleanupError(
                f"Package directory/manifest version mismatch: {path.name} / {manifest_version}"
            )
        packages.append(
            {
                "path": path.name,
                "role": role,
                "version": directory_version,
                "release_status": str(manifest.get("release_status") or "legacy"),
                "build_id": str(manifest.get("build_id") or ""),
            }
        )
    return packages


def referenced_package_paths(root: Path, reference_roots: list[str]) -> dict[str, list[str]]:
    references: dict[str, list[str]] = {}
    for relative_root in reference_roots:
        base = (root / relative_root).resolve()
        if not base.exists() or not base.is_relative_to(root.resolve()):
            continue
        paths = [base] if base.is_file() else base.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for match in PACKAGE_TOKEN_RE.finditer(text):
                references.setdefault(match.group(0), []).append(
                    path.relative_to(root).as_posix()
                )
    return {key: sorted(set(value)) for key, value in references.items()}


def runtime_package_paths(root: Path) -> dict[str, list[str]]:
    """Return package roots named by trusted runtime-lock source records.

    A runtime's own ``SKILL_VERSION`` is deliberately not used to reconstruct a
    package directory name.  A unified package may expose several exact runtime
    identities, so package ownership comes from the lock's repository-relative
    ``source`` path instead.
    """
    result: dict[str, list[str]] = {}
    lock_path = root / ".github" / "sop-runtime-lock.json"
    if not lock_path.is_file():
        return result
    lock = load_json(lock_path)
    runtimes = lock.get("runtimes")
    if not isinstance(runtimes, dict):
        raise CleanupError("Runtime lock must contain a runtimes object")
    for runtime_name, record in runtimes.items():
        if not isinstance(record, dict):
            raise CleanupError(f"Runtime lock record must be an object: {runtime_name}")
        source = str(record.get("source", "")).replace("\\", "/").strip()
        source_path = Path(source)
        if (
            not source
            or source_path.is_absolute()
            or ".." in source_path.parts
            or not source_path.parts
            or not PACKAGE_RE.fullmatch(source_path.parts[0])
        ):
            raise CleanupError(f"Runtime lock source is not package-owned: {runtime_name}")
        package = source_path.parts[0]
        result.setdefault(package, []).append(
            f".github/sop-runtime-lock.json#runtimes.{runtime_name}"
        )
    return {key: sorted(set(value)) for key, value in result.items()}


def canonical_token(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()[:16]


def build_plan(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    packages = discover_packages(root)
    reference_roots = [str(value) for value in config.get("reference_roots", ["sop"])]
    references = referenced_package_paths(root, reference_roots)
    runtime = runtime_package_paths(root)
    pinned = {str(value) for value in config.get("pinned_packages", [])}
    retain_counts = config.get("retain_latest_stable", {})
    latest: set[str] = set()
    for role in ("coordinator", "member"):
        count = max(0, int(retain_counts.get(role, 1)))
        stable = sorted(
            (
                item
                for item in packages
                if item["role"] == role and item["release_status"] == "stable"
            ),
            key=lambda item: version_key(item["version"]),
            reverse=True,
        )
        latest.update(item["path"] for item in stable[:count])

    retained: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for package in packages:
        reasons: list[str] = []
        path = package["path"]
        if path in pinned:
            reasons.append("policy-pin")
        if path in latest:
            reasons.append("latest-stable-retention")
        if path in references:
            reasons.append("repository-reference")
        if path in runtime:
            reasons.append("installed-runtime-validator")
        item = {
            **package,
            "reasons": reasons or ["unreferenced-superseded-release"],
            "reference_files": references.get(path, []),
            "runtime_files": runtime.get(path, []),
        }
        (retained if reasons else candidates).append(item)

    head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    token_payload = {
        "schema_version": "1.0",
        "repository_head": head,
        "policy": config,
        "candidate_paths": [item["path"] for item in candidates],
        "retained_paths": [item["path"] for item in retained],
    }
    return {
        **token_payload,
        "retained": retained,
        "candidates": candidates,
        "summary": {
            "package_count": len(packages),
            "retained_count": len(retained),
            "candidate_count": len(candidates),
        },
        "confirmation_token": canonical_token(token_payload),
        "apply_effect": "stage-git-removals-and-audit-record-only",
    }


def ensure_clean_tracked_worktree(root: Path) -> None:
    unstaged = run_git(root, "diff", "--quiet", check=False)
    staged = run_git(root, "diff", "--cached", "--quiet", check=False)
    if unstaged.returncode != 0 or staged.returncode != 0:
        raise CleanupError("Tracked worktree changes exist; commit or stash them before cleanup")


def untracked_nonignored_files(root: Path, relative: str) -> list[str]:
    result = run_git(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        relative,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def ignored_files(root: Path, relative: str) -> list[str]:
    result = run_git(
        root,
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        "--",
        relative,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_safe_cache_relative(relative: Path) -> bool:
    return (
        any(part in SAFE_CACHE_DIR_NAMES for part in relative.parts)
        or relative.name in SAFE_CACHE_FILE_NAMES
        or relative.name.startswith(".coverage.")
        or relative.suffix.lower() in SAFE_CACHE_SUFFIXES
    )


def unsafe_residual_entries(candidate: Path) -> list[str]:
    unsafe: list[str] = []
    for entry in candidate.rglob("*"):
        if entry.is_symlink():
            unsafe.append(entry.relative_to(candidate).as_posix())
        elif entry.is_file() and not is_safe_cache_relative(
            entry.relative_to(candidate)
        ):
            unsafe.append(entry.relative_to(candidate).as_posix())
    return sorted(unsafe)


def apply_plan(root: Path, config_path: Path, token: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise CleanupError("Cleanup reason cannot be blank")
    if config_path.resolve() != (root / CANONICAL_RETENTION_POLICY).resolve():
        raise CleanupError(
            "Cleanup apply requires the canonical .github/sop-skill-retention.json policy"
        )
    ensure_clean_tracked_worktree(root)
    plan = build_plan(root, config_path)
    if token != plan["confirmation_token"]:
        raise CleanupError("Confirmation token does not match the current cleanup plan")
    paths = [item["path"] for item in plan["candidates"]]
    if not paths:
        raise CleanupError("Cleanup plan has no candidates")
    candidates: list[Path] = []
    untracked: list[str] = []
    unsafe_ignored: list[str] = []
    for relative in paths:
        candidate = root / relative
        resolved = candidate.resolve()
        if (
            candidate.is_symlink()
            or resolved.parent != root.resolve()
            or not PACKAGE_RE.fullmatch(candidate.name)
        ):
            raise CleanupError(f"Unsafe cleanup path: {relative}")
        candidates.append(candidate)
        untracked.extend(untracked_nonignored_files(root, relative))
        for ignored in ignored_files(root, relative):
            inside = Path(ignored).relative_to(relative)
            if not is_safe_cache_relative(inside):
                unsafe_ignored.append(ignored)
    if untracked:
        raise CleanupError(
            "Cleanup candidates contain untracked non-ignored files: "
            + ", ".join(sorted(untracked))
        )
    if unsafe_ignored:
        raise CleanupError(
            "Cleanup candidates contain ignored files outside the cache allowlist: "
            + ", ".join(sorted(unsafe_ignored))
        )
    run_git(root, "rm", "-r", "--", *paths)
    for candidate in candidates:
        if candidate.exists():
            unsafe = unsafe_residual_entries(candidate)
            if unsafe:
                raise CleanupError(
                    f"Cleanup target {candidate.name} contains unsafe residual files: "
                    + ", ".join(unsafe)
                )
            shutil.rmtree(candidate)
        if candidate.exists():
            raise CleanupError(f"Cleanup target still exists: {candidate.name}")
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    audit = {
        "schema_version": "1.0",
        "status": "staged",
        "applied_at": timestamp,
        "repository_head_before_apply": plan["repository_head"],
        "confirmation_token": token,
        "reason": reason.strip(),
        "removed_packages": paths,
        "retained_packages": [item["path"] for item in plan["retained"]],
        "history_preserved_by": "git",
        "commit_and_push_required": True,
    }
    audit_dir = root / ".github/skill-cleanup/history"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"{timestamp[:10]}-{token}.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_git(root, "add", "--", audit_path.relative_to(root).as_posix())
    return {**audit, "audit_path": audit_path.relative_to(root).as_posix()}


def render_text(plan: dict[str, Any]) -> str:
    lines = [
        f"Packages: {plan['summary']['package_count']}",
        f"Retained: {plan['summary']['retained_count']}",
        f"Cleanup candidates: {plan['summary']['candidate_count']}",
        "",
        "Retained:",
    ]
    lines.extend(
        f"  - {item['path']}: {', '.join(item['reasons'])}" for item in plan["retained"]
    )
    lines.append("Cleanup candidates:")
    lines.extend(f"  - {item['path']}" for item in plan["candidates"])
    lines.extend(["", f"Confirmation token: {plan['confirmation_token']}"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply"))
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument(
        "--config", default=".github/sop-skill-retention.json", help="policy path"
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--confirm-token")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()
    try:
        root = Path(args.project_root).resolve()
        config_path = (root / args.config).resolve()
        if args.command == "plan":
            result = build_plan(root, config_path)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else render_text(result))
        else:
            if not args.confirm_token:
                raise CleanupError("apply requires --confirm-token")
            result = apply_plan(root, config_path, args.confirm_token, args.reason)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except CleanupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

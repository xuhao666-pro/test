#!/usr/bin/env python3
"""Plan and apply auditable cleanup of versioned SOP Skill packages."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PACKAGE_RE = re.compile(r"^ai-sop-(coordinator|member)-skill-v(\d+(?:\.\d+)*)$")
PACKAGE_TOKEN_RE = re.compile(r"ai-sop-(?:coordinator|member)-skill-v\d+(?:\.\d+)*")
SKILL_VERSION_RE = re.compile(r'^SKILL_VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
TEXT_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".txt"}


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
        for path in base.rglob("*"):
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
    result: dict[str, list[str]] = {}
    scripts = [root / ".github/scripts/sop_coordinator_cli.py"]
    scripts.extend(sorted((root / ".github/scripts").glob("sop_member_cli*.py")))
    for path in scripts:
        if not path.is_file():
            continue
        match = SKILL_VERSION_RE.search(path.read_text(encoding="utf-8"))
        if not match:
            continue
        role = "coordinator" if "coordinator" in path.name else "member"
        package = f"ai-sop-{role}-skill-v{match.group(1)}"
        result.setdefault(package, []).append(path.relative_to(root).as_posix())
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


def apply_plan(root: Path, config_path: Path, token: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise CleanupError("Cleanup reason cannot be blank")
    ensure_clean_tracked_worktree(root)
    plan = build_plan(root, config_path)
    if token != plan["confirmation_token"]:
        raise CleanupError("Confirmation token does not match the current cleanup plan")
    paths = [item["path"] for item in plan["candidates"]]
    if not paths:
        raise CleanupError("Cleanup plan has no candidates")
    for relative in paths:
        candidate = (root / relative).resolve()
        if candidate.parent != root.resolve() or not PACKAGE_RE.fullmatch(candidate.name):
            raise CleanupError(f"Unsafe cleanup path: {relative}")
    run_git(root, "rm", "-r", "--", *paths)
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

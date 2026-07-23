#!/usr/bin/env python3
"""Validate the repository-level SOP system before project activation."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PATH = ROOT / ".github" / "sop-system.json"
LOCK_PATH = ROOT / ".github" / "sop-runtime-lock.json"
ALLOWED_BOOTSTRAP_WORKFLOWS = {"sop-system-validate.yml"}
PACKAGE_RE = re.compile(r"^ai-sop-(?:coordinator|member)-skill-v\d+(?:\.\d+)*$")
CLEANUP_AUDIT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([0-9a-f]{16})\.json$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
CLEANUP_HISTORY_RELATIVE = Path(".github/skill-cleanup/history")
RETENTION_POLICY_RELATIVE = ".github/sop-skill-retention.json"
CLEANUP_AUDIT_FIELDS = {
    "schema_version",
    "status",
    "applied_at",
    "repository_head_before_apply",
    "confirmation_token",
    "reason",
    "removed_packages",
    "retained_packages",
    "history_preserved_by",
    "commit_and_push_required",
}
EXPECTED_RUNTIME_NAMES = {
    "predevelopment_coordinator",
    "predevelopment_member",
    "legacy_predevelopment_member",
    "development_coordinator",
    "development_member",
}
REQUIRED_PACKAGES = {
    "ai-sop-coordinator-skill-v1.8.4",
    "ai-sop-coordinator-skill-v2.1.0",
    "ai-sop-coordinator-skill-v2.1.1",
    "ai-sop-member-skill-v2.1.0",
}
UNIFIED_PACKAGE_RUNTIMES = {
    "ai-sop-coordinator-skill-v2.1.1": {
        "package_name": "ai-sop-coordinator-skill",
        "package_build_id": "coordinator-package-2.1.1-unified-runtimes-v1",
        "profiles": {
            "predevelopment": (
                "1.8.5",
                "coordinator-cli-1.8.5-unified-member-package-v1",
            ),
            "development_delivery": ("2.0.0", "coordinator-dev-cli-2.0.0-v1"),
        },
        "trusted_assets": {
            "bundled_remote_validator": (
                "ai-sop-coordinator/assets/remote-validator/member_cli.py",
                "1.8.1",
                "member-cli-1.8.1-assignment-acceptance-v1",
            ),
            "bundled_legacy_remote_validator": (
                "ai-sop-coordinator/assets/remote-validator/member_cli_1_8_0.py",
                "1.8.0",
                "member-cli-1.8.0-ai-dialogue-exact-release-v1",
            ),
        },
    },
    "ai-sop-member-skill-v2.1.0": {
        "package_name": "ai-sop-member-skill",
        "package_build_id": "member-package-2.1.0-unified-runtimes-v1",
        "profiles": {
            "legacy_predevelopment": (
                "1.8.0",
                "member-cli-1.8.0-ai-dialogue-exact-release-v1",
            ),
            "predevelopment": (
                "1.8.1",
                "member-cli-1.8.1-assignment-acceptance-v1",
            ),
            "development_delivery": ("2.0.0", "member-dev-cli-2.0.0-v1"),
        },
    },
}
BOOTSTRAP_FORBIDDEN_PATHS = {
    "sop",
    "dashboard",
    "projectcode",
}
CAPABILITY_WORKFLOWS = {
    "dashboard": {"sop-readme-dashboard.yml"},
    "dashboard_actions": {"sop-dashboard-actions.yml"},
    "github_issue_notifications": {"sop-notifications.yml"},
    "dingtalk_notifications": {"sop-notifications.yml"},
    "automatic_skill_cleanup": {
        "sop-skill-cleanup.yml",
        "sop-skill-cleanup-validate.yml",
    },
    "remote_feedback": {
        "sop-member-signal.yml",
        "sop-member-feedback.yml",
    },
}
SKIP_SCAN_PARTS = {".git", "__pycache__", "tests"}
TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = {
    "DingTalk webhook access token": re.compile(
        r"https://oapi\.dingtalk\.com/robot/send\?access_token=[A-Za-z0-9_-]{16,}"
    ),
    "mainland China mobile number": re.compile(
        r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"
    ),
}


class ValidationError(RuntimeError):
    pass


def run_git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise ValidationError(f"git {' '.join(args)} failed: {detail}")
    return result


def canonical_token(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]


def git_package_set(root: Path, treeish: str) -> set[str]:
    result = run_git(root, "ls-tree", "-d", "--name-only", treeish)
    return {
        line.strip()
        for line in result.stdout.splitlines()
        if PACKAGE_RE.fullmatch(line.strip())
    }


def index_package_set(root: Path) -> set[str]:
    result = run_git(root, "ls-files")
    return {
        path.split("/", 1)[0]
        for path in result.stdout.splitlines()
        if path and PACKAGE_RE.fullmatch(path.split("/", 1)[0])
    }


def validate_package_removals(
    root: Path,
    audit_relative: str,
    removed: list[str],
    *diff_args: str,
) -> None:
    result = run_git(root, *diff_args)
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        related = {
            value.split("/", 1)[0]
            for value in fields[1:]
            if value and value.split("/", 1)[0] in removed
        }
        if related and status != "D":
            raise ValidationError(
                f"cleanup package content was not deleted in place: {audit_relative}"
            )
        seen.update(related)
    if seen != set(removed):
        raise ValidationError(
            f"cleanup audit package deletions are incomplete: {audit_relative}"
        )


def parse_git_json(root: Path, treeish: str, relative: str) -> dict[str, Any]:
    result = run_git(root, "show", f"{treeish}:{relative}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"{relative} at {treeish} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{relative} at {treeish} must contain an object")
    return value


def validate_cleanup_audit(root: Path, path: Path) -> None:
    relative = path.relative_to(root).as_posix()
    match = CLEANUP_AUDIT_RE.fullmatch(path.name)
    if not match:
        raise ValidationError(f"invalid cleanup audit filename: {relative}")
    if path.is_symlink() or not path.is_file():
        raise ValidationError(f"cleanup audit must be a regular file: {relative}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot load cleanup audit {relative}: {exc}") from exc
    if not isinstance(record, dict) or set(record) != CLEANUP_AUDIT_FIELDS:
        raise ValidationError(f"cleanup audit fields are not exact: {relative}")
    if record.get("schema_version") != "1.0" or record.get("status") != "staged":
        raise ValidationError(f"cleanup audit schema or status is invalid: {relative}")

    applied_at = record.get("applied_at")
    try:
        applied = dt.datetime.fromisoformat(str(applied_at))
    except ValueError as exc:
        raise ValidationError(f"cleanup audit timestamp is invalid: {relative}") from exc
    if applied.tzinfo is None or applied.utcoffset() != dt.timedelta(0):
        raise ValidationError(f"cleanup audit timestamp must be UTC: {relative}")
    filename_date, filename_token = match.groups()
    if applied.date().isoformat() != filename_date:
        raise ValidationError(f"cleanup audit filename date mismatch: {relative}")

    before = record.get("repository_head_before_apply")
    token = record.get("confirmation_token")
    if not isinstance(before, str) or not GIT_COMMIT_RE.fullmatch(before):
        raise ValidationError(f"cleanup audit repository head is invalid: {relative}")
    if token != filename_token:
        raise ValidationError(f"cleanup audit token does not match filename: {relative}")
    if not isinstance(record.get("reason"), str) or not record["reason"].strip():
        raise ValidationError(f"cleanup audit reason is missing: {relative}")
    if len(record["reason"]) > 1000:
        raise ValidationError(f"cleanup audit reason is too long: {relative}")

    removed = record.get("removed_packages")
    retained = record.get("retained_packages")
    for label, values in (("removed", removed), ("retained", retained)):
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, str) for value in values)
            or values != sorted(set(values))
            or any(not PACKAGE_RE.fullmatch(value) for value in values)
        ):
            raise ValidationError(
                f"cleanup audit {label} package list is invalid: {relative}"
            )
    if set(removed) & set(retained):
        raise ValidationError(f"cleanup audit package lists overlap: {relative}")
    if (
        record.get("history_preserved_by") != "git"
        or record.get("commit_and_push_required") is not True
    ):
        raise ValidationError(f"cleanup audit preservation contract is invalid: {relative}")

    policy = parse_git_json(root, before, RETENTION_POLICY_RELATIVE)
    payload = {
        "schema_version": "1.0",
        "repository_head": before,
        "policy": policy,
        "candidate_paths": removed,
        "retained_paths": retained,
    }
    if token != canonical_token(payload):
        raise ValidationError(f"cleanup audit confirmation token is invalid: {relative}")

    before_packages = git_package_set(root, before)
    if before_packages != set(removed) | set(retained):
        raise ValidationError(f"cleanup audit does not match its parent package set: {relative}")

    in_head = run_git(root, "cat-file", "-e", f"HEAD:{relative}", check=False)
    if in_head.returncode != 0:
        current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
        if current_head != before:
            raise ValidationError(f"staged cleanup audit is not based on HEAD: {relative}")
        status = run_git(
            root, "diff", "--cached", "--name-status", "--", relative
        ).stdout.strip()
        if status != f"A\t{relative}":
            raise ValidationError(f"cleanup audit is not staged as a new file: {relative}")
        staged_blob = run_git(root, "rev-parse", f":{relative}").stdout.strip()
        worktree_blob = run_git(root, "hash-object", relative).stdout.strip()
        if staged_blob != worktree_blob:
            raise ValidationError(f"cleanup audit differs from its staged blob: {relative}")
        if index_package_set(root) != set(retained):
            raise ValidationError(f"staged cleanup package set is inconsistent: {relative}")
        validate_package_removals(
            root,
            relative,
            removed,
            "diff",
            "--cached",
            "--name-status",
            "--find-renames",
        )
        return

    introductions = [
        line.strip()
        for line in run_git(
            root, "log", "--diff-filter=A", "--format=%H", "--", relative
        ).stdout.splitlines()
        if line.strip()
    ]
    if len(introductions) != 1:
        raise ValidationError(f"cleanup audit must have one introduction commit: {relative}")
    introduction = introductions[0]
    ancestry = run_git(
        root, "rev-list", "--parents", "-n", "1", introduction
    ).stdout.split()
    if len(ancestry) != 2 or ancestry[1] != before:
        raise ValidationError(f"cleanup audit parent commit mismatch: {relative}")
    if run_git(
        root, "merge-base", "--is-ancestor", introduction, "HEAD", check=False
    ).returncode != 0:
        raise ValidationError(f"cleanup audit commit is not reachable from HEAD: {relative}")
    introduced_blob = run_git(
        root, "rev-parse", f"{introduction}:{relative}"
    ).stdout.strip()
    head_blob = run_git(root, "rev-parse", f"HEAD:{relative}").stdout.strip()
    current_blob = run_git(root, "hash-object", relative).stdout.strip()
    if head_blob != introduced_blob or current_blob != head_blob:
        raise ValidationError(f"cleanup audit was modified after introduction: {relative}")
    if git_package_set(root, introduction) != set(retained):
        raise ValidationError(f"cleanup commit package set is inconsistent: {relative}")
    validate_package_removals(
        root,
        relative,
        removed,
        "diff",
        "--name-status",
        "--find-renames",
        before,
        introduction,
    )


def validate_cleanup_history(root: Path = ROOT) -> None:
    history = root / CLEANUP_HISTORY_RELATIVE
    history_prefix = CLEANUP_HISTORY_RELATIVE.as_posix() + "/"
    historical = {
        line.strip()
        for line in run_git(
            root,
            "log",
            "--diff-filter=A",
            "--name-only",
            "--format=",
            "HEAD",
            "--",
            CLEANUP_HISTORY_RELATIVE.as_posix(),
        ).stdout.splitlines()
        if line.strip().startswith(history_prefix)
    }
    tracked_at_head = {
        line.strip()
        for line in run_git(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            "HEAD",
            "--",
            CLEANUP_HISTORY_RELATIVE.as_posix(),
        ).stdout.splitlines()
        if line.strip().startswith(history_prefix)
    }
    if historical != tracked_at_head:
        raise ValidationError(
            "cleanup audit records introduced in repository history must remain present"
        )
    staged_additions: set[str] = set()
    for line in run_git(
        root,
        "diff",
        "--cached",
        "--name-status",
        "--",
        CLEANUP_HISTORY_RELATIVE.as_posix(),
    ).stdout.splitlines():
        fields = line.split("\t")
        if len(fields) == 2 and fields[0] == "A":
            staged_additions.add(fields[1])
    expected = tracked_at_head | staged_additions
    if not history.exists():
        if expected:
            raise ValidationError("cleanup audit records are missing from the worktree")
        return
    if history.is_symlink() or not history.is_dir():
        raise ValidationError("cleanup history must be a regular directory")
    entries = sorted(history.iterdir())
    actual = {entry.relative_to(root).as_posix() for entry in entries}
    if actual != expected:
        raise ValidationError(
            "cleanup history contents do not match immutable Git audit records"
        )
    for entry in entries:
        if entry.is_dir() or entry.is_symlink():
            raise ValidationError(
                "cleanup history may contain only direct regular JSON records"
            )
        validate_cleanup_audit(root, entry)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def script_identity(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    version = re.search(r'^SKILL_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    build = re.search(r'^BUILD_ID\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not version or not build:
        raise ValidationError(f"runtime identity missing in {path.relative_to(ROOT)}")
    return version.group(1), build.group(1)


def repository_path(relative: str, *, label: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute():
        raise ValidationError(f"{label} must be repository-relative")
    path = (ROOT / raw).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValidationError(f"{label} escapes the repository") from exc
    return path


def package_path(package_root: Path, relative: str, *, label: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute():
        raise ValidationError(f"{label} must be package-relative")
    path = (package_root / raw).resolve()
    try:
        path.relative_to(package_root.resolve())
    except ValueError as exc:
        raise ValidationError(f"{label} escapes its package") from exc
    return path


def validate_package_validation(package_root: Path, manifest: dict[str, Any]) -> None:
    path = package_root / "package-validation.json"
    validation = load_json(path)
    for field in ("package_name", "package_version"):
        if validation.get(field) != manifest.get(field):
            raise ValidationError(
                f"{path.relative_to(ROOT)} {field} does not match package manifest"
            )
    if not str(validation.get("validated_at", "")).strip():
        raise ValidationError(f"{path.relative_to(ROOT)} validated_at is missing")
    results = validation.get("results")
    if not isinstance(results, list) or not results:
        raise ValidationError(f"{path.relative_to(ROOT)} must contain validation results")
    for index, result in enumerate(results):
        if (
            not isinstance(result, dict)
            or not str(result.get("check", "")).strip()
            or result.get("status") != "passed"
        ):
            raise ValidationError(
                f"{path.relative_to(ROOT)} result {index} is not an explicit pass"
            )


def validate_unified_package(
    package_name: str, expected: dict[str, Any]
) -> set[str]:
    package_root = ROOT / package_name
    manifest_path = package_root / "package-manifest.json"
    manifest = load_json(manifest_path)
    directory_version = package_name.rsplit("-v", 1)[1]
    if manifest.get("manifest_schema_version") != "2.1":
        raise ValidationError(f"{manifest_path.relative_to(ROOT)} schema must be 2.1")
    if manifest.get("package_name") != expected["package_name"]:
        raise ValidationError(f"{manifest_path.relative_to(ROOT)} package_name mismatch")
    if manifest.get("package_version") != directory_version:
        raise ValidationError(f"{manifest_path.relative_to(ROOT)} package_version mismatch")
    if manifest.get("release_status") != "stable":
        raise ValidationError(f"{manifest_path.relative_to(ROOT)} must be stable")
    if manifest.get("build_id") != expected["package_build_id"]:
        raise ValidationError(f"{manifest_path.relative_to(ROOT)} package build_id mismatch")

    releases = manifest.get("runtime_releases")
    expected_profiles = expected["profiles"]
    if not isinstance(releases, dict) or set(releases) != set(expected_profiles):
        raise ValidationError(
            f"{manifest_path.relative_to(ROOT)} runtime profiles must be exact"
        )

    trusted_sources: set[str] = set()
    for profile, (expected_version, expected_build) in expected_profiles.items():
        record = releases.get(profile)
        if not isinstance(record, dict):
            raise ValidationError(f"runtime profile {package_name}/{profile} must be an object")
        expected_runtime_status = (
            "legacy" if profile == "legacy_predevelopment" else "stable"
        )
        if record.get("release_status") != expected_runtime_status:
            raise ValidationError(
                f"runtime profile {package_name}/{profile} status is invalid"
            )
        if (
            record.get("skill_version") != expected_version
            or record.get("build_id") != expected_build
        ):
            raise ValidationError(f"runtime profile {package_name}/{profile} identity mismatch")
        stage_ids = record.get("stage_ids")
        expected_stage_ids = (
            ["A", "B", "C"]
            if profile in {"predevelopment", "legacy_predevelopment"}
            else ["D", "E"]
        )
        if (
            not isinstance(stage_ids, list)
            or stage_ids != expected_stage_ids
        ):
            raise ValidationError(
                f"runtime profile {package_name}/{profile} stage_ids invalid"
            )
        for field in ("protocol_version", "project_schema_version"):
            if not str(record.get(field, "")).strip():
                raise ValidationError(
                    f"runtime profile {package_name}/{profile} {field} is missing"
                )

        cli_relative = str(record.get("cli_path", "")).strip()
        protocol_relative = str(record.get("protocol_path", "")).strip()
        if not cli_relative or not protocol_relative:
            raise ValidationError(
                f"runtime profile {package_name}/{profile} paths are incomplete"
            )
        cli_path = package_path(
            package_root, cli_relative, label=f"runtime {package_name}/{profile} cli_path"
        )
        protocol_path = package_path(
            package_root,
            protocol_relative,
            label=f"runtime {package_name}/{profile} protocol_path",
        )
        if not cli_path.is_file() or not protocol_path.is_file():
            raise ValidationError(f"runtime profile {package_name}/{profile} asset is missing")
        cli_version, cli_build = script_identity(cli_path)
        if cli_version != expected_version or cli_build != expected_build:
            raise ValidationError(f"runtime profile {package_name}/{profile} CLI mismatch")
        protocol = load_json(protocol_path)
        expected_protocol = {
            "skill_version": expected_version,
            "build_id": expected_build,
            "protocol_version": record["protocol_version"],
            "project_schema_version": record["project_schema_version"],
        }
        if any(protocol.get(key) != value for key, value in expected_protocol.items()):
            raise ValidationError(f"runtime profile {package_name}/{profile} protocol mismatch")
        allowed_protocol_statuses = (
            {"stable", "legacy"}
            if profile == "legacy_predevelopment"
            else {"stable"}
        )
        if protocol.get("release_status") not in allowed_protocol_statuses:
            raise ValidationError(
                f"runtime profile {package_name}/{profile} protocol status is invalid"
            )
        trusted_sources.add(f"{package_name}/{Path(cli_relative).as_posix()}")

    runtime_metadata = manifest.get("runtime")
    trusted_assets = expected.get("trusted_assets", {})
    if trusted_assets and not isinstance(runtime_metadata, dict):
        raise ValidationError(f"{manifest_path.relative_to(ROOT)} runtime metadata missing")
    for field, (relative, expected_version, expected_build) in trusted_assets.items():
        if runtime_metadata.get(field) != relative:
            raise ValidationError(
                f"{manifest_path.relative_to(ROOT)} {field} does not match its trusted asset"
            )
        asset = package_path(package_root, relative, label=f"trusted asset {field}")
        if not asset.is_file():
            raise ValidationError(f"trusted asset is missing: {asset.relative_to(ROOT)}")
        asset_version, asset_build = script_identity(asset)
        if asset_version != expected_version or asset_build != expected_build:
            raise ValidationError(f"trusted asset identity mismatch: {asset.relative_to(ROOT)}")
        trusted_sources.add(f"{package_name}/{Path(relative).as_posix()}")

    validate_package_validation(package_root, manifest)
    return trusted_sources


def validate_packages() -> set[str]:
    installed = {
        path.name
        for path in ROOT.iterdir()
        if path.is_dir() and PACKAGE_RE.fullmatch(path.name)
    }
    if installed != REQUIRED_PACKAGES:
        missing = sorted(REQUIRED_PACKAGES - installed)
        unexpected = sorted(installed - REQUIRED_PACKAGES)
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if unexpected:
            details.append("unexpected=" + ",".join(unexpected))
        raise ValidationError("installed Skill package set mismatch: " + "; ".join(details))

    legacy_manifest = load_json(
        ROOT / "ai-sop-coordinator-skill-v1.8.4" / "package-manifest.json"
    )
    if (
        legacy_manifest.get("package_name") != "ai-sop-coordinator-skill"
        or legacy_manifest.get("package_version") != "1.8.4"
        or legacy_manifest.get("release_status") != "stable"
    ):
        raise ValidationError("Coordinator 1.8.4 lineage package identity mismatch")

    previous_manifest = load_json(
        ROOT / "ai-sop-coordinator-skill-v2.1.0" / "package-manifest.json"
    )
    if (
        previous_manifest.get("package_name") != "ai-sop-coordinator-skill"
        or previous_manifest.get("package_version") != "2.1.0"
        or previous_manifest.get("release_status") != "stable"
    ):
        raise ValidationError("Coordinator 2.1.0 lineage package identity mismatch")

    trusted_sources: set[str] = set()
    for package_name, expected in UNIFIED_PACKAGE_RUNTIMES.items():
        trusted_sources.update(validate_unified_package(package_name, expected))
    return trusted_sources


def validate_runtime_lock(system: dict[str, Any], trusted_sources: set[str]) -> None:
    lock = load_json(LOCK_PATH)
    if lock.get("schema_version") != "1.0":
        raise ValidationError("runtime lock schema_version must be 1.0")
    runtimes = lock.get("runtimes")
    if not isinstance(runtimes, dict) or not runtimes:
        raise ValidationError("runtime lock must define runtimes")
    if set(runtimes) != EXPECTED_RUNTIME_NAMES:
        raise ValidationError("runtime lock must define the exact trusted runtimes")
    capabilities = system.get("capabilities", {})
    for name, record in runtimes.items():
        if not isinstance(record, dict):
            raise ValidationError(f"runtime {name} must be an object")
        relative = record.get("path")
        if not isinstance(relative, str) or not relative:
            raise ValidationError(f"runtime {name} path is missing")
        path = repository_path(relative, label=f"runtime {name} path")
        if not path.is_file():
            raise ValidationError(f"runtime {name} file is missing: {relative}")
        actual_hash = sha256(path)
        if actual_hash != record.get("sha256"):
            raise ValidationError(
                f"runtime {name} hash mismatch: {actual_hash} != {record.get('sha256')}"
            )
        version, build_id = script_identity(path)
        if version != record.get("version") or build_id != record.get("build_id"):
            raise ValidationError(f"runtime {name} identity does not match its lock")
        source_relative = record.get("source")
        if not isinstance(source_relative, str) or not source_relative:
            raise ValidationError(f"runtime {name} source is missing")
        normalized_source = Path(source_relative.replace("\\", "/")).as_posix()
        if normalized_source not in trusted_sources:
            raise ValidationError(
                f"runtime {name} source is not a declared trusted 2.1 runtime: "
                f"{source_relative}"
            )
        source = repository_path(source_relative, label=f"runtime {name} source")
        if not source.is_file() or sha256(source) != actual_hash:
            raise ValidationError(f"runtime {name} does not match its trusted package source")
        if name.startswith("development_"):
            expected_enabled = capabilities.get("development_de") is True
            if record.get("enabled") is not expected_enabled:
                raise ValidationError(
                    f"runtime {name} enabled flag must match development_de capability"
                )


def validate_secret_hygiene() -> None:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.name.startswith("test_"):
            continue
        relative = path.relative_to(ROOT)
        if any(part in SKIP_SCAN_PARTS for part in relative.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{relative}: possible {label}")
    if failures:
        raise ValidationError("credential hygiene failed:\n" + "\n".join(failures))


def validate_lifecycle() -> dict[str, Any]:
    system = load_json(SYSTEM_PATH)
    if system.get("schema_version") != "1.0":
        raise ValidationError("sop-system schema_version must be 1.0")
    lifecycle = system.get("lifecycle")
    if lifecycle not in {"bootstrap", "active"}:
        raise ValidationError("lifecycle must be bootstrap or active")
    capabilities = system.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        raise ValidationError("capabilities must be a non-empty object")
    if any(not isinstance(value, bool) for value in capabilities.values()):
        raise ValidationError("all capability flags must be booleans")
    if capabilities.get("predevelopment_ac") is not True:
        raise ValidationError("predevelopment_ac must remain enabled")
    if capabilities.get("github_issue_notifications") is not capabilities.get(
        "dingtalk_notifications"
    ):
        raise ValidationError(
            "github_issue_notifications and dingtalk_notifications must be enabled together"
        )

    if lifecycle == "bootstrap":
        if system.get("project_initialized") is not False:
            raise ValidationError("bootstrap requires project_initialized=false")
        if system.get("project_data_included") is not False:
            raise ValidationError("bootstrap requires project_data_included=false")
        enabled_project_capabilities = {
            name
            for name, enabled in capabilities.items()
            if name != "predevelopment_ac" and enabled
        }
        if enabled_project_capabilities:
            raise ValidationError(
                "bootstrap cannot enable project capabilities: "
                + ", ".join(sorted(enabled_project_capabilities))
            )
        for relative in BOOTSTRAP_FORBIDDEN_PATHS:
            if (ROOT / relative).exists():
                raise ValidationError(f"bootstrap repository must not contain {relative}")
        workflow_dir = ROOT / ".github" / "workflows"
        active = {
            path.name
            for path in workflow_dir.glob("*.y*ml")
            if path.is_file()
        }
        unexpected = active - ALLOWED_BOOTSTRAP_WORKFLOWS
        if unexpected:
            raise ValidationError(
                "bootstrap has unexpected active workflows: " + ", ".join(sorted(unexpected))
            )
    else:
        if system.get("project_initialized") is not True:
            raise ValidationError("active lifecycle requires project_initialized=true")
        if system.get("project_data_included") is not True:
            raise ValidationError("active lifecycle requires project_data_included=true")
        state_path = ROOT / "sop" / "project-state.yaml"
        if not state_path.is_file():
            raise ValidationError("active lifecycle requires sop/project-state.yaml")
        if not load_json(state_path):
            raise ValidationError("active project-state must not be empty")
        active_workflows = {
            path.name
            for path in (ROOT / ".github" / "workflows").glob("*.y*ml")
            if path.is_file()
        }
        for capability, required_workflows in CAPABILITY_WORKFLOWS.items():
            if capabilities.get(capability) is not True:
                continue
            missing = required_workflows - active_workflows
            if missing:
                raise ValidationError(
                    f"capability {capability} requires workflows: "
                    + ", ".join(sorted(missing))
                )
            for workflow_name in required_workflows:
                active_path = ROOT / ".github" / "workflows" / workflow_name
                template_path = (
                    ROOT / ".github" / "sop-templates" / "workflows" / workflow_name
                )
                if not template_path.is_file() or active_path.read_bytes() != template_path.read_bytes():
                    raise ValidationError(
                        f"active workflow must match hardened template: {workflow_name}"
                    )
    validate_cleanup_history()
    return system


def main() -> int:
    try:
        system = validate_lifecycle()
        trusted_sources = validate_packages()
        validate_runtime_lock(system, trusted_sources)
        validate_secret_hygiene()
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"SOP system validation passed (lifecycle={system['lifecycle']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

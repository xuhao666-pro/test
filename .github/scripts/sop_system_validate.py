#!/usr/bin/env python3
"""Validate the repository-level SOP system before project activation."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PATH = ROOT / ".github" / "sop-system.json"
LOCK_PATH = ROOT / ".github" / "sop-runtime-lock.json"
ALLOWED_BOOTSTRAP_WORKFLOWS = {"sop-system-validate.yml"}
EXPECTED_RUNTIME_NAMES = {
    "predevelopment_coordinator",
    "predevelopment_member",
    "legacy_predevelopment_member",
    "development_coordinator",
    "development_member",
}
REQUIRED_PACKAGES = {
    "ai-sop-coordinator-skill-v2.0.0",
    "ai-sop-coordinator-skill-v1.8.4",
    "ai-sop-member-skill-v2.0.0",
    "ai-sop-member-skill-v1.8.1",
    "ai-sop-member-skill-v1.8.0",
}
BOOTSTRAP_FORBIDDEN_PATHS = {
    "sop",
    "dashboard",
    "projectcode",
    ".github/skill-cleanup/history",
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


def validate_runtime_lock(system: dict[str, Any]) -> None:
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
    for package in REQUIRED_PACKAGES:
        if not (ROOT / package).is_dir():
            raise ValidationError(f"required package is missing: {package}")
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
    return system


def main() -> int:
    try:
        system = validate_lifecycle()
        validate_runtime_lock(system)
        validate_secret_hygiene()
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"SOP system validation passed (lifecycle={system['lifecycle']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

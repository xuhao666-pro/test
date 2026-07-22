#!/usr/bin/env python3
"""Deterministic project-state helper for ai-sop-coordinator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


PROTOCOL_VERSION = "1.0"
PROJECT_SCHEMA_VERSION = "1.5"
SKILL_VERSION = "1.8.4"
BUILD_ID = "coordinator-cli-1.8.4-human-gate-review-v1"
MEMBER_MINIMUM_VERSION = "1.8.1"
MEMBER_BUILD_ID = "member-cli-1.8.1-assignment-acceptance-v1"
COLLABORATION_MODELS = {"role-based", "collective-participation"}
GATE_CONFIRMATION_POLICIES = {"accountable-members", "all-participants"}
RISK_LEVELS = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
STAGES = {
    "01-requirement-contract": {
        "gate": "G1",
        "next": "02-solution-validation",
        "kinds": {"requirement-analysis", "shared-review"},
        "default_baseline": "none",
    },
    "02-solution-validation": {
        "gate": "G2",
        "next": "03-development-entry",
        "kinds": {
            "function-design",
            "system-inventory",
            "prototype-validation",
            "shared-review",
        },
        "default_baseline": "G1",
    },
    "03-development-entry": {
        "gate": "G3",
        "next": None,
        "kinds": {"technical-design", "test-task-packaging", "generic", "shared-review"},
        "default_baseline": "G2",
    },
}
REQUIRED_GATE_ARTIFACT_TYPES = {
    "01-requirement-contract": {
        "multi-view-review",
        "consensus-user-stories",
        "requirement-contract",
        "demand-pool",
        "atomic-requirements",
        "business-acceptance",
    },
    "02-solution-validation": {
        "solution-review",
        "consensus-function-design",
        "system-inventory",
        "validation-report",
        "production-gaps",
    },
    "03-development-entry": {
        "final-product-technical-plan",
        "test-matrix",
        "development-task-packages",
        "risk-and-rollback",
    },
}
TRACEABILITY_FIELDS = (
    "p0_source_coverage",
    "p0_user_story_coverage",
    "p0_user_story_source_coverage",
    "p0_user_story_requirement_coverage",
    "p0_acceptance_coverage",
    "p0_design_coverage",
    "p0_task_coverage",
    "p0_test_coverage",
)
GATE_REVIEW_FILE = "gate-review-pack.md"
GATE_REVIEW_METADATA_PREFIX = "<!-- gate-review-metadata:"
GATE_REVIEW_COMPARISON_STATUSES = {"none", "published", "reviewed", "baseline"}
GATE_REVIEW_COMMON_HEADINGS = (
    "本次要决定什么",
    "评审身份",
    "一页结论",
    "成员观点",
    "一致意见与未决分歧",
    "采纳、暂缓与拒绝",
    "风险、缺口与 Gate 条件",
    "对比版本变化",
    "全员评审检查表",
    "建议 Gate 结论",
    "原始材料附录",
)
GATE_REVIEW_STAGE_HEADINGS = {
    "01-requirement-contract": ("G1 需求合同核心内容",),
    "02-solution-validation": ("G2 方案与验证核心内容",),
    "03-development-entry": ("G3 开发准备核心内容",),
}
GATE_REVIEW_STAGE_SUBHEADINGS = {
    "01-requirement-contract": (
        "用户、场景与用户痛点",
        "用户故事与需求来源",
        "原子需求与业务验收",
    ),
    "02-solution-validation": (
        "候选方案与比较",
        "验证结果与生产缺口",
        "功能设计与系统边界",
    ),
    "03-development-entry": (
        "技术设计与开发任务",
        "测试策略与质量门槛",
        "风险、回滚与开发许可",
    ),
}
GATE_REQUIRED_CAPACITIES = {
    "G1": {"business-decision", "product-decision"},
    "G2": {"business-decision", "product-decision", "technical-decision"},
    "G3": {
        "project-decision",
        "product-decision",
        "technical-decision",
        "test-decision",
    },
}
ROLE_TO_CAPACITY = {
    "business-owner": "business-decision",
    "product-owner": "product-decision",
    "technical-owner": "technical-decision",
    "project-owner": "project-decision",
    "test-owner": "test-decision",
}
PARTICIPATION_MODES = {"role-assigned", "collective-round", "individual-exception"}
TASK_PRIORITIES = {"P0", "P1", "P2", "P3"}
AI_DIALOGUE_MODES = {"required", "optional"}
REQUIRED_SUBMISSION_FILES = (
    "submission-manifest.yaml",
    "main-output.md",
    "content-block-index.yaml",
    "source-ledger.yaml",
    "assumptions-and-gaps.yaml",
    "risks-and-new-requirements.yaml",
)
ADAPTIVE_GRILL_OUTPUTS = (
    "human-collaboration-log.yaml",
    "grill-summary.yaml",
)


def resolve_ai_dialogue_policy(project: dict[str, Any]) -> dict[str, str]:
    value = project.get("ai_dialogue_collaboration")
    if value is None:
        return {"mode": "required", "source": "project-policy"}
    if not isinstance(value, dict) or value.get("mode") not in AI_DIALOGUE_MODES:
        raise SopError("Project ai_dialogue_collaboration.mode must be required or optional")
    return {"mode": str(value["mode"]), "source": "project-policy"}


def confirmed_member_release(project: dict[str, Any]) -> dict[str, str]:
    control = project.get("skill_release_control")
    if control is None:
        # Projects created before release control existed implicitly used Member 1.8.0.
        # Keep that historical binding stable instead of changing it when this
        # coordinator package advances its default for newly initialized projects.
        return {
            "name": "ai-sop-member",
            "version": "1.8.0",
            "build_id": "member-cli-1.8.0-ai-dialogue-exact-release-v1",
            "package_path": "ai-sop-member-skill-v1.8.0",
            "release_commit": "legacy-project-v1.8-default",
            "protocol_version": PROTOCOL_VERSION,
        }
    if not isinstance(control, dict) or control.get("status") != "confirmed":
        raise SopError(
            "Member Skill release is awaiting coordinator confirmation after Gate; "
            "confirm a stable repository release before dispatch"
        )
    release = control.get("confirmed_member_skill")
    required = ("name", "version", "build_id", "package_path", "release_commit")
    if not isinstance(release, dict) or any(not str(release.get(key, "")).strip() for key in required):
        raise SopError("Confirmed Member Skill release record is incomplete")
    return {key: str(value) for key, value in release.items()}


def skill_release_confirmation_token(release: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(release, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def discover_latest_stable_member_release(repository_root: Path) -> dict[str, str]:
    releases: list[dict[str, str]] = []
    for package in repository_root.glob("ai-sop-member-skill-v*"):
        manifest_path = package / "package-manifest.json"
        protocol_path = package / "ai-sop-member" / "assets" / "protocol-version.yaml"
        cli_path = package / "ai-sop-member" / "scripts" / "member_cli.py"
        if not (manifest_path.is_file() and protocol_path.is_file() and cli_path.is_file()):
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            protocol = load_data(protocol_path)
        except (OSError, ValueError, SopError):
            continue
        if manifest.get("release_status") != "stable":
            continue
        version = str(manifest.get("package_version", "")).strip()
        build_id = str(manifest.get("build_id", "")).strip()
        cli_text = cli_path.read_text(encoding="utf-8")
        cli_version = re.search(r'^SKILL_VERSION\s*=\s*"([^"]+)"', cli_text, re.MULTILINE)
        cli_build = re.search(r'^BUILD_ID\s*=\s*"([^"]+)"', cli_text, re.MULTILINE)
        if (
            not version
            or not build_id
            or str(protocol.get("skill_version")) != version
            or not cli_version
            or cli_version.group(1) != version
            or not cli_build
            or cli_build.group(1) != build_id
        ):
            continue
        releases.append(
            {
                "name": "ai-sop-member",
                "version": version,
                "build_id": build_id,
                "package_path": package.name,
                "protocol_version": str(protocol.get("protocol_version", "")),
            }
        )
    if not releases:
        raise SopError("No consistent stable ai-sop-member release was found")
    return max(releases, key=lambda item: version_tuple(item["version"]))
SUBMISSION_CONFIRMATION_OUTPUT = "human-submission-confirmation.yaml"
SUBMISSION_CONFIRMATION_POSITIONS = (
    "confirm",
    "oppose",
    "question",
    "reserve",
)
ADAPTIVE_GRILL_TOPICS = (
    "target-users",
    "scenarios",
    "problems",
    "business-value",
    "evidence",
    "counterexamples",
    "scope",
    "priority",
    "risks",
)
ADAPTIVE_GRILL_CONFIRMATIONS = (
    "problem-definition",
    "p0-scope",
    "unresolved-disagreements",
)
PROVENANCE_ID_PATTERN = re.compile(r"^P-\d{3,}$")
SOURCE_BLOCK_ID_PATTERN = re.compile(r"^SB-[a-f0-9]{16}(?:-\d+)?$")
PROVENANCE_MARKER_PATTERN = re.compile(r"\[(P-\d{3,})\]")
DERIVATION_TYPES = {
    "verbatim",
    "paraphrased",
    "synthesis",
    "derived",
    "human-decision",
    "coordinator-added",
    "conflict-retained",
    "legacy-unattributed",
}
ALLOWED_TRANSITIONS = {
    "preparing": {"collecting", "terminated"},
    "collecting": {"submission-closed", "returned-to-collection", "terminated"},
    "returned-to-collection": {"collecting", "terminated"},
    "submission-closed": {"aggregating", "returned-to-collection", "terminated"},
    "aggregating": {"team-review", "returned-to-collection", "terminated"},
    "team-review": {"gate-pending", "returned-to-collection", "terminated"},
    "gate-pending": {"merge-pending", "returned-to-collection", "terminated"},
    "merge-pending": {"baselined", "returned-to-collection", "terminated"},
    "baselined": {"next-stage"},
    "next-stage": set(),
    "terminated": set(),
}


class SopError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def project_lock(project_root: str | Path, timeout_seconds: float = 15.0):
    root = Path(project_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".ai-sop-coordinator.lock"
    deadline = time.monotonic() + timeout_seconds
    descriptor = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SopError(f"Timed out waiting for coordinator lock: {lock_path}")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()} created_at={now_iso()}\n".encode("utf-8"))
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def load_data(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SopError(f"File not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        if not yaml:
            raise SopError(
                f"Cannot parse non-JSON YAML in {path}; use JSON-compatible YAML or install PyYAML"
            )
        try:
            data = yaml.safe_load(text)
        except Exception as exc:
            raise SopError(f"Cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SopError(f"Expected a mapping in {path}")
    return data


def dump_data(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # JSON is valid YAML 1.2 and keeps every member machine dependency-free.
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def normalize_content(value: str) -> str:
    lines = []
    for raw in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"[ \t]+", " ", raw.strip())
        if line:
            lines.append(line)
    return "\n".join(lines)


def content_hash(value: str) -> str:
    normalized = normalize_content(value)
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def version_tuple(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", str(value))
    return tuple(int(part) for part in parts) if parts else (0,)


def requires_assignment_acceptance(assignment: dict[str, Any]) -> bool:
    return version_tuple(str(assignment.get("minimum_skill_version", "1.0.0"))) >= (
        1,
        8,
        1,
    )


def assignment_acceptance_policy(assignment: dict[str, Any]) -> dict[str, Any] | None:
    if not requires_assignment_acceptance(assignment):
        return None
    expected = {
        "mode": "explicit-member-receipt",
        "required": True,
        "receipt_schema_version": "1.0",
        "gate_effect": "none",
    }
    if assignment.get("acceptance_policy") != expected:
        raise SopError("V1.8.1 assignment acceptance_policy is invalid")
    return expected


def requires_submission_confirmation(assignment: dict[str, Any]) -> bool:
    return version_tuple(str(assignment.get("minimum_skill_version", "1.0.0"))) >= (
        1,
        7,
        5,
    )


def validate_submission_confirmation_policy(
    assignment: dict[str, Any],
) -> dict[str, Any] | None:
    if not requires_submission_confirmation(assignment):
        return None
    policy = assignment.get("submission_confirmation")
    if not isinstance(policy, dict):
        raise SopError("Assignment submission_confirmation must be a mapping")
    if policy.get("required") is not True:
        raise SopError("Assignment submission_confirmation.required must be true")
    if str(policy.get("human_owner", "")) != str(assignment.get("human_owner", "")):
        raise SopError("submission_confirmation human_owner must match the assignment")
    if policy.get("source_file") != "main-output.md":
        raise SopError("submission_confirmation source_file must be main-output.md")
    if policy.get("hash_algorithm") != "sha256-normalized-v1":
        raise SopError(
            "submission_confirmation hash_algorithm must be sha256-normalized-v1"
        )
    required_subjects = policy.get("required_subjects")
    if not isinstance(required_subjects, list) or sorted(
        set(str(item) for item in required_subjects)
    ) != ["main-output-hash", "personal-stance"]:
        raise SopError(
            "submission_confirmation must require body hash and personal stance"
        )
    allowed_positions = policy.get("allowed_positions")
    if not isinstance(allowed_positions, list) or sorted(
        set(str(item) for item in allowed_positions)
    ) != sorted(SUBMISSION_CONFIRMATION_POSITIONS):
        raise SopError("submission_confirmation allowed_positions are invalid")
    if policy.get("stale_policy") != "block":
        raise SopError("submission_confirmation stale_policy must be block")
    if policy.get("gate_effect") != "none":
        raise SopError("submission_confirmation gate_effect must be none")
    return policy


def submission_confirmation_token(
    assignment: dict[str, Any],
    submission_id: str,
    document_hash: str,
    position: str,
    position_statement: str,
) -> str:
    payload = {
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "submission_id": submission_id,
        "member_id": str(assignment["member_id"]),
        "human_owner": str(assignment["human_owner"]),
        "source_file": "main-output.md",
        "document_hash": document_hash,
        "position": position,
        "position_statement": position_statement,
        "authority_scope": "member-contribution-submission-only",
        "gate_effect": "none",
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def confirmation_manifest_summary(record: dict[str, Any]) -> dict[str, Any]:
    stance = record.get("personal_stance")
    stance = stance if isinstance(stance, dict) else {}
    return {
        "file": SUBMISSION_CONFIRMATION_OUTPUT,
        "status": record.get("status"),
        "document_hash": record.get("document_hash"),
        "position": stance.get("code"),
        "confirmed_by": record.get("confirmed_by"),
        "confirmed_at": record.get("confirmed_at"),
        "record_hash": content_hash(
            json.dumps(record, ensure_ascii=False, sort_keys=True)
        ),
    }


def submission_confirmation_projection(
    assignment: dict[str, Any], manifest: dict[str, Any] | None
) -> dict[str, Any]:
    if not requires_submission_confirmation(assignment):
        return {
            "required": False,
            "status": "legacy-not-required",
            "human_owner": assignment.get("human_owner"),
            "personal_stance": None,
            "requires_review": False,
            "confirmed_at": None,
            "document_hash": None,
            "record_hash": None,
        }
    summary = manifest.get("human_submission_confirmation") if manifest else None
    summary = summary if isinstance(summary, dict) else {}
    position = summary.get("position")
    return {
        "required": True,
        "status": summary.get("status", "missing"),
        "human_owner": assignment.get("human_owner"),
        "personal_stance": position,
        "requires_review": position in {"oppose", "question", "reserve"},
        "confirmed_at": summary.get("confirmed_at"),
        "document_hash": summary.get("document_hash"),
        "record_hash": summary.get("record_hash"),
    }


def validate_local_submission_confirmation(
    submission: Path,
    assignment: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if not requires_submission_confirmation(assignment):
        return submission_confirmation_projection(assignment, manifest)
    validate_submission_confirmation_policy(assignment)
    main_text = (submission / "main-output.md").read_text(encoding="utf-8")
    content_index = load_data(submission / "content-block-index.yaml")
    validate_member_content_index(main_text, assignment, manifest, content_index)
    document_hash = str(content_index.get("document_hash", ""))
    if manifest.get("content_document_hash") != document_hash:
        raise SopError("Submission manifest content_document_hash is stale")
    if manifest.get("content_block_count") != content_index.get("block_count"):
        raise SopError("Submission manifest content_block_count is stale")

    record = load_data(submission / SUBMISSION_CONFIRMATION_OUTPUT)
    collaboration = assignment.get("human_collaboration")
    collaboration_mode = (
        str(collaboration.get("mode", "none"))
        if isinstance(collaboration, dict)
        else "none"
    )
    expected_identity = {
        "schema_version": "1.0",
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "submission_id": str(manifest.get("submission_id", submission.name)),
        "member_id": str(assignment["member_id"]),
        "human_owner": str(assignment["human_owner"]),
        "source_file": "main-output.md",
        "hash_algorithm": "sha256-normalized-v1",
        "human_collaboration_mode": collaboration_mode,
        "authority_scope": "member-contribution-submission-only",
        "gate_effect": "none",
    }
    mismatches = [
        field
        for field, expected in expected_identity.items()
        if str(record.get(field)) != str(expected)
    ]
    if mismatches:
        raise SopError(
            "Human submission confirmation identity mismatch: "
            + ", ".join(mismatches)
        )
    if manifest.get("human_submission_confirmation") != confirmation_manifest_summary(
        record
    ):
        raise SopError("Manifest human_submission_confirmation summary is stale")
    if record.get("status") != "confirmed":
        raise SopError("Human owner has not confirmed the current body hash and stance")
    if str(record.get("document_hash", "")) != document_hash:
        raise SopError("Human owner confirmation is stale because main-output.md changed")
    stance = record.get("personal_stance")
    if not isinstance(stance, dict):
        raise SopError("Human owner confirmation personal_stance must be a mapping")
    position = str(stance.get("code", ""))
    statement = str(stance.get("statement", "")).strip()
    if position not in SUBMISSION_CONFIRMATION_POSITIONS:
        raise SopError(f"Invalid human owner personal stance: {position}")
    if not statement:
        raise SopError("Human owner personal stance statement cannot be blank")
    token = submission_confirmation_token(
        assignment,
        str(manifest.get("submission_id", submission.name)),
        document_hash,
        position,
        statement,
    )
    if str(record.get("confirmation_token", "")) != token:
        raise SopError("Human owner confirmation token does not match the current preview")
    subjects = record.get("confirmed_subjects")
    if not isinstance(subjects, dict) or any(
        subjects.get(field) is not True
        for field in ("exact_document_hash", "personal_stance")
    ):
        raise SopError("Human owner confirmation subjects are incomplete")
    if str(record.get("confirmed_by", "")) != str(assignment["human_owner"]):
        raise SopError("Human owner confirmation was not made by the registered owner")
    if not str(record.get("prepared_at", "")).strip():
        raise SopError("Human owner confirmation prepared_at cannot be blank")
    if not str(record.get("confirmed_at", "")).strip():
        raise SopError("Human owner confirmation confirmed_at cannot be blank")
    if record.get("confirmation_method") != "explicit-human-owner":
        raise SopError(
            "Human owner confirmation method must be explicit-human-owner"
        )
    return submission_confirmation_projection(assignment, manifest)


def markdown_content_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    headings: list[str] = []
    buffer: list[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal buffer
        normalized = normalize_content("\n".join(buffer))
        buffer = []
        if normalized:
            blocks.append({"content": normalized, "heading_path": list(headings)})

    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = raw.strip()
        if stripped.startswith("```"):
            buffer.append(raw)
            in_fence = not in_fence
            if not in_fence:
                flush()
            continue
        if in_fence:
            buffer.append(raw)
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            headings[:] = headings[: level - 1]
            headings.append(heading.group(2))
            continue
        if not stripped:
            flush()
        else:
            buffer.append(raw)
    flush()
    return blocks


def build_member_content_index(
    text: str, assignment: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    occurrences: dict[str, int] = {}
    for ordinal, raw in enumerate(markdown_content_blocks(text), start=1):
        normalized = str(raw["content"])
        identity = (
            f"{assignment['member_id']}|{assignment['assignment_id']}|{normalized}"
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        base_id = f"SB-{digest[:16]}"
        occurrences[base_id] = occurrences.get(base_id, 0) + 1
        block_id = (
            base_id
            if occurrences[base_id] == 1
            else f"{base_id}-{occurrences[base_id]}"
        )
        blocks.append(
            {
                "source_block_id": block_id,
                "ordinal": ordinal,
                "heading_path": raw["heading_path"],
                "content_hash": content_hash(normalized),
                "text_excerpt": normalized.replace("\n", " ")[:200],
                "evidence_refs": sorted(
                    set(re.findall(r"\bSRC-\d{3,}\b", normalized))
                ),
            }
        )
    return {
        "schema_version": "1.0",
        "submission_id": manifest.get("submission_id"),
        "assignment_id": assignment["assignment_id"],
        "member_id": assignment["member_id"],
        "source_file": "main-output.md",
        "document_hash": content_hash(text),
        "block_count": len(blocks),
        "indexed_at": now_iso(),
        "blocks": blocks,
    }


def validate_member_content_index(
    text: str,
    assignment: dict[str, Any],
    manifest: dict[str, Any],
    actual: dict[str, Any],
) -> None:
    expected = build_member_content_index(text, assignment, manifest)
    for field in (
        "schema_version",
        "submission_id",
        "assignment_id",
        "member_id",
        "source_file",
        "document_hash",
        "block_count",
        "blocks",
    ):
        if actual.get(field) != expected.get(field):
            raise SopError(
                f"Member content-block-index is stale or invalid: {field}"
            )
    for item in actual.get("blocks", []):
        block_id = str(item.get("source_block_id", ""))
        if not SOURCE_BLOCK_ID_PATTERN.fullmatch(block_id):
            raise SopError(f"Invalid member source_block_id: {block_id}")


def sop_root(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / "sop"


def stage_root(project_root: str | Path, stage: str) -> Path:
    if stage not in STAGES:
        raise SopError(f"Unknown stage: {stage}")
    return sop_root(project_root) / "stages" / stage


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    if not cleaned:
        raise SopError(f"Invalid identifier: {value!r}")
    return cleaned


def find_git_root(path: Path) -> Path | None:
    current = path.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def run_git(git_root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=git_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SopError("Git executable was not found") from exc
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SopError(f"git {' '.join(arguments)} failed: {detail}")
    return result


def configured_main_branch(project: dict[str, Any]) -> str:
    integration = project.get("git_integration", {})
    branch = str(integration.get("main_branch", "main")).strip()
    if not branch or branch.startswith("-"):
        raise SopError("project git_integration.main_branch is invalid")
    return branch


def default_member_branch(member_id: str) -> str:
    return f"sop/member/{safe_id(member_id)}"


def non_lock_worktree_changes(git_root: Path) -> list[str]:
    output = run_git(git_root, "status", "--porcelain", "--untracked-files=all").stdout
    changes = []
    for line in output.splitlines():
        path_text = line[3:].replace("\\", "/") if len(line) > 3 else line
        if path_text == ".ai-sop-coordinator.lock" or path_text.endswith(
            "/.ai-sop-coordinator.lock"
        ):
            continue
        changes.append(line)
    return changes


def require_main_git_worktree(project_root: str | Path, project: dict[str, Any]) -> Path:
    git_root = find_git_root(Path(project_root))
    if git_root is None:
        raise SopError("A shared Git repository is required for Gate branch integration")
    main_branch = configured_main_branch(project)
    current_branch = run_git(git_root, "branch", "--show-current").stdout.strip()
    if current_branch != main_branch:
        raise SopError(
            f"Run the Gate integration command on {main_branch}, not {current_branch or 'detached HEAD'}"
        )
    changes = non_lock_worktree_changes(git_root)
    if changes:
        raise SopError(
            "Git worktree must be clean before Gate approval or integration: "
            + "; ".join(changes[:8])
        )
    return git_root


def resolve_git_head(git_root: Path, branch: str) -> str:
    if not branch or branch.startswith("-"):
        raise SopError(f"Invalid member Git branch: {branch!r}")
    result = run_git(git_root, "rev-parse", "--verify", f"{branch}^{{commit}}")
    return result.stdout.strip()


def build_gate_merge_plan(
    project_root: str | Path,
    root: Path,
    project: dict[str, Any],
    remote: str = "origin",
) -> dict[str, Any]:
    git_root = find_git_root(Path(project_root))
    if git_root is None:
        raise SopError("Cannot prepare a Gate without the shared Git repository")
    main_branch = configured_main_branch(project)
    resolve_git_head(git_root, main_branch)
    branches: list[dict[str, str]] = []
    seen: set[str] = set()
    for member_id in active_member_ids(root, project):
        role = load_data(root / "roles" / f"{member_id}.yaml")
        branch = str(role.get("git_branch", default_member_branch(member_id))).strip()
        if branch == main_branch:
            raise SopError(f"Member {member_id} branch cannot be the main branch")
        if branch in seen:
            raise SopError(f"Member Git branch is assigned more than once: {branch}")
        seen.add(branch)
        observed_ref = f"{remote}/{branch}"
        branches.append(
            {
                "member_id": member_id,
                "branch": branch,
                "observed_ref": observed_ref,
                "expected_head": resolve_git_head(git_root, observed_ref),
            }
        )
    if not branches:
        raise SopError("Gate branch integration requires at least one active member branch")
    return {
        "required": True,
        "policy": "all-active-member-branches",
        "target_branch": main_branch,
        "member_branches": branches,
        "human_review_covers_branch_heads": False,
        "status": "pending-human-approval",
        "prepared_at": now_iso(),
    }


def validate_gate_merge_plan(
    project_root: str | Path,
    root: Path,
    project: dict[str, Any],
    decision: dict[str, Any],
    require_human_coverage: bool,
    remote: str = "origin",
) -> tuple[Path, dict[str, Any]]:
    git_root = find_git_root(Path(project_root))
    if git_root is None:
        raise SopError("A shared Git repository is required for Gate branch integration")
    plan = decision.get("merge_plan")
    if not isinstance(plan, dict) or plan.get("required") is not True:
        raise SopError("Gate decision requires a merge_plan")
    if plan.get("policy") != "all-active-member-branches":
        raise SopError("Gate merge_plan policy must be all-active-member-branches")
    if plan.get("target_branch") != configured_main_branch(project):
        raise SopError("Gate merge_plan target_branch must match project main branch")
    if require_human_coverage and plan.get("human_review_covers_branch_heads") is not True:
        raise SopError("Human approval must explicitly cover every recorded member branch head")
    entries = plan.get("member_branches")
    if not isinstance(entries, list):
        raise SopError("Gate merge_plan.member_branches must be a list")
    expected_members = set(active_member_ids(root, project))
    actual_members: set[str] = set()
    actual_branches: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SopError("Gate merge_plan contains an invalid member branch entry")
        member_id = safe_id(str(entry.get("member_id", "")))
        branch = str(entry.get("branch", "")).strip()
        observed_ref = str(entry.get("observed_ref", f"{remote}/{branch}")).strip()
        expected_head = str(entry.get("expected_head", "")).strip()
        role = load_data(root / "roles" / f"{member_id}.yaml")
        registered_branch = str(
            role.get("git_branch", default_member_branch(member_id))
        ).strip()
        if branch != registered_branch:
            raise SopError(f"Gate merge branch does not match member card: {member_id}")
        if observed_ref != f"{remote}/{registered_branch}":
            raise SopError(f"Gate observed ref does not match member card: {member_id}")
        if member_id in actual_members or branch in actual_branches:
            raise SopError("Gate merge_plan contains duplicate members or branches")
        actual_members.add(member_id)
        actual_branches.add(branch)
        current_head = resolve_git_head(git_root, observed_ref)
        if current_head != expected_head:
            raise SopError(
                f"Member branch changed after Gate preparation: {member_id} "
                f"expected {expected_head}, found {current_head}"
            )
    if actual_members != expected_members:
        missing = sorted(expected_members - actual_members)
        extra = sorted(actual_members - expected_members)
        raise SopError(f"Gate merge_plan member mismatch; missing={missing}, extra={extra}")
    return git_root, plan


def git_relative_path(git_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError as exc:
        raise SopError(f"SOP artifact is outside the Git repository: {path}") from exc


def require_git_identity(git_root: Path) -> None:
    for key in ("user.name", "user.email"):
        if not run_git(git_root, "config", "--get", key, check=False).stdout.strip():
            raise SopError(f"Git {key} must be configured before mandatory Gate integration")


def commit_sop_paths(git_root: Path, paths: list[Path], message: str) -> str:
    relative_paths = [git_relative_path(git_root, path) for path in paths]
    run_git(git_root, "add", "--", *relative_paths)
    staged = run_git(git_root, "diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        raise SopError("No Gate state changes were available to commit")
    result = run_git(git_root, "commit", "-m", message, "--", *relative_paths, check=False)
    if result.returncode != 0:
        for relative_path in relative_paths:
            run_git(
                git_root,
                "restore",
                "--staged",
                "--worktree",
                "--",
                relative_path,
                check=False,
            )
        detail = (result.stderr or result.stdout).strip()
        raise SopError(f"Could not commit mandatory Gate state: {detail}")
    return run_git(git_root, "rev-parse", "HEAD").stdout.strip()


def parse_member(value: str, collaboration_model: str) -> tuple[str, str, str]:
    parts = value.split(":")
    if collaboration_model == "role-based":
        if len(parts) != 3 or not all(parts):
            raise SopError("role-based --member must use member-id:human-owner:role")
    elif collaboration_model == "collective-participation":
        if len(parts) not in {2, 3} or not all(parts):
            raise SopError(
                "collective-participation --member must use member-id:human-owner "
                "or member-id:human-owner:role"
            )
        if len(parts) == 2:
            parts.append("general-contributor")
    else:
        raise SopError(f"Unknown collaboration model: {collaboration_model}")
    return safe_id(parts[0]), parts[1], safe_id(parts[2])


def add_member(
    root: Path,
    member_id: str,
    human_owner: str,
    role: str,
    collaboration_model: str,
    git_branch: str | None = None,
) -> Path:
    role_path = root / "roles" / f"{member_id}.yaml"
    if role_path.exists():
        raise SopError(f"Member already exists: {member_id}")
    participation_type = (
        "general-contributor"
        if collaboration_model == "collective-participation"
        else "role-contributor"
    )
    dump_data(
        role_path,
        {
            "member_id": member_id,
            "member_type": "human-ai-unit",
            "human_owner": human_owner,
            "status": "active",
            "collaboration_model": collaboration_model,
            "participation_type": participation_type,
            "participation_scope": (
                "all-rounds"
                if collaboration_model == "collective-participation"
                else "assigned-rounds"
            ),
            "team_role": role,
            "git_branch": git_branch or default_member_branch(member_id),
            "primary_role": None if role == "general-contributor" else role,
            "additional_roles": [],
            "accountability_capacities": [],
            "ai_role": f"ai-{role}",
            "role_goal": f"Complete authorized SOP work from the {role} perspective",
            "professional_perspective": role,
            "responsible_stages": [],
            "responsibilities": [],
            "allowed_actions": ["analyze", "propose", "question", "create-own-artifacts"],
            "required_artifacts": [],
            "prohibited_actions": [
                "approve-human-gate",
                "impersonate-user-or-member",
                "expand-approved-scope",
                "modify-production-without-authorization",
            ],
            "escalation_conditions": [
                "scope-or-baseline-conflict",
                "R2-or-R3-risk",
                "missing-authority-or-evidence",
            ],
            "allowed_data_tools": [],
            "continuous_context_path": f"sop/roles/{member_id}.yaml",
            "allowed_paths": [
                f"sop/stages/*/dispatch/*-{member_id}-*.yaml",
                f"sop/stages/*/submissions/{member_id}/",
            ],
            "forbidden_paths": [
                "sop/stages/*/submissions/other-members/",
                "sop/stages/*/aggregation/",
                "sop/stages/*/gate/",
                "sop/stages/*/baseline/",
            ],
            "created_at": now_iso(),
        },
    )
    return role_path


def empty_gate_accountability() -> dict[str, dict[str, list[str]]]:
    return {gate_id: {} for gate_id in GATE_REQUIRED_CAPACITIES}


def register_accountability(
    project: dict[str, Any], member_id: str, gate_id: str, capacity: str
) -> None:
    gate_map = project.setdefault("gate_accountability", empty_gate_accountability())
    capacity_map = gate_map.setdefault(gate_id, {})
    member_ids = set(capacity_map.get(capacity, []))
    member_ids.add(member_id)
    capacity_map[capacity] = sorted(member_ids)


def register_default_role_accountability(
    project: dict[str, Any], role_card: dict[str, Any]
) -> None:
    capacity = ROLE_TO_CAPACITY.get(str(role_card.get("team_role", "")))
    if not capacity:
        return
    member_id = str(role_card["member_id"])
    records = list(role_card.get("accountability_capacities", []))
    for gate_id, required in GATE_REQUIRED_CAPACITIES.items():
        if capacity in required:
            register_accountability(project, member_id, gate_id, capacity)
            record = {"gate_id": gate_id, "capacity": capacity}
            if record not in records:
                records.append(record)
    role_card["accountability_capacities"] = sorted(
        records, key=lambda item: (str(item.get("gate_id")), str(item.get("capacity")))
    )


def active_member_ids(root: Path, project: dict[str, Any]) -> list[str]:
    registered = project.get("registered_member_ids", [])
    if not isinstance(registered, list):
        raise SopError("project-state registered_member_ids must be a list")
    active: list[str] = []
    for raw_member_id in sorted(str(value) for value in registered):
        member_id = safe_id(raw_member_id)
        role = load_data(root / "roles" / f"{member_id}.yaml")
        if str(role.get("status", "active")) == "active":
            active.append(member_id)
    return active


def require_current_schema(project: dict[str, Any]) -> None:
    if str(project.get("project_schema_version")) != PROJECT_SCHEMA_VERSION:
        raise SopError(
            f"Project schema {project.get('project_schema_version')} must be migrated to "
            f"{PROJECT_SCHEMA_VERSION} with migrate-project"
        )


def cmd_init_project(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    git_root = find_git_root(Path(args.project_root))
    if root.exists() and any(root.iterdir()):
        raise SopError(f"SOP directory already exists and is not empty: {root}")
    collaboration_model = args.collaboration_model
    if collaboration_model not in COLLABORATION_MODELS:
        raise SopError(f"Unknown collaboration model: {collaboration_model}")
    gate_confirmation_policy = args.gate_confirmation_policy or (
        "all-participants"
        if collaboration_model == "collective-participation"
        else "accountable-members"
    )
    parsed_members = [
        parse_member(value, collaboration_model) for value in (args.member or [])
    ]
    member_ids = [member_id for member_id, _, _ in parsed_members]
    if len(member_ids) != len(set(member_ids)):
        raise SopError("--member contains duplicate member IDs")
    member_branches: dict[str, str] = {}
    for mapping in args.member_branch or []:
        if "=" not in mapping:
            raise SopError("--member-branch must use member-id=branch")
        raw_member_id, branch = mapping.split("=", 1)
        member_id = safe_id(raw_member_id)
        branch = branch.strip()
        if member_id not in member_ids:
            raise SopError(f"--member-branch references an unregistered member: {member_id}")
        if not branch or branch.startswith("-"):
            raise SopError(f"Invalid member Git branch: {branch!r}")
        if member_id in member_branches:
            raise SopError(f"Duplicate --member-branch mapping: {member_id}")
        member_branches[member_id] = branch
    resolved_branches = [
        member_branches.get(member_id, default_member_branch(member_id))
        for member_id in member_ids
    ]
    if len(resolved_branches) != len(set(resolved_branches)):
        raise SopError("Each member must have a distinct Git branch")
    if args.main_branch in resolved_branches:
        raise SopError("A member Git branch cannot be the main branch")
    risk_level = args.risk_level.upper()
    if risk_level not in RISK_LEVELS:
        raise SopError(f"Unknown risk level: {args.risk_level}")
    execution_mode = args.execution_mode
    ai_dialogue_mode = args.ai_dialogue_mode
    if ai_dialogue_mode not in AI_DIALOGUE_MODES:
        raise SopError("AI dialogue mode must be required or optional")
    if execution_mode == "lightweight" and RISK_LEVELS[risk_level] >= RISK_LEVELS["R2"]:
        execution_mode = "standard"
        print("WARNING: R2/R3 projects automatically use standard mode.", file=sys.stderr)
    for relative in ("protocol/schemas", "roles", "demand-pool", "decisions", "stages"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    dump_data(
        root / "protocol" / "protocol-version.yaml",
        {
            "protocol_version": PROTOCOL_VERSION,
            "project_schema_version": PROJECT_SCHEMA_VERSION,
            "coordinator_skill_version": SKILL_VERSION,
        },
    )
    dump_data(
        root / "project-state.yaml",
        {
            "project_id": safe_id(args.project_id),
            "project_name": args.project_name,
            "coordinator_id": safe_id(args.coordinator_id),
            "protocol_version": PROTOCOL_VERSION,
            "project_schema_version": PROJECT_SCHEMA_VERSION,
            "status": "pre-development",
            "execution_mode": execution_mode,
            "collaboration_model": collaboration_model,
            "ai_dialogue_collaboration": {
                "mode": ai_dialogue_mode,
                "source": "project-policy",
            },
            "skill_release_control": {
                "status": "confirmed",
                "confirmed_member_skill": {
                    "name": "ai-sop-member",
                    "version": MEMBER_MINIMUM_VERSION,
                    "build_id": MEMBER_BUILD_ID,
                    "package_path": f"ai-sop-member-skill-v{MEMBER_MINIMUM_VERSION}",
                    "release_commit": "bundled-project-initial-release",
                    "protocol_version": PROTOCOL_VERSION,
                },
                "confirmation_source": "project-initial-release",
                "requires_post_gate_confirmation": False,
            },
            "gate_confirmation_policy": gate_confirmation_policy,
            "gate_accountability": empty_gate_accountability(),
            "highest_risk_level": risk_level,
            "real_development_status": args.real_development_status,
            "next_fixed_gate": "G1",
            "blocking_items": [],
            "risk_owner_roles": sorted(set(args.risk_owner_role or [])),
            "coordination_store": {
                "type": "git",
                "git_detected": git_root is not None,
                "git_root": str(git_root) if git_root else None,
            },
            "git_integration": {
                "required": True,
                "main_branch": args.main_branch,
                "merge_policy": "all-active-member-branches-after-human-approval",
                "pending_gate": None,
                "last_completed": None,
            },
            "submission_tracking": {
                "schema_version": "1.0",
                "revision": 0,
                "last_refreshed_at": None,
                "last_refresh_source": "init-project",
                "stages": {},
                "totals": {},
            },
            "provenance_tracking": {
                "schema_version": "1.0",
                "mode": "enforced",
                "effective_from_project_schema": PROJECT_SCHEMA_VERSION,
                "migrated_from_schema": None,
                "legacy_content_policy": "disallow-legacy-unattributed",
            },
            "current_stage": "01-requirement-contract",
            "baselines": {"G1": None, "G2": None, "G3": None},
            "created_at": now_iso(),
            "updated_at": now_iso(),
        },
    )
    dump_data(
        root / "demand-pool" / "demand-pool.yaml",
        {
            "artifact_id": "A04",
            "version": "0.1",
            "requirements": [],
            "updated_at": now_iso(),
        },
    )
    dump_data(root / "decisions" / "decision-log.yaml", {"artifact_id": "A00", "decisions": []})
    for stage, config in STAGES.items():
        current = root / "stages" / stage
        for name in ("dispatch", "submissions", "aggregation", "gate", "baseline"):
            (current / name).mkdir(parents=True, exist_ok=True)
        (current / "aggregation" / "provenance").mkdir(parents=True, exist_ok=True)
        dump_data(
            current / "stage-state.yaml",
            {
                "stage_id": stage,
                "gate_id": config["gate"],
                "status": "preparing",
                "expected_assignments": [],
                "rounds": {},
                "missing_submissions": [],
                "invalid_submissions": [],
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        )
        dump_data(
            current / "aggregation" / "participation-matrix.yaml",
            {
                "artifact_type": "participation-matrix",
                "schema_version": "1.0",
                "stage_id": stage,
                "collaboration_model": collaboration_model,
                "rounds": {},
                "stage_summary": {},
                "gate_confirmation": {
                    "policy": gate_confirmation_policy,
                    "approved_member_ids": [],
                },
                "updated_at": now_iso(),
            },
        )
        dump_data(
            current / "aggregation" / "provenance" / "source-block-index.yaml",
            {
                "schema_version": "1.0",
                "stage_id": stage,
                "generated_at": None,
                "source_index_hash": None,
                "submission_count": 0,
                "block_count": 0,
                "submissions": [],
                "source_blocks": [],
            },
        )
        dump_data(
            current / "aggregation" / "provenance" / "provenance-ledger.yaml",
            {
                "schema_version": "1.0",
                "stage_id": stage,
                "source_index": "aggregation/provenance/source-block-index.yaml",
                "updated_at": None,
                "targets": [],
            },
        )
    for member_id, human_owner, role in parsed_members:
        add_member(
            root,
            member_id,
            human_owner,
            role,
            collaboration_model,
            member_branches.get(member_id),
        )
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    project["registered_member_ids"] = sorted(path.stem for path in (root / "roles").glob("*.yaml"))
    if collaboration_model == "role-based":
        for role_path in sorted((root / "roles").glob("*.yaml")):
            role_card = load_data(role_path)
            register_default_role_accountability(project, role_card)
            dump_data(role_path, role_card)
    project["updated_at"] = now_iso()
    dump_data(project_path, project)
    print(root)
    if git_root is None:
        print(
            "WARNING: No Git repository detected. Establish the shared Git repository before distributed collection.",
            file=sys.stderr,
        )


def cmd_add_member(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    require_current_schema(project)
    collaboration_model = str(project.get("collaboration_model", "role-based"))
    if not args.role and collaboration_model == "role-based":
        raise SopError("role-based add-member requires --role")
    role = safe_id(args.role or "general-contributor")
    role_path = add_member(
        root,
        safe_id(args.member_id),
        args.human_owner,
        role,
        collaboration_model,
        args.git_branch,
    )
    role_card = load_data(role_path)
    if collaboration_model == "role-based":
        register_default_role_accountability(project, role_card)
        dump_data(role_path, role_card)
    project["registered_member_ids"] = sorted(path.stem for path in (root / "roles").glob("*.yaml"))
    project["updated_at"] = now_iso()
    dump_data(project_path, project)
    print(root / "roles" / f"{safe_id(args.member_id)}.yaml")


def cmd_assign_accountability(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    require_current_schema(project)
    member_id = safe_id(args.member_id)
    role_path = root / "roles" / f"{member_id}.yaml"
    role_card = load_data(role_path)
    if str(role_card.get("status", "active")) != "active":
        raise SopError(f"Cannot assign accountability to inactive member: {member_id}")
    gate_id = args.gate.upper()
    capacities = sorted({safe_id(value) for value in args.capacity})
    records = list(role_card.get("accountability_capacities", []))
    for capacity in capacities:
        register_accountability(project, member_id, gate_id, capacity)
        record = {"gate_id": gate_id, "capacity": capacity}
        if record not in records:
            records.append(record)
    role_card["accountability_capacities"] = sorted(
        records, key=lambda item: (str(item.get("gate_id")), str(item.get("capacity")))
    )
    role_card["updated_at"] = now_iso()
    project["updated_at"] = now_iso()
    dump_data(role_path, role_card)
    dump_data(project_path, project)
    print(json.dumps({"member_id": member_id, "gate_id": gate_id, "capacities": capacities}))


def cmd_migrate_project(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    current = str(project.get("project_schema_version", "1.0"))
    if current == PROJECT_SCHEMA_VERSION:
        print(project_path)
        return
    if current not in {"1.0", "1.1", "1.2", "1.3", "1.4"}:
        raise SopError(f"Unsupported migration from project schema {current}")
    legacy = current in {"1.0", "1.1"}
    collaboration_model = (
        "role-based" if legacy else str(project.get("collaboration_model", "role-based"))
    )
    gate_confirmation_policy = (
        "accountable-members"
        if legacy
        else str(project.get("gate_confirmation_policy", "accountable-members"))
    )
    risk_level = str(args.risk_level or project.get("highest_risk_level", "R1")).upper()
    if risk_level not in RISK_LEVELS:
        raise SopError(f"Unknown risk level: {risk_level}")
    execution_mode = str(args.execution_mode or project.get("execution_mode", "standard"))
    if execution_mode == "lightweight" and RISK_LEVELS[risk_level] >= RISK_LEVELS["R2"]:
        execution_mode = "standard"
    current_stage = str(project.get("current_stage", "01-requirement-contract"))
    project.update(
        {
            "project_schema_version": PROJECT_SCHEMA_VERSION,
            "protocol_version": str(project.get("protocol_version", PROTOCOL_VERSION)),
            "execution_mode": execution_mode,
            "collaboration_model": collaboration_model,
            "gate_confirmation_policy": gate_confirmation_policy,
            "gate_accountability": (
                empty_gate_accountability()
                if legacy
                else project.get("gate_accountability", empty_gate_accountability())
            ),
            "highest_risk_level": risk_level,
            "real_development_status": project.get("real_development_status", "not-started"),
            "next_fixed_gate": STAGES.get(current_stage, STAGES["01-requirement-contract"])["gate"],
            "blocking_items": project.get("blocking_items", []),
            "risk_owner_roles": sorted(
                set(
                    args.risk_owner_role
                    if args.risk_owner_role is not None
                    else project.get("risk_owner_roles", [])
                )
            ),
            "registered_member_ids": sorted(path.stem for path in (root / "roles").glob("*.yaml")),
            "updated_at": now_iso(),
        }
    )
    project["git_integration"] = {
        "required": True,
        "main_branch": args.main_branch
        or project.get("git_integration", {}).get("main_branch", "main"),
        "merge_policy": "all-active-member-branches-after-human-approval",
        "pending_gate": project.get("git_integration", {}).get("pending_gate"),
        "last_completed": project.get("git_integration", {}).get("last_completed"),
    }
    project["submission_tracking"] = project.get(
        "submission_tracking",
        {
            "schema_version": "1.0",
            "revision": 0,
            "last_refreshed_at": None,
            "last_refresh_source": "migrate-project",
            "stages": {},
            "totals": {},
        },
    )
    project["provenance_tracking"] = {
        "schema_version": "1.0",
        "mode": "enforced",
        "effective_from_project_schema": PROJECT_SCHEMA_VERSION,
        "migrated_from_schema": current,
        "legacy_content_policy": "allow-reviewed-legacy-unattributed",
    }
    dump_data(project_path, project)
    protocol_path = root / "protocol" / "protocol-version.yaml"
    protocol = load_data(protocol_path) if protocol_path.exists() else {}
    protocol["protocol_version"] = str(project.get("protocol_version", PROTOCOL_VERSION))
    protocol["project_schema_version"] = PROJECT_SCHEMA_VERSION
    protocol["coordinator_skill_version"] = SKILL_VERSION
    dump_data(protocol_path, protocol)
    for stage in STAGES:
        state_path = root / "stages" / stage / "stage-state.yaml"
        state = load_data(state_path)
        rounds = state.setdefault("rounds", {})
        stage_path = root / "stages" / stage
        for assignment_path in sorted((stage_path / "dispatch").glob("*.yaml")):
            assignment = load_data(assignment_path)
            assignment_member_id = safe_id(str(assignment.get("member_id", "")))
            assignment_role_path = root / "roles" / f"{assignment_member_id}.yaml"
            assignment_role = load_data(assignment_role_path)
            assignment["project_schema_version"] = PROJECT_SCHEMA_VERSION
            assignment["collaboration_model"] = assignment.get(
                "collaboration_model", collaboration_model
            )
            assignment["participation_mode"] = assignment.get(
                "participation_mode", "role-assigned"
            )
            assignment.setdefault("review_of_round", None)
            assignment["git_branch"] = assignment_role.get(
                "git_branch", default_member_branch(assignment_member_id)
            )
            assignment["main_branch"] = configured_main_branch(project)
            # Historical assignments are immutable contracts. Do not make an old task
            # require the new intake fields merely because the project tooling was upgraded.
            assignment.setdefault("minimum_skill_version", "1.0.0")
            dump_data(assignment_path, assignment)
            round_id = str(assignment.get("round_id", "legacy-round"))
            round_record = rounds.setdefault(
                round_id,
                {
                    "status": "collecting",
                    "assignment_ids": [],
                    "kinds": [],
                    "reviewed_at": None,
                },
            )
            round_record["collaboration_model"] = round_record.get(
                "collaboration_model", collaboration_model
            )
            round_record["participation_mode"] = round_record.get(
                "participation_mode", "role-assigned"
            )
            round_record["assignment_ids"] = sorted(
                set(round_record.get("assignment_ids", []))
                | {str(assignment["assignment_id"])}
            )
            round_record["kinds"] = sorted(
                set(round_record.get("kinds", []))
                | {str(assignment.get("assignment_kind", "generic"))}
            )
            round_record["expected_member_ids"] = sorted(
                set(round_record.get("expected_member_ids", []))
                | {str(assignment["member_id"])}
            )
            round_record.setdefault("shared_review_required", False)
            round_record.setdefault("shared_review_member_ids", [])
            round_record.setdefault("missing_exceptions", [])
            submission = (
                stage_path
                / "submissions"
                / str(assignment["member_id"])
                / f"{assignment['assignment_id']}-v{assignment['assignment_version']}"
                / "submission-manifest.yaml"
            )
            if submission.exists():
                manifest = load_data(submission)
                manifest["project_schema_version"] = PROJECT_SCHEMA_VERSION
                manifest["collaboration_model"] = manifest.get(
                    "collaboration_model", collaboration_model
                )
                manifest["participation_mode"] = manifest.get(
                    "participation_mode", "role-assigned"
                )
                manifest.setdefault("review_of_round", None)
                manifest["git_branch"] = assignment["git_branch"]
                manifest["main_branch"] = assignment["main_branch"]
                submission_dir = submission.parent
                main_output = submission_dir / "main-output.md"
                if main_output.is_file():
                    content_index = build_member_content_index(
                        main_output.read_text(encoding="utf-8"), assignment, manifest
                    )
                    dump_data(
                        submission_dir / "content-block-index.yaml", content_index
                    )
                    manifest["content_index"] = "content-block-index.yaml"
                    manifest["content_document_hash"] = content_index["document_hash"]
                    manifest["content_block_count"] = content_index["block_count"]
                    outputs = list(manifest.get("outputs", []))
                    if "content-block-index.yaml" not in outputs:
                        outputs.append("content-block-index.yaml")
                    manifest["outputs"] = outputs
                dump_data(submission, manifest)
        dump_data(state_path, state)
        matrix_path = root / "stages" / stage / "aggregation" / "participation-matrix.yaml"
        if not matrix_path.exists():
            dump_data(
                matrix_path,
                {
                    "artifact_type": "participation-matrix",
                    "schema_version": "1.0",
                    "stage_id": stage,
                    "collaboration_model": collaboration_model,
                    "rounds": {},
                    "stage_summary": {},
                    "gate_confirmation": {
                        "policy": gate_confirmation_policy,
                        "approved_member_ids": [],
                    },
                    "updated_at": now_iso(),
                },
            )
        provenance_root = root / "stages" / stage / "aggregation" / "provenance"
        provenance_root.mkdir(parents=True, exist_ok=True)
        source_index_path = provenance_root / "source-block-index.yaml"
        if not source_index_path.exists():
            dump_data(
                source_index_path,
                {
                    "schema_version": "1.0",
                    "stage_id": stage,
                    "generated_at": None,
                    "source_index_hash": None,
                    "submission_count": 0,
                    "block_count": 0,
                    "submissions": [],
                    "source_blocks": [],
                },
            )
        ledger_path = provenance_root / "provenance-ledger.yaml"
        if not ledger_path.exists():
            dump_data(
                ledger_path,
                {
                    "schema_version": "1.0",
                    "stage_id": stage,
                    "source_index": "aggregation/provenance/source-block-index.yaml",
                    "updated_at": None,
                    "targets": [],
                },
            )
    for role_path in (root / "roles").glob("*.yaml"):
        role = load_data(role_path)
        member_id = str(role.get("member_id", role_path.stem))
        team_role = str(role.get("team_role", "project-member"))
        role.setdefault("status", "active")
        role.setdefault("collaboration_model", collaboration_model)
        role.setdefault(
            "participation_type",
            "general-contributor"
            if collaboration_model == "collective-participation"
            else "role-contributor",
        )
        role.setdefault(
            "participation_scope",
            "all-rounds"
            if collaboration_model == "collective-participation"
            else "assigned-rounds",
        )
        role.setdefault(
            "primary_role", None if team_role == "general-contributor" else team_role
        )
        role.setdefault("git_branch", default_member_branch(member_id))
        role.setdefault("additional_roles", [])
        role.setdefault("accountability_capacities", [])
        role.setdefault("role_goal", f"从 {team_role} 视角完成获授权的 SOP 工作")
        role.setdefault("professional_perspective", team_role)
        role.setdefault("responsible_stages", [])
        role.setdefault("allowed_actions", ["analyze", "propose", "question", "create-own-artifacts"])
        role.setdefault("required_artifacts", [])
        role.setdefault(
            "prohibited_actions",
            ["approve-human-gate", "impersonate-user-or-member", "expand-approved-scope"],
        )
        role.setdefault(
            "escalation_conditions",
            ["scope-or-baseline-conflict", "R2-or-R3-risk", "missing-authority-or-evidence"],
        )
        role.setdefault("allowed_data_tools", [])
        role.setdefault("continuous_context_path", f"sop/roles/{member_id}.yaml")
        register_default_role_accountability(project, role)
        dump_data(role_path, role)
    dump_data(project_path, project)
    demand_pool_path = root / "demand-pool" / "demand-pool.yaml"
    if demand_pool_path.exists():
        demand_pool = load_data(demand_pool_path)
        demand_pool.setdefault("artifact_id", "A04")
        dump_data(demand_pool_path, demand_pool)
    decisions = root / "decisions" / "decision-log.yaml"
    if not decisions.exists():
        dump_data(decisions, {"artifact_id": "A00", "decisions": []})
    print(project_path)


def current_baseline(project: dict[str, Any], stage: str) -> str:
    gate = STAGES[stage]["default_baseline"]
    if gate == "none":
        return "none"
    value = project.get("baselines", {}).get(gate)
    if not value:
        raise SopError(f"Stage {stage} requires an approved {gate} baseline")
    return str(value)


def reviewed_solution_round(state: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for round_id, record in state.get("rounds", {}).items():
        kinds = set(record.get("kinds", []))
        if (
            {"function-design", "system-inventory"}.issubset(kinds)
            and record.get("status") == "reviewed"
        ):
            return str(round_id), record
    return None


def ensure_stage_two_assignment_order(
    state: dict[str, Any], kind: str, independence_mode: str
) -> tuple[str, dict[str, Any]] | None:
    if kind in {"function-design", "system-inventory"}:
        if independence_mode != "isolated-design":
            raise SopError(f"{kind} requires independence mode isolated-design")
        for record in state.get("rounds", {}).values():
            if "prototype-validation" in set(record.get("kinds", [])):
                raise SopError("Cannot add design/inventory assignments after validation has started")
        return None
    if kind == "prototype-validation":
        if independence_mode != "specialized-preparation":
            raise SopError("prototype-validation requires specialized-preparation")
        reviewed = reviewed_solution_round(state)
        if not reviewed:
            raise SopError(
                "prototype-validation requires a closed and reviewed round containing "
                "both function-design and system-inventory"
            )
        return reviewed
    return None


def assignment_context(
    args: argparse.Namespace,
) -> tuple[Path, dict[str, Any], Path, Path, dict[str, Any], str, dict[str, Any] | None]:
    root = sop_root(args.project_root)
    project = load_data(root / "project-state.yaml")
    require_current_schema(project)
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    if state.get("status") not in {"preparing", "collecting", "returned-to-collection"}:
        raise SopError(f"Cannot create assignments while stage is {state.get('status')}")
    if args.kind not in STAGES[args.stage]["kinds"]:
        raise SopError(f"Task kind {args.kind} is not allowed in {args.stage}")
    round_id = safe_id(args.round)
    reviewed_round = None
    if args.stage == "02-solution-validation":
        reviewed_round = ensure_stage_two_assignment_order(
            state, args.kind, args.independence_mode
        )
    review_of_round = getattr(args, "review_of_round", None)
    if args.kind == "shared-review":
        if args.independence_mode != "shared-review":
            raise SopError("shared-review requires independence mode shared-review")
        if not review_of_round:
            raise SopError("shared-review requires --review-of-round")
        target_round_id = safe_id(review_of_round)
        target = state.get("rounds", {}).get(target_round_id)
        if not isinstance(target, dict) or target.get("status") not in {"closed", "reviewed"}:
            raise SopError("The --review-of-round target must be closed before review dispatch")
        if "shared-review" in set(target.get("kinds", [])):
            raise SopError("A shared-review round cannot review another shared-review round")
    elif review_of_round:
        raise SopError("--review-of-round is only valid for shared-review assignments")
    return root, project, stage_path, state_path, state, round_id, reviewed_round


def prepare_round_record(
    state: dict[str, Any],
    round_id: str,
    collaboration_model: str,
    participation_mode: str,
    expected_members: list[str],
) -> dict[str, Any]:
    rounds = state.setdefault("rounds", {})
    record = rounds.get(round_id)
    if record is None:
        record = {
            "status": "collecting",
            "assignment_ids": [],
            "kinds": [],
            "reviewed_at": None,
            "collaboration_model": collaboration_model,
            "participation_mode": participation_mode,
            "expected_member_ids": sorted(expected_members),
            "shared_review_required": False,
            "shared_review_member_ids": [],
            "missing_exceptions": [],
        }
        rounds[round_id] = record
    if not isinstance(record, dict) or record.get("status") != "collecting":
        raise SopError(f"Round {round_id} is not collecting")
    existing_model = str(record.get("collaboration_model", collaboration_model))
    if existing_model != collaboration_model:
        raise SopError(f"Round {round_id} uses collaboration model {existing_model}")
    existing_members = sorted(str(value) for value in record.get("expected_member_ids", []))
    if (
        collaboration_model == "collective-participation"
        and existing_members
        and existing_members != sorted(expected_members)
    ):
        raise SopError(
            f"Active membership changed after round {round_id} started; "
            "start a new round or restore the membership snapshot"
        )
    record["collaboration_model"] = collaboration_model
    if record.get("participation_mode") == "collective-round":
        participation_mode = "collective-round"
    record["participation_mode"] = participation_mode
    record["expected_member_ids"] = sorted(expected_members)
    record.setdefault("shared_review_required", False)
    record.setdefault("shared_review_member_ids", [])
    record.setdefault("missing_exceptions", [])
    return record


def complete_markdown(path: Path) -> bool:
    if not path.is_file():
        return False
    content = path.read_text(encoding="utf-8")
    return bool(content.strip()) and "[[FILL]]" not in content


def published_round_refs(
    *,
    stage_path: Path,
    stage: str,
    round_id: str,
    require_summary: bool,
) -> list[str]:
    state = load_data(stage_path / "stage-state.yaml")
    record = state.get("rounds", {}).get(round_id)
    if not isinstance(record, dict):
        raise SopError(f"Reviewed round does not exist: {round_id}")
    if record.get("status") not in {"closed", "reviewed"}:
        raise SopError(f"Reviewed round {round_id} must be closed before dispatch")
    round_root = stage_path / "aggregation" / "rounds" / round_id
    index_path = round_root / "submission-index.yaml"
    if not index_path.is_file():
        raise SopError(
            "Shared-review dispatch requires a published submission index: "
            f"{index_path}"
        )
    index = load_data(index_path)
    if str(index.get("stage_id")) != stage or str(index.get("round_id")) != round_id:
        raise SopError(f"Published submission index does not match round {round_id}")
    base = f"sop/stages/{stage}/aggregation/rounds/{round_id}"
    refs = [f"{base}/submission-index.yaml"]
    summary_path = round_root / "summary.md"
    if complete_markdown(summary_path):
        refs.append(f"{base}/summary.md")
    elif require_summary:
        raise SopError(
            f"Round {round_id} summary.md must be complete before this assignment"
        )
    return refs


def build_assignment(
    *,
    root: Path,
    project: dict[str, Any],
    stage_path: Path,
    stage: str,
    round_id: str,
    member_id: str,
    kind: str,
    task_contract: dict[str, Any],
    independence_mode: str,
    deadline: str | None,
    participation_mode: str,
    reviewed_round: tuple[str, dict[str, Any]] | None,
    review_of_round: str | None = None,
    human_collaboration_mode: str = "none",
    human_collaboration_max_questions: int = 20,
) -> tuple[Path, dict[str, Any]]:
    if participation_mode not in PARTICIPATION_MODES:
        raise SopError(f"Unknown participation mode: {participation_mode}")
    member_id = safe_id(member_id)
    role_card = load_data(root / "roles" / f"{member_id}.yaml")
    if str(role_card.get("status", "active")) != "active":
        raise SopError(f"Cannot assign inactive member: {member_id}")
    assignment_id = safe_id(f"A-{stage.split('-', 1)[0]}-{round_id}-{member_id}-{kind}")
    path = stage_path / "dispatch" / f"{assignment_id}.yaml"
    if path.exists():
        raise SopError(f"Assignment already exists: {path}")
    baseline = current_baseline(project, stage)
    baseline_refs = ["sop/project-state.yaml", f"sop/roles/{member_id}.yaml"]
    if baseline != "none":
        previous_stage = (
            "01-requirement-contract" if stage.startswith("02-") else "02-solution-validation"
        )
        baseline_refs.append(f"sop/stages/{previous_stage}/baseline/{baseline}/")
    if reviewed_round:
        reviewed_round_id, _ = reviewed_round
        baseline_refs.extend(
            published_round_refs(
                stage_path=stage_path,
                stage=stage,
                round_id=reviewed_round_id,
                require_summary=True,
            )
        )
    if review_of_round:
        baseline_refs.extend(
            published_round_refs(
                stage_path=stage_path,
                stage=stage,
                round_id=safe_id(review_of_round),
                require_summary=False,
            )
        )
    collaboration_model = str(project.get("collaboration_model", "role-based"))
    allowed_actions = ["read-authorized-sources", "create-own-submission"]
    forbidden_actions = [
        "read-other-submissions",
        "modify-project-state",
        "modify-aggregation",
        "modify-gate",
        "modify-baseline",
    ]
    if kind == "shared-review":
        allowed_actions.append("read-published-round-materials")
        forbidden_actions.remove("read-other-submissions")
        forbidden_actions.append("read-unpublished-or-open-round-submissions")
    if human_collaboration_mode == "adaptive-grill":
        if kind != "requirement-analysis":
            raise SopError("adaptive-grill is only supported for requirement-analysis")
        if independence_mode != "isolated-discovery":
            raise SopError("adaptive-grill requires independence mode isolated-discovery")
        if not 3 <= human_collaboration_max_questions <= 100:
            raise SopError("adaptive-grill max questions must be between 3 and 100")
        human_collaboration = {
            "mode": "adaptive-grill",
            "required": True,
            "human_owner": role_card["human_owner"],
            "required_topics": list(ADAPTIVE_GRILL_TOPICS),
            "required_confirmations": list(ADAPTIVE_GRILL_CONFIRMATIONS),
            "unanswered_policy": "block",
            "max_questions": human_collaboration_max_questions,
            "allow_early_completion": True,
        }
    elif human_collaboration_mode == "none":
        human_collaboration = {"mode": "none", "required": False}
    else:
        raise SopError(f"Unsupported human collaboration mode: {human_collaboration_mode}")
    submission_confirmation = {
        "required": True,
        "human_owner": role_card["human_owner"],
        "source_file": "main-output.md",
        "hash_algorithm": "sha256-normalized-v1",
        "required_subjects": ["main-output-hash", "personal-stance"],
        "allowed_positions": list(SUBMISSION_CONFIRMATION_POSITIONS),
        "stale_policy": "block",
        "gate_effect": "none",
    }
    ai_dialogue_collaboration = resolve_ai_dialogue_policy(project)
    required_member_skill = confirmed_member_release(project)
    acceptance_policy = None
    if version_tuple(required_member_skill["version"]) >= (1, 8, 1):
        acceptance_policy = {
            "mode": "explicit-member-receipt",
            "required": True,
            "receipt_schema_version": "1.0",
            "gate_effect": "none",
        }
    member_task_contract = dict(task_contract)
    member_task_contract["human_collaboration"] = human_collaboration
    member_task_contract["submission_confirmation"] = submission_confirmation
    member_task_contract["ai_dialogue_collaboration"] = ai_dialogue_collaboration
    member_task_contract["required_member_skill"] = required_member_skill
    if acceptance_policy is not None:
        member_task_contract["acceptance_policy"] = acceptance_policy
    required_outputs = [*REQUIRED_SUBMISSION_FILES, SUBMISSION_CONFIRMATION_OUTPUT]
    quality_checks = [
        "identity-matches",
        "versions-match",
        "sources-labeled",
        "facts-separated-from-inference",
        "output-schema-valid",
        "human-owner-confirmed-current-main-output-hash",
        "human-owner-personal-stance-recorded",
        "stale-human-confirmation-blocked",
    ]
    if human_collaboration_mode == "adaptive-grill":
        required_outputs.extend(ADAPTIVE_GRILL_OUTPUTS)
        quality_checks.extend(
            [
                "adaptive-grill-consent-recorded",
                "adaptive-grill-topics-complete",
                "adaptive-grill-confirmations-complete",
            ]
        )
    assignment = {
        "assignment_id": assignment_id,
        "assignment_version": "1.0",
        "project_id": project["project_id"],
        "stage_id": stage,
        "round_id": round_id,
        "assignment_kind": kind,
        "member_id": role_card["member_id"],
        "human_owner": role_card["human_owner"],
        "role": role_card["team_role"],
        "git_branch": role_card.get(
            "git_branch", default_member_branch(str(role_card["member_id"]))
        ),
        "main_branch": configured_main_branch(project),
        "collaboration_model": collaboration_model,
        "participation_mode": participation_mode,
        "review_of_round": safe_id(review_of_round) if review_of_round else None,
        "task_source": task_contract["task_source"],
        "objective": task_contract["objective"],
        "scope": task_contract["scope"],
        "input_refs": task_contract["input_refs"],
        "deliverables": task_contract["deliverables"],
        "acceptance_criteria": task_contract["acceptance_criteria"],
        "constraints": task_contract["constraints"],
        "dependencies": task_contract["dependencies"],
        "priority": task_contract["priority"],
        "coordinator_notes": task_contract["coordinator_notes"],
        "human_collaboration": human_collaboration,
        "submission_confirmation": submission_confirmation,
        "ai_dialogue_collaboration": ai_dialogue_collaboration,
        "required_member_skill": required_member_skill,
        "acceptance_policy": acceptance_policy,
        "independence_mode": independence_mode,
        "skill_name": "ai-sop-member",
        "minimum_skill_version": required_member_skill["version"],
        "protocol_version": project["protocol_version"],
        "project_schema_version": project["project_schema_version"],
        "baseline_version": baseline,
        "baseline_refs": baseline_refs,
        "allowed_sources": ["member-owned-materials", "authorized-project-files"],
        "allowed_actions": allowed_actions,
        "forbidden_actions": forbidden_actions,
        "required_outputs": required_outputs,
        "quality_checks": quality_checks,
        "deadline": deadline,
        "return_to": project["coordinator_id"],
        "status": "distributed",
        "created_at": now_iso(),
    }
    assignment["task_contract_hash"] = hashlib.sha256(
        json.dumps(member_task_contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return path, assignment


def normalized_cli_values(values: list[str] | None, field: str, *, required: bool) -> list[str]:
    normalized = [str(value).strip() for value in (values or []) if str(value).strip()]
    if required and not normalized:
        raise SopError(f"Task intake requires at least one {field}")
    return normalized


def task_contract_from_args(args: argparse.Namespace) -> dict[str, Any]:
    task_source = str(args.task_source).strip()
    objective = str(args.objective).strip()
    if not task_source:
        raise SopError("Task intake requires a non-empty --task-source")
    if not objective:
        raise SopError("Task intake requires a non-empty --objective")
    return {
        "task_source": task_source,
        "objective": objective,
        "scope": {
            "included": normalized_cli_values(args.scope_in, "--scope-in", required=True),
            "excluded": normalized_cli_values(args.scope_out, "--scope-out", required=False),
        },
        "input_refs": normalized_cli_values(args.input_ref, "--input-ref", required=False),
        "deliverables": normalized_cli_values(
            args.deliverable, "--deliverable", required=True
        ),
        "acceptance_criteria": normalized_cli_values(
            args.acceptance_criterion, "--acceptance-criterion", required=True
        ),
        "constraints": normalized_cli_values(args.constraint, "--constraint", required=False),
        "dependencies": normalized_cli_values(args.dependency, "--dependency", required=False),
        "priority": str(args.priority),
        "coordinator_notes": normalized_cli_values(
            args.coordinator_note, "--coordinator-note", required=False
        ),
    }


def assignment_preview_token(plans: list[tuple[Path, dict[str, Any]]]) -> str:
    payload = []
    for _, assignment in plans:
        stable = {
            key: value
            for key, value in assignment.items()
            if key not in {"created_at", "dispatch_confirmation"}
        }
        payload.append(stable)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def confirm_assignment_preview(
    plans: list[tuple[Path, dict[str, Any]]],
    project: dict[str, Any],
    confirmation: str | None,
) -> bool:
    token = assignment_preview_token(plans)
    if not confirmation:
        print(
            json.dumps(
                {
                    "status": "awaiting-human-confirmation",
                    "confirmation_token": token,
                    "instruction": (
                        "Review this exact preview, then rerun the same command with "
                        f"--confirm-dispatch {token}"
                    ),
                    "assignments": [assignment for _, assignment in plans],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return False
    if confirmation != token:
        raise SopError(
            "Dispatch confirmation does not match the current preview; "
            "review the new preview and confirm its token"
        )
    confirmed_at = now_iso()
    for _, assignment in plans:
        assignment["dispatch_confirmation"] = {
            "status": "confirmed",
            "confirmation_token": token,
            "confirmed_by": project["coordinator_id"],
            "confirmed_at": confirmed_at,
        }
    return True


def commit_assignments(
    plans: list[tuple[Path, dict[str, Any]]],
    state_path: Path,
    state: dict[str, Any],
    round_record: dict[str, Any],
) -> None:
    created: list[Path] = []
    try:
        for path, assignment in plans:
            dump_data(path, assignment)
            created.append(path)
        assignment_ids = {str(assignment["assignment_id"]) for _, assignment in plans}
        kinds = {str(assignment["assignment_kind"]) for _, assignment in plans}
        state["expected_assignments"] = sorted(
            set(state.get("expected_assignments", [])) | assignment_ids
        )
        state["status"] = "collecting"
        round_record["assignment_ids"] = sorted(
            set(round_record.get("assignment_ids", [])) | assignment_ids
        )
        round_record["kinds"] = sorted(set(round_record.get("kinds", [])) | kinds)
        state["updated_at"] = now_iso()
        dump_data(state_path, state)
    except Exception as exc:
        for path in created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        if isinstance(exc, SopError):
            raise
        raise SopError(f"Could not commit assignments atomically: {exc}") from exc


def cmd_create_assignment(args: argparse.Namespace) -> None:
    root, project, stage_path, state_path, state, round_id, reviewed = assignment_context(args)
    collaboration_model = str(project.get("collaboration_model", "role-based"))
    member_id = safe_id(args.member_id)
    if collaboration_model == "collective-participation":
        expected_members = active_member_ids(root, project)
        participation_mode = "individual-exception"
    else:
        expected_members = sorted(
            set(
                [member_id]
                + list(
                    state.get("rounds", {})
                    .get(round_id, {})
                    .get("expected_member_ids", [])
                )
            )
        )
        participation_mode = "role-assigned"
    round_record = prepare_round_record(
        state, round_id, collaboration_model, participation_mode, expected_members
    )
    if args.kind == "shared-review":
        target_round = safe_id(args.review_of_round)
        existing_target = round_record.get("review_of_round")
        if existing_target and existing_target != target_round:
            raise SopError(f"Round {round_id} already reviews {existing_target}")
        round_record["review_of_round"] = target_round
    participation_mode = str(round_record["participation_mode"])
    task_contract = task_contract_from_args(args)
    plan = build_assignment(
        root=root,
        project=project,
        stage_path=stage_path,
        stage=args.stage,
        round_id=round_id,
        member_id=member_id,
        kind=args.kind,
        task_contract=task_contract,
        independence_mode=args.independence_mode,
        deadline=args.deadline,
        participation_mode=participation_mode,
        reviewed_round=reviewed,
        review_of_round=args.review_of_round,
        human_collaboration_mode=args.human_collaboration_mode,
        human_collaboration_max_questions=args.human_collaboration_max_questions,
    )
    if not confirm_assignment_preview([plan], project, args.confirm_dispatch):
        return
    commit_assignments([plan], state_path, state, round_record)
    refresh_participation_matrix(args.project_root, args.stage, round_id)
    print(plan[0])


def cmd_create_collective_round(args: argparse.Namespace) -> None:
    root, project, stage_path, state_path, state, round_id, reviewed = assignment_context(args)
    if project.get("collaboration_model") != "collective-participation":
        raise SopError("create-collective-round requires collective-participation mode")
    members = active_member_ids(root, project)
    if not members:
        raise SopError("Collective round requires at least one active member")
    round_record = prepare_round_record(
        state, round_id, "collective-participation", "collective-round", members
    )
    round_record["participation_mode"] = "collective-round"
    if args.kind == "shared-review":
        target_round = safe_id(args.review_of_round)
        existing_target = round_record.get("review_of_round")
        if existing_target and existing_target != target_round:
            raise SopError(f"Round {round_id} already reviews {existing_target}")
        round_record["review_of_round"] = target_round
    task_contract = task_contract_from_args(args)
    plans = [
        build_assignment(
            root=root,
            project=project,
            stage_path=stage_path,
            stage=args.stage,
            round_id=round_id,
            member_id=member_id,
            kind=args.kind,
            task_contract=task_contract,
            independence_mode=args.independence_mode,
            deadline=args.deadline,
            participation_mode="collective-round",
            reviewed_round=reviewed,
            review_of_round=args.review_of_round,
            human_collaboration_mode=args.human_collaboration_mode,
            human_collaboration_max_questions=args.human_collaboration_max_questions,
        )
        for member_id in members
    ]
    if not confirm_assignment_preview(plans, project, args.confirm_dispatch):
        return
    commit_assignments(plans, state_path, state, round_record)
    refresh_participation_matrix(args.project_root, args.stage, round_id)
    print(json.dumps({"round_id": round_id, "assignments": [str(path) for path, _ in plans]}))


def find_submission(stage_path: Path, assignment: dict[str, Any]) -> Path:
    return (
        stage_path
        / "submissions"
        / str(assignment["member_id"])
        / f"{assignment['assignment_id']}-v{assignment['assignment_version']}"
    )


def active_assignment_ids(state: dict[str, Any]) -> list[str]:
    superseded = {
        str(assignment_id)
        for record in state.get("rounds", {}).values()
        if isinstance(record, dict) and record.get("status") == "superseded"
        for assignment_id in record.get("assignment_ids", [])
    }
    return [
        str(assignment_id)
        for assignment_id in state.get("expected_assignments", [])
        if str(assignment_id) not in superseded
    ]


def inspect_stage(
    project_root: str | Path, stage: str, round_id: str | None = None
) -> dict[str, Any]:
    root = sop_root(project_root)
    project = load_data(root / "project-state.yaml")
    require_current_schema(project)
    stage_path = stage_root(project_root, stage)
    state = load_data(stage_path / "stage-state.yaml")
    valid: list[dict[str, Any]] = []
    missing: list[str] = []
    invalid: list[dict[str, str]] = []
    assignment_ids = active_assignment_ids(state)
    if round_id is not None:
        record = state.get("rounds", {}).get(round_id)
        if not isinstance(record, dict):
            raise SopError(f"Unknown round: {round_id}")
        if record.get("status") == "superseded":
            raise SopError(f"Round {round_id} is superseded and is not executable")
        assignment_ids = list(record.get("assignment_ids", []))
    for assignment_id in assignment_ids:
        matches = list((stage_path / "dispatch").glob(f"{assignment_id}.yaml"))
        if not matches:
            invalid.append({"assignment_id": assignment_id, "reason": "assignment-file-missing"})
            continue
        assignment = load_data(matches[0])
        submission = find_submission(stage_path, assignment)
        if not submission.is_dir():
            missing.append(assignment_id)
            continue
        required_files = assignment.get("required_outputs", list(REQUIRED_SUBMISSION_FILES))
        if not isinstance(required_files, list):
            required_files = list(REQUIRED_SUBMISSION_FILES)
        absent = [str(name) for name in required_files if not (submission / str(name)).is_file()]
        if absent:
            invalid.append(
                {"assignment_id": assignment_id, "reason": f"missing-files:{','.join(absent)}"}
            )
            continue
        try:
            manifest = load_data(submission / "submission-manifest.yaml")
        except SopError as exc:
            invalid.append({"assignment_id": assignment_id, "reason": str(exc)})
            continue
        expected = {
            "assignment_id": assignment_id,
            "assignment_version": str(assignment["assignment_version"]),
            "member_id": str(assignment["member_id"]),
            "git_branch": str(assignment["git_branch"]),
            "main_branch": str(assignment["main_branch"]),
            "stage_id": str(assignment["stage_id"]),
            "round_id": str(assignment["round_id"]),
            "assignment_kind": str(assignment["assignment_kind"]),
            "protocol_version": str(assignment["protocol_version"]),
            "project_schema_version": str(assignment["project_schema_version"]),
            "baseline_version": str(assignment["baseline_version"]),
            "collaboration_model": str(
                assignment.get("collaboration_model", project.get("collaboration_model", "role-based"))
            ),
            "participation_mode": str(
                assignment.get("participation_mode", "role-assigned")
            ),
            "review_of_round": str(assignment.get("review_of_round")),
            "human_collaboration": str(assignment.get("human_collaboration")),
            "status": "submitted",
        }
        if requires_submission_confirmation(assignment):
            try:
                expected["human_owner"] = str(assignment["human_owner"])
                expected_confirmation_policy = validate_submission_confirmation_policy(
                    assignment
                )
            except SopError as exc:
                invalid.append({"assignment_id": assignment_id, "reason": str(exc)})
                continue
        mismatches = [
            key for key, value in expected.items() if str(manifest.get(key)) != value
        ]
        if requires_submission_confirmation(assignment) and manifest.get(
            "submission_confirmation"
        ) != expected_confirmation_policy:
            mismatches.append("submission_confirmation")
        if mismatches:
            invalid.append(
                {"assignment_id": assignment_id, "reason": f"manifest-mismatch:{','.join(mismatches)}"}
            )
            continue
        try:
            confirmation = validate_local_submission_confirmation(
                submission, assignment, manifest
            )
        except (OSError, UnicodeError, SopError) as exc:
            invalid.append({"assignment_id": assignment_id, "reason": str(exc)})
            continue
        valid.append(
            {
                "assignment_id": assignment_id,
                "member_id": assignment["member_id"],
                "collaboration_model": assignment.get("collaboration_model", "role-based"),
                "participation_mode": assignment.get("participation_mode", "role-assigned"),
                "submission": submission.relative_to(sop_root(project_root)).as_posix(),
                "human_submission_confirmation": confirmation,
            }
        )
    result = {
        "stage_id": stage,
        "round_id": round_id,
        "stage_status": state.get("status"),
        "valid_submissions": valid,
        "missing_submissions": missing,
        "invalid_submissions": invalid,
    }
    result["participation_issues"] = collective_participation_issues(
        project_root, stage, state, result, round_id
    )
    return result


def default_remote_member_cli() -> Path:
    candidates = (
        Path(__file__).resolve().with_name("sop_member_cli.py"),
        Path(__file__).resolve().parent.parent
        / "assets"
        / "remote-validator"
        / "member_cli.py",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SopError(
        "Trusted remote Member CLI is unavailable; expected a sibling "
        "sop_member_cli.py or assets/remote-validator/member_cli.py"
    )


def member_cli_release(path: Path) -> tuple[str, str] | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    version = re.search(r'^SKILL_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    build = re.search(r'^BUILD_ID\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not version or not build:
        return None
    return version.group(1), build.group(1)


def select_remote_member_cli(base: Path, assignment: dict[str, Any]) -> Path:
    required = assignment.get("required_member_skill")
    if not isinstance(required, dict):
        return base
    expected = (str(required.get("version", "")), str(required.get("build_id", "")))
    suffix = expected[0].replace(".", "_")
    candidates = [
        base,
        base.with_name(f"{base.stem}_{suffix}{base.suffix}"),
        base.parent / f"member_cli_{suffix}.py",
    ]
    for candidate in dict.fromkeys(candidates):
        if member_cli_release(candidate) == expected:
            return candidate
    raise SopError(
        "Trusted remote Member CLI release is unavailable for "
        f"{expected[0]}/{expected[1]}"
    )


def inspect_authoritative_stage(
    project_root: str | Path,
    stage: str,
    round_id: str | None = None,
    remote: str = "origin",
) -> dict[str, Any]:
    """Validate submissions from exact registered remote branch commits."""
    root = sop_root(project_root)
    project = load_data(root / "project-state.yaml")
    require_current_schema(project)
    stage_path = stage_root(project_root, stage)
    state = load_data(stage_path / "stage-state.yaml")
    git_root = find_git_root(Path(project_root))
    if git_root is None:
        return inspect_stage(project_root, stage, round_id)
    remote_url = run_git(git_root, "remote", "get-url", remote, check=False)
    if remote_url.returncode != 0:
        return inspect_stage(project_root, stage, round_id)
    run_git(git_root, "fetch", remote, "--prune")

    assignment_ids = active_assignment_ids(state)
    if round_id is not None:
        record = state.get("rounds", {}).get(round_id)
        if not isinstance(record, dict):
            raise SopError(f"Unknown round: {round_id}")
        if record.get("status") == "superseded":
            raise SopError(f"Round {round_id} is superseded and is not executable")
        assignment_ids = list(record.get("assignment_ids", []))

    base_member_cli = default_remote_member_cli()
    valid: list[dict[str, Any]] = []
    missing: list[str] = []
    invalid: list[dict[str, str]] = []
    for assignment_id in assignment_ids:
        assignment_path = stage_path / "dispatch" / f"{assignment_id}.yaml"
        if not assignment_path.is_file():
            invalid.append(
                {"assignment_id": assignment_id, "reason": "assignment-file-missing"}
            )
            continue
        assignment = load_data(assignment_path)
        try:
            member_cli = select_remote_member_cli(base_member_cli, assignment)
        except SopError as exc:
            invalid.append({"assignment_id": assignment_id, "reason": str(exc)})
            continue
        member_id = safe_id(str(assignment["member_id"]))
        branch = str(assignment.get("git_branch", default_member_branch(member_id)))
        observed = resolve_observation_ref(git_root, branch, remote)
        if observed is None:
            invalid.append(
                {
                    "assignment_id": assignment_id,
                    "reason": f"registered-remote-branch-unavailable:{branch}",
                }
            )
            continue
        observed_ref, observed_head = observed
        submission = find_submission(stage_path, assignment)
        submission_commit = resolve_submission_commit(
            git_root, observed_ref, submission
        )
        if submission_commit is None:
            missing.append(assignment_id)
            continue
        manifest = read_git_mapping(
            git_root, submission_commit, submission / "submission-manifest.yaml"
        )
        if manifest is None:
            missing.append(assignment_id)
            continue
        if str(manifest.get("status", "")) != "submitted":
            invalid.append(
                {
                    "assignment_id": assignment_id,
                    "reason": f"remote-manifest-status:{manifest.get('status')}",
                }
            )
            continue
        if not git_submission_files_complete(
            git_root, submission_commit, submission, assignment
        ):
            invalid.append(
                {
                    "assignment_id": assignment_id,
                    "reason": "required-remote-submission-files-missing",
                }
            )
            continue
        remote_valid, remote_reason = validate_remote_submission(
            git_root=git_root,
            observed_ref=observed_ref,
            observed_head=observed_head,
            submission_commit=submission_commit,
            assignment_path=assignment_path,
            submission_path=submission,
            member_id=member_id,
            member_cli=member_cli,
            remote=remote,
        )
        if not remote_valid:
            invalid.append(
                {
                    "assignment_id": assignment_id,
                    "reason": remote_reason or "remote-validation-failed",
                }
            )
            continue
        valid.append(
            {
                "assignment_id": assignment_id,
                "member_id": member_id,
                "collaboration_model": assignment.get(
                    "collaboration_model", "role-based"
                ),
                "participation_mode": assignment.get(
                    "participation_mode", "role-assigned"
                ),
                "submission": submission.relative_to(root).as_posix(),
                "observed_ref": observed_ref,
                "observed_head": observed_head,
                "observed_submission_commit": submission_commit,
                "submitted_at": manifest.get("submitted_at"),
                "human_submission_confirmation": submission_confirmation_projection(
                    assignment, manifest
                ),
            }
        )

    result = {
        "stage_id": stage,
        "round_id": round_id,
        "stage_status": state.get("status"),
        "observation_mode": "exact-remote-ref",
        "remote": remote,
        "valid_submissions": valid,
        "missing_submissions": missing,
        "invalid_submissions": invalid,
    }
    result["participation_issues"] = collective_participation_issues(
        project_root, stage, state, result, round_id
    )
    return result


def parse_mapping_text(text: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        if not yaml:
            raise SopError(f"Cannot parse non-JSON YAML from {label}")
        try:
            data = yaml.safe_load(text)
        except Exception as exc:
            raise SopError(f"Cannot parse {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise SopError(f"Expected a mapping in {label}")
    return data


def resolve_observation_ref(git_root: Path, branch: str, remote: str) -> tuple[str, str] | None:
    candidates: list[str] = []
    remote_branch = f"{remote}/{branch}" if remote and not branch.startswith(f"{remote}/") else None
    if remote_branch:
        candidates.append(remote_branch)
    candidates.append(branch)
    for candidate in candidates:
        result = run_git(git_root, "rev-parse", "--verify", f"{candidate}^{{commit}}", check=False)
        if result.returncode == 0:
            return candidate, result.stdout.strip()
    return None


def read_git_mapping(git_root: Path, ref: str, path: Path) -> dict[str, Any] | None:
    try:
        relative = path.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        return None
    result = run_git(git_root, "show", f"{ref}:{relative}", check=False)
    if result.returncode != 0:
        return None
    try:
        return parse_mapping_text(result.stdout, f"{ref}:{relative}")
    except SopError as exc:
        return {"status": "submitted", "__parse_error__": str(exc)}


def read_git_text(git_root: Path, ref: str, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        return None
    result = run_git(git_root, "show", f"{ref}:{relative}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def git_submission_files_complete(
    git_root: Path, ref: str, submission: Path, assignment: dict[str, Any]
) -> bool:
    try:
        relative_root = submission.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        return False
    required_files = assignment.get("required_outputs", list(REQUIRED_SUBMISSION_FILES))
    if not isinstance(required_files, list):
        return False
    for name in required_files:
        result = run_git(
            git_root,
            "cat-file",
            "-e",
            f"{ref}:{relative_root}/{name}",
            check=False,
        )
        if result.returncode != 0:
            return False
    return True


def resolve_submission_commit(
    git_root: Path, observed_ref: str, submission_path: Path
) -> str | None:
    """Resolve the newest commit that changed this exact submission directory."""
    submission_relative = git_relative_path(git_root, submission_path)
    result = run_git(
        git_root,
        "log",
        "-1",
        "--format=%H",
        observed_ref,
        "--",
        submission_relative,
        check=False,
    )
    commit = result.stdout.strip() if result.returncode == 0 else ""
    if not commit:
        return None
    reachable = run_git(
        git_root,
        "merge-base",
        "--is-ancestor",
        commit,
        observed_ref,
        check=False,
    )
    return commit if reachable.returncode == 0 else None


def validate_remote_submission(
    *,
    git_root: Path,
    observed_ref: str,
    observed_head: str,
    submission_commit: str,
    assignment_path: Path,
    submission_path: Path,
    member_id: str,
    member_cli: Path,
    remote: str,
) -> tuple[bool, str | None]:
    if not member_cli.is_file():
        return False, f"remote-validator-missing:{member_cli}"
    assignment_relative = git_relative_path(git_root, assignment_path)
    submission_relative = git_relative_path(git_root, submission_path)
    temporary_root = Path(tempfile.mkdtemp(prefix="ai-sop-remote-validation-"))
    temporary = temporary_root / "worktree"
    added = False
    try:
        result = run_git(
            git_root,
            "worktree",
            "add",
            "--detach",
            str(temporary),
            submission_commit,
            check=False,
        )
        if result.returncode != 0:
            return False, "remote-worktree-add-failed:" + (
                result.stderr or result.stdout
            ).strip()
        added = True
        validation = subprocess.run(
            [
                sys.executable,
                str(member_cli),
                "validate",
                str(temporary / submission_relative),
                "--assignment",
                str(temporary / assignment_relative),
                "--member-id",
                member_id,
                "--remote",
                remote,
                "--detached-validation",
            ],
            cwd=temporary,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if validation.returncode != 0:
            detail = (validation.stderr or validation.stdout).strip()
            return False, f"remote-validation-failed:{detail}"
        exact = run_git(git_root, "rev-parse", observed_ref, check=False).stdout.strip()
        if exact != observed_head:
            return False, "remote-ref-changed-during-validation"
        return True, None
    finally:
        if added:
            run_git(
                git_root,
                "worktree",
                "remove",
                "--force",
                str(temporary),
                check=False,
            )
        shutil.rmtree(temporary_root, ignore_errors=True)
        run_git(git_root, "worktree", "prune", check=False)


def manifest_mismatch_fields(
    manifest: dict[str, Any], assignment: dict[str, Any], project: dict[str, Any]
) -> list[str]:
    expected = {
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "member_id": str(assignment["member_id"]),
        "git_branch": str(assignment["git_branch"]),
        "main_branch": str(assignment["main_branch"]),
        "stage_id": str(assignment["stage_id"]),
        "round_id": str(assignment["round_id"]),
        "assignment_kind": str(assignment["assignment_kind"]),
        "protocol_version": str(assignment["protocol_version"]),
        "project_schema_version": str(assignment["project_schema_version"]),
        "baseline_version": str(assignment["baseline_version"]),
        "collaboration_model": str(
            assignment.get("collaboration_model", project.get("collaboration_model", "role-based"))
        ),
        "participation_mode": str(assignment.get("participation_mode", "role-assigned")),
        "review_of_round": str(assignment.get("review_of_round")),
        "human_collaboration": str(assignment.get("human_collaboration")),
    }
    expected_confirmation_policy = None
    if requires_submission_confirmation(assignment):
        expected["human_owner"] = str(assignment.get("human_owner"))
        expected_confirmation_policy = validate_submission_confirmation_policy(assignment)
    mismatches = [
        key for key, value in expected.items() if str(manifest.get(key)) != value
    ]
    if expected_confirmation_policy is not None and manifest.get(
        "submission_confirmation"
    ) != expected_confirmation_policy:
        mismatches.append("submission_confirmation")
    return mismatches


def acceptance_receipt_path(stage_path: Path, assignment: dict[str, Any]) -> Path:
    member_id = safe_id(str(assignment["member_id"]))
    assignment_id = safe_id(str(assignment["assignment_id"]))
    version = str(assignment["assignment_version"])
    return stage_path / "acceptances" / member_id / f"{assignment_id}-v{version}.yaml"


def assignment_acceptance_projection(
    *,
    git_root: Path | None,
    stage_path: Path,
    assignment_path: Path,
    assignment: dict[str, Any],
    observed_ref: str | None,
    observed_head: str | None,
    previous_record: dict[str, Any] | None,
) -> dict[str, Any]:
    if not requires_assignment_acceptance(assignment):
        return {"required": False, "status": "legacy-not-required", "gate_effect": "none"}
    try:
        policy = assignment_acceptance_policy(assignment)
    except SopError as exc:
        return {
            "required": True,
            "status": "invalid",
            "validation_reason": str(exc),
            "gate_effect": "none",
        }
    receipt_path = acceptance_receipt_path(stage_path, assignment)
    result: dict[str, Any] = {
        "required": True,
        "status": "pending",
        "accepted_at": None,
        "observed_at": None,
        "observed_ref": observed_ref,
        "observed_head": observed_head,
        "observed_acceptance_commit": None,
        "receipt_path": receipt_path.relative_to(stage_path.parent.parent).as_posix(),
        "validation_reason": None,
        "gate_effect": "none",
    }
    if git_root is None or observed_ref is None or observed_head is None:
        return result
    acceptance_commit = resolve_submission_commit(git_root, observed_ref, receipt_path)
    if acceptance_commit is None:
        return result
    result["observed_acceptance_commit"] = acceptance_commit
    receipt = read_git_mapping(git_root, acceptance_commit, receipt_path)
    if receipt is None:
        return result
    if receipt.get("__parse_error__"):
        result["status"] = "invalid"
        result["validation_reason"] = str(receipt["__parse_error__"])
        return result
    required_skill = assignment.get("required_member_skill", {})
    expected = {
        "schema_version": str(policy["receipt_schema_version"]),
        "status": "accepted",
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "member_id": str(assignment["member_id"]),
        "human_owner": str(assignment.get("human_owner", "")),
        "git_branch": str(assignment["git_branch"]),
        "assignment_path": git_relative_path(git_root, assignment_path),
        "assignment_document_hash": "sha256:"
        + hashlib.sha256(assignment_path.read_bytes()).hexdigest(),
        "task_contract_hash": str(assignment.get("task_contract_hash", "")),
        "receipt_path": git_relative_path(git_root, receipt_path),
        "acceptance_method": "explicit-member-command",
        "gate_effect": "none",
        "member_skill": {
            "name": "ai-sop-member",
            "version": str(required_skill.get("version", "")),
            "build_id": str(required_skill.get("build_id", "")),
        },
    }
    mismatches = [key for key, value in expected.items() if receipt.get(key) != value]
    if mismatches or not str(receipt.get("accepted_at", "")).strip():
        result["status"] = "invalid"
        result["validation_reason"] = (
            "acceptance-receipt-mismatch:" + ",".join(mismatches)
            if mismatches
            else "acceptance-receipt-accepted-at-missing"
        )
        return result
    previous_acceptance = (
        previous_record.get("assignment_acceptance", {})
        if isinstance(previous_record, dict)
        else {}
    )
    prior_observed = (
        previous_acceptance.get("observed_at")
        if previous_acceptance.get("observed_acceptance_commit") == acceptance_commit
        else None
    )
    result.update(
        {
            "status": "accepted",
            "accepted_at": receipt["accepted_at"],
            "observed_at": prior_observed or now_iso(),
            "validation_reason": None,
        }
    )
    return result


def refresh_project_state(
    project_root: str | Path,
    source: str,
    remote: str = "origin",
    validate_remote: bool = False,
    member_cli: Path | None = None,
) -> Path:
    root = sop_root(project_root)
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    require_current_schema(project)
    git_root = find_git_root(Path(project_root))
    stage_projections: dict[str, Any] = {}
    total_expected = total_submitted = total_valid = total_pending = 0
    total_invalid = total_missing = total_in_progress = 0
    total_confirmation_required = total_confirmation_confirmed = 0
    total_confirmation_pending = total_confirmation_legacy = 0
    total_confirmation_attention = 0
    total_acceptance_required = total_acceptance_accepted = 0
    total_acceptance_pending = total_acceptance_invalid = 0
    previous = project.get("submission_tracking", {})
    previous_stages = previous.get("stages", {}) if isinstance(previous, dict) else {}

    for stage in STAGES:
        stage_path = stage_root(project_root, stage)
        state = load_data(stage_path / "stage-state.yaml")
        inspection = inspect_stage(project_root, stage)
        valid_ids = {str(item["assignment_id"]) for item in inspection["valid_submissions"]}
        invalid_reasons = {
            str(item["assignment_id"]): str(item["reason"])
            for item in inspection["invalid_submissions"]
        }
        records: dict[str, Any] = {}
        submitted_members: set[str] = set()
        missing_members: set[str] = set()
        pending_members: set[str] = set()
        last_submission_at: str | None = None

        for raw_assignment_id in sorted(active_assignment_ids(state)):
            assignment_id = safe_id(raw_assignment_id)
            assignment_path = stage_path / "dispatch" / f"{assignment_id}.yaml"
            if not assignment_path.is_file():
                records[assignment_id] = {
                    "assignment_id": assignment_id,
                    "status": "invalid",
                    "validation_status": "invalid",
                    "validation_reason": "assignment-file-missing",
                }
                continue
            assignment = load_data(assignment_path)
            member_id = safe_id(str(assignment["member_id"]))
            submission = find_submission(stage_path, assignment)
            manifest_path = submission / "submission-manifest.yaml"
            manifest = load_data(manifest_path) if manifest_path.is_file() else None
            observation_source = "working-tree" if manifest is not None else None
            observed_ref = None
            observed_head = None
            observed_submission_commit = None
            remote_files_complete = False
            previous_stage = (
                previous_stages.get(stage, {}) if isinstance(previous_stages, dict) else {}
            )
            previous_records = (
                previous_stage.get("records", {}) if isinstance(previous_stage, dict) else {}
            )
            previous_record = (
                previous_records.get(assignment_id)
                if isinstance(previous_records, dict)
                else None
            )

            branch = str(assignment.get("git_branch", default_member_branch(member_id)))
            if git_root is not None:
                resolved = resolve_observation_ref(git_root, branch, remote)
                if resolved:
                    observed_ref, observed_head = resolved
                    observed_submission_commit = resolve_submission_commit(
                        git_root, observed_ref, submission
                    )
                    git_manifest = (
                        read_git_mapping(
                            git_root, observed_submission_commit, manifest_path
                        )
                        if observed_submission_commit is not None
                        else None
                    )
                    if git_manifest is not None and (
                        manifest is None
                        or str(git_manifest.get("submitted_at", ""))
                        >= str(manifest.get("submitted_at", ""))
                    ):
                        manifest = git_manifest
                        observation_source = f"git:{observed_ref}"
                        remote_files_complete = git_submission_files_complete(
                            git_root,
                            observed_submission_commit,
                            submission,
                            assignment,
                        )

            status = "missing"
            validation_status = "not-submitted"
            validation_reason = None
            if manifest is not None:
                status = str(manifest.get("status", "in-progress"))
                parse_error = str(manifest.get("__parse_error__", "")).strip()
                policy_error = None
                try:
                    mismatches = manifest_mismatch_fields(manifest, assignment, project)
                except SopError as exc:
                    mismatches = []
                    policy_error = str(exc)
                if parse_error:
                    validation_status = "invalid"
                    validation_reason = parse_error
                elif policy_error:
                    validation_status = "invalid"
                    validation_reason = policy_error
                elif mismatches:
                    validation_status = "invalid"
                    validation_reason = "manifest-mismatch:" + ",".join(mismatches)
                elif assignment_id in valid_ids:
                    validation_status = "valid"
                elif assignment_id in invalid_reasons and observation_source == "working-tree":
                    validation_status = "invalid"
                    validation_reason = invalid_reasons[assignment_id]
                elif (
                    status == "submitted"
                    and observation_source
                    and observation_source.startswith("git:")
                    and remote_files_complete
                    and validate_remote
                    and git_root is not None
                    and observed_ref is not None
                    and observed_head is not None
                    and observed_submission_commit is not None
                    and member_cli is not None
                ):
                    try:
                        selected_member_cli = select_remote_member_cli(member_cli, assignment)
                    except SopError as exc:
                        remote_valid, remote_reason = False, str(exc)
                    else:
                        remote_valid, remote_reason = validate_remote_submission(
                            git_root=git_root,
                            observed_ref=observed_ref,
                            observed_head=observed_head,
                            submission_commit=observed_submission_commit,
                            assignment_path=assignment_path,
                            submission_path=submission,
                            member_id=member_id,
                            member_cli=selected_member_cli,
                            remote=remote,
                        )
                    validation_status = "valid" if remote_valid else "invalid"
                    validation_reason = remote_reason
                elif status == "submitted" and (
                    observation_source == "working-tree" or remote_files_complete
                ):
                    validation_status = "pending-validation"
                elif status == "submitted":
                    validation_status = "invalid"
                    validation_reason = "required-submission-files-missing"
                else:
                    validation_status = "not-submitted"

            confirmation = submission_confirmation_projection(assignment, manifest)
            acceptance = assignment_acceptance_projection(
                git_root=git_root,
                stage_path=stage_path,
                assignment_path=assignment_path,
                assignment=assignment,
                observed_ref=observed_ref,
                observed_head=observed_head,
                previous_record=previous_record,
            )

            if status == "submitted":
                submitted_members.add(member_id)
                submitted_at = str(manifest.get("submitted_at", "")) if manifest else ""
                if submitted_at and (last_submission_at is None or submitted_at > last_submission_at):
                    last_submission_at = submitted_at
            elif status == "in-progress":
                pass
            else:
                missing_members.add(member_id)
            if validation_status == "pending-validation":
                pending_members.add(member_id)

            records[assignment_id] = {
                "assignment_id": assignment_id,
                "assignment_version": str(assignment["assignment_version"]),
                "member_id": member_id,
                "round_id": str(assignment.get("round_id", "")),
                "assignment_kind": str(assignment.get("assignment_kind", "")),
                "git_branch": branch,
                "observed_ref": observed_ref,
                "observed_head": observed_head,
                "observed_submission_commit": observed_submission_commit,
                "status": status,
                "validation_status": validation_status,
                "validation_reason": validation_reason,
                "submitted_at": manifest.get("submitted_at") if manifest else None,
                "submission_path": str(submission.relative_to(root)),
                "observation_source": observation_source,
                "sources_count": manifest.get("sources_count", 0) if manifest else 0,
                "assumptions_count": manifest.get("assumptions_count", 0) if manifest else 0,
                "new_requirements_count": manifest.get("new_requirements_count", 0)
                if manifest
                else 0,
                "risks_count": manifest.get("risks_count", 0) if manifest else 0,
                "human_submission_confirmation": confirmation,
                "assignment_acceptance": acceptance,
            }

        expected_count = len(records)
        submitted_count = sum(1 for item in records.values() if item["status"] == "submitted")
        in_progress_count = sum(1 for item in records.values() if item["status"] == "in-progress")
        valid_count = sum(1 for item in records.values() if item["validation_status"] == "valid")
        pending_count = sum(
            1 for item in records.values() if item["validation_status"] == "pending-validation"
        )
        invalid_count = sum(
            1 for item in records.values() if item["validation_status"] == "invalid"
        )
        missing_count = sum(1 for item in records.values() if item["status"] == "missing")
        confirmation_required_count = sum(
            1
            for item in records.values()
            if item.get("human_submission_confirmation", {}).get("required") is True
        )
        confirmation_confirmed_count = sum(
            1
            for item in records.values()
            if item.get("human_submission_confirmation", {}).get("status") == "confirmed"
        )
        confirmation_pending_count = sum(
            1
            for item in records.values()
            if item.get("human_submission_confirmation", {}).get("required") is True
            and item.get("human_submission_confirmation", {}).get("status") != "confirmed"
        )
        confirmation_legacy_count = sum(
            1
            for item in records.values()
            if item.get("human_submission_confirmation", {}).get("status")
            == "legacy-not-required"
        )
        confirmation_attention_count = sum(
            1
            for item in records.values()
            if item.get("human_submission_confirmation", {}).get("requires_review") is True
        )
        acceptance_required_count = sum(
            1
            for item in records.values()
            if item.get("assignment_acceptance", {}).get("required") is True
        )
        acceptance_accepted_count = sum(
            1
            for item in records.values()
            if item.get("assignment_acceptance", {}).get("status") == "accepted"
        )
        acceptance_pending_count = sum(
            1
            for item in records.values()
            if item.get("assignment_acceptance", {}).get("status") == "pending"
        )
        acceptance_invalid_count = sum(
            1
            for item in records.values()
            if item.get("assignment_acceptance", {}).get("status") == "invalid"
        )
        active_round_ids = [
            str(round_id)
            for round_id, round_record in state.get("rounds", {}).items()
            if isinstance(round_record, dict)
            and round_record.get("status") == "collecting"
        ]
        stage_projections[stage] = {
            "stage_status": state.get("status"),
            "active_round_ids": active_round_ids,
            "current_round_id": active_round_ids[-1] if active_round_ids else None,
            "expected_count": expected_count,
            "submitted_count": submitted_count,
            "in_progress_count": in_progress_count,
            "valid_count": valid_count,
            "pending_validation_count": pending_count,
            "invalid_count": invalid_count,
            "missing_count": missing_count,
            "confirmation_required_count": confirmation_required_count,
            "confirmation_confirmed_count": confirmation_confirmed_count,
            "confirmation_pending_count": confirmation_pending_count,
            "confirmation_legacy_count": confirmation_legacy_count,
            "confirmation_attention_count": confirmation_attention_count,
            "acceptance_required_count": acceptance_required_count,
            "acceptance_accepted_count": acceptance_accepted_count,
            "acceptance_pending_count": acceptance_pending_count,
            "acceptance_invalid_count": acceptance_invalid_count,
            "submitted_member_ids": sorted(submitted_members),
            "pending_validation_member_ids": sorted(pending_members),
            "missing_member_ids": sorted(missing_members),
            "last_submission_at": last_submission_at,
            "submission_index": f"stages/{stage}/aggregation/submission-index.yaml",
            "records": records,
        }
        total_expected += expected_count
        total_submitted += submitted_count
        total_in_progress += in_progress_count
        total_valid += valid_count
        total_pending += pending_count
        total_invalid += invalid_count
        total_missing += missing_count
        total_confirmation_required += confirmation_required_count
        total_confirmation_confirmed += confirmation_confirmed_count
        total_confirmation_pending += confirmation_pending_count
        total_confirmation_legacy += confirmation_legacy_count
        total_confirmation_attention += confirmation_attention_count
        total_acceptance_required += acceptance_required_count
        total_acceptance_accepted += acceptance_accepted_count
        total_acceptance_pending += acceptance_pending_count
        total_acceptance_invalid += acceptance_invalid_count

    projection = {
        "schema_version": "1.1",
        "observation_mode": "working-tree-and-git-refs",
        "remote": remote,
        "stages": stage_projections,
        "totals": {
            "expected_count": total_expected,
            "submitted_count": total_submitted,
            "in_progress_count": total_in_progress,
            "valid_count": total_valid,
            "pending_validation_count": total_pending,
            "invalid_count": total_invalid,
            "missing_count": total_missing,
            "confirmation_required_count": total_confirmation_required,
            "confirmation_confirmed_count": total_confirmation_confirmed,
            "confirmation_pending_count": total_confirmation_pending,
            "confirmation_legacy_count": total_confirmation_legacy,
            "confirmation_attention_count": total_confirmation_attention,
            "acceptance_required_count": total_acceptance_required,
            "acceptance_accepted_count": total_acceptance_accepted,
            "acceptance_pending_count": total_acceptance_pending,
            "acceptance_invalid_count": total_acceptance_invalid,
        },
    }
    previous_projection = {
        key: value
        for key, value in previous.items()
        if key not in {"revision", "last_refreshed_at", "last_refresh_source"}
    }
    if projection == previous_projection:
        return project_path
    project["submission_tracking"] = {
        **projection,
        "revision": int(previous.get("revision", 0)) + 1,
        "last_refreshed_at": now_iso(),
        "last_refresh_source": source,
    }
    project["updated_at"] = now_iso()
    dump_data(project_path, project)
    return project_path


def collective_participation_issues(
    project_root: str | Path,
    stage: str,
    state: dict[str, Any],
    inspection: dict[str, Any],
    round_id: str | None = None,
) -> list[dict[str, Any]]:
    root = sop_root(project_root)
    project = load_data(root / "project-state.yaml")
    if project.get("collaboration_model") != "collective-participation":
        return []
    active = active_member_ids(root, project)
    valid_ids = {str(item["assignment_id"]) for item in inspection["valid_submissions"]}
    missing_ids = set(str(value) for value in inspection["missing_submissions"])
    invalid_ids = {
        str(item["assignment_id"]) for item in inspection["invalid_submissions"]
    }
    stage_path = stage_root(project_root, stage)
    records = state.get("rounds", {})
    selected = (
        {round_id: records.get(round_id)}
        if round_id is not None
        else records
    )
    issues: list[dict[str, Any]] = []
    if not selected:
        return [{"round_id": None, "reason": "collective-stage-has-no-rounds"}]
    for selected_round_id, raw_record in selected.items():
        if not isinstance(raw_record, dict):
            continue
        if raw_record.get("status") == "superseded":
            continue
        expected = sorted(str(value) for value in raw_record.get("expected_member_ids", []))
        if not expected:
            issues.append(
                {"round_id": selected_round_id, "reason": "expected-members-not-recorded"}
            )
            continue
        if expected != active:
            issues.append(
                {
                    "round_id": selected_round_id,
                    "reason": "active-membership-drift",
                    "expected_member_ids": expected,
                    "active_member_ids": active,
                }
            )
        assignments_by_member: dict[str, list[dict[str, Any]]] = {member_id: [] for member_id in expected}
        for assignment_id in raw_record.get("assignment_ids", []):
            path = stage_path / "dispatch" / f"{assignment_id}.yaml"
            if not path.exists():
                continue
            assignment = load_data(path)
            member_id = str(assignment.get("member_id", ""))
            if member_id in assignments_by_member:
                assignments_by_member[member_id].append(assignment)
        required_kinds = set(str(value) for value in raw_record.get("kinds", []))
        for member_id in expected:
            assignments = assignments_by_member[member_id]
            member_assignment_ids = {
                str(assignment["assignment_id"]) for assignment in assignments
            }
            member_kinds = {
                str(assignment.get("assignment_kind", "")) for assignment in assignments
            }
            absent_kinds = sorted(required_kinds - member_kinds)
            if not assignments or absent_kinds:
                issues.append(
                    {
                        "round_id": selected_round_id,
                        "member_id": member_id,
                        "reason": "member-assignment-coverage-incomplete",
                        "missing_kinds": absent_kinds,
                    }
                )
            missing_for_member = sorted(member_assignment_ids & missing_ids)
            invalid_for_member = sorted(member_assignment_ids & invalid_ids)
            if missing_for_member:
                issues.append(
                    {
                        "round_id": selected_round_id,
                        "member_id": member_id,
                        "reason": "member-submission-missing",
                        "assignment_ids": missing_for_member,
                    }
                )
            if invalid_for_member:
                issues.append(
                    {
                        "round_id": selected_round_id,
                        "member_id": member_id,
                        "reason": "member-submission-invalid",
                        "assignment_ids": invalid_for_member,
                    }
                )
            if member_assignment_ids and member_assignment_ids <= valid_ids:
                pass
        if raw_record.get("shared_review_required") and raw_record.get("status") != "collecting":
            reviewed_members = set(
                str(value) for value in raw_record.get("shared_review_member_ids", [])
            )
            for member_id in sorted(set(expected) - reviewed_members):
                issues.append(
                    {
                        "round_id": selected_round_id,
                        "member_id": member_id,
                        "reason": "shared-review-incomplete",
                    }
                )
    return issues


def participation_matrix_path(project_root: str | Path, stage: str) -> Path:
    return stage_root(project_root, stage) / "aggregation" / "participation-matrix.yaml"


def refresh_participation_matrix(
    project_root: str | Path, stage: str, round_id: str | None = None
) -> Path:
    root = sop_root(project_root)
    project = load_data(root / "project-state.yaml")
    stage_path = stage_root(project_root, stage)
    state = load_data(stage_path / "stage-state.yaml")
    path = participation_matrix_path(project_root, stage)
    matrix = load_data(path) if path.exists() else {}
    matrix.update(
        {
            "artifact_type": "participation-matrix",
            "schema_version": "1.0",
            "stage_id": stage,
            "collaboration_model": project.get("collaboration_model", "role-based"),
        }
    )
    matrix_rounds = matrix.setdefault("rounds", {})
    records = state.get("rounds", {})
    round_ids = [round_id] if round_id is not None else sorted(records)
    for current_round_id in round_ids:
        record = records.get(current_round_id)
        if not isinstance(record, dict):
            continue
        if record.get("status") == "superseded":
            matrix_rounds[current_round_id] = {
                "round_id": current_round_id,
                "status": "superseded",
                "replacement_round_id": record.get("replacement_round_id"),
                "superseded_reason": record.get("superseded_reason"),
                "submission_coverage": 100,
                "shared_review_coverage": 100,
                "participation": [],
                "participation_issues": [],
            }
            continue
        # Closed distributed rounds are validated against exact remote refs and
        # frozen in their submission index.  Re-scanning only the coordinator's
        # working tree here would incorrectly turn valid remote submissions into
        # "missing" until the member branches are merged after Gate approval.
        round_index_path = (
            stage_path
            / "aggregation"
            / "rounds"
            / current_round_id
            / "submission-index.yaml"
        )
        if record.get("status") == "closed" and round_index_path.is_file():
            frozen_index = load_data(round_index_path)
            inspection = {
                "valid_submissions": list(frozen_index.get("valid_submissions", [])),
                "missing_submissions": list(frozen_index.get("missing_submissions", [])),
                "invalid_submissions": list(frozen_index.get("invalid_submissions", [])),
                "participation_issues": [],
            }
        else:
            inspection = inspect_stage(project_root, stage, current_round_id)
        valid_ids = {str(item["assignment_id"]) for item in inspection["valid_submissions"]}
        missing_ids = set(str(value) for value in inspection["missing_submissions"])
        invalid_ids = {
            str(item["assignment_id"]) for item in inspection["invalid_submissions"]
        }
        previous = matrix_rounds.get(current_round_id, {})
        previous_entries = {
            str(item.get("member_id")): item
            for item in previous.get("participation", [])
            if isinstance(item, dict)
        }
        expected = sorted(str(value) for value in record.get("expected_member_ids", []))
        entries: list[dict[str, Any]] = []
        for member_id in expected:
            assignment_ids: list[str] = []
            for assignment_id in record.get("assignment_ids", []):
                assignment_path = stage_path / "dispatch" / f"{assignment_id}.yaml"
                if assignment_path.exists():
                    assignment = load_data(assignment_path)
                    if str(assignment.get("member_id")) == member_id:
                        assignment_ids.append(str(assignment_id))
            prior = previous_entries.get(member_id, {})
            if any(assignment_id in invalid_ids for assignment_id in assignment_ids):
                submission_status = "invalid"
            elif not assignment_ids or any(
                assignment_id in missing_ids for assignment_id in assignment_ids
            ):
                submission_status = "missing"
            elif set(assignment_ids) <= valid_ids:
                submission_status = "submitted"
            else:
                submission_status = "pending"
            reviewed = member_id in set(record.get("shared_review_member_ids", []))
            entries.append(
                {
                    "member_id": member_id,
                    "assignment_ids": sorted(assignment_ids),
                    "submission_status": submission_status,
                    "shared_review": (
                        "completed"
                        if reviewed
                        else ("pending" if record.get("shared_review_required") else "not-required")
                    ),
                    "shared_review_note": prior.get("shared_review_note"),
                    "shared_review_evidence": record.get("shared_review_evidence", {}).get(
                        member_id, prior.get("shared_review_evidence")
                    ),
                    "gate_confirmation": prior.get("gate_confirmation", "pending"),
                }
            )
        expected_count = len(expected)
        submitted_count = sum(
            1 for item in entries if item["submission_status"] == "submitted"
        )
        reviewed_count = sum(1 for item in entries if item["shared_review"] == "completed")
        matrix_rounds[current_round_id] = {
            "round_id": current_round_id,
            "status": record.get("status"),
            "participation_mode": record.get("participation_mode", "role-assigned"),
            "review_of_round": record.get("review_of_round"),
            "expected_members": expected,
            "excluded_members": [],
            "participation": entries,
            "submission_coverage": (
                round(submitted_count * 100 / expected_count) if expected_count else 0
            ),
            "shared_review_coverage": (
                round(reviewed_count * 100 / expected_count)
                if expected_count and record.get("shared_review_required")
                else 100
            ),
            "missing_members": sorted(
                item["member_id"]
                for item in entries
                if item["submission_status"] != "submitted"
            ),
            "participation_issues": inspection.get("participation_issues", []),
            "missing_exceptions": list(record.get("missing_exceptions", [])),
        }
    incomplete = sorted(
        current_round_id
        for current_round_id, record in matrix_rounds.items()
        if record.get("status") != "superseded"
        and (record.get("submission_coverage") != 100
        or record.get("shared_review_coverage") != 100
        )
    )
    matrix["stage_summary"] = {
        "round_count": len(matrix_rounds),
        "incomplete_rounds": incomplete,
        "has_recorded_exceptions": any(
            bool(record.get("missing_exceptions")) for record in matrix_rounds.values()
        ),
    }
    matrix.setdefault(
        "gate_confirmation",
        {
            "policy": project.get("gate_confirmation_policy", "accountable-members"),
            "approved_member_ids": [],
        },
    )
    matrix["gate_confirmation"]["policy"] = project.get(
        "gate_confirmation_policy", "accountable-members"
    )
    matrix["updated_at"] = now_iso()
    dump_data(path, matrix)
    return path


def cmd_record_shared_review(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project = load_data(root / "project-state.yaml")
    require_current_schema(project)
    if project.get("collaboration_model") != "collective-participation":
        raise SopError("record-shared-review is only used in collective-participation mode")
    member_id = safe_id(args.member_id)
    if member_id not in active_member_ids(root, project):
        raise SopError(f"Member is not active: {member_id}")
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    round_id = safe_id(args.round)
    record = state.get("rounds", {}).get(round_id)
    if not isinstance(record, dict) or record.get("status") not in {"closed", "reviewed"}:
        raise SopError(f"Round {round_id} must be closed before shared review is recorded")
    if member_id not in set(record.get("expected_member_ids", [])):
        raise SopError(f"Member {member_id} is not expected in round {round_id}")
    artifact = Path(args.artifact_ref)
    if not artifact.is_absolute():
        artifact = Path(args.project_root).resolve() / artifact
    artifact = artifact.resolve()
    member_submission_root = (stage_path / "submissions" / member_id).resolve()
    if not artifact.is_file() or not artifact.is_relative_to(member_submission_root):
        raise SopError(
            "--artifact-ref must be an existing file in the member-owned submissions directory"
        )
    record["shared_review_required"] = True
    record["shared_review_member_ids"] = sorted(
        set(record.get("shared_review_member_ids", [])) | {member_id}
    )
    evidence = dict(record.get("shared_review_evidence", {}))
    evidence[member_id] = str(artifact.relative_to(sop_root(args.project_root)))
    record["shared_review_evidence"] = evidence
    state["updated_at"] = now_iso()
    dump_data(state_path, state)
    path = refresh_participation_matrix(args.project_root, args.stage, round_id)
    matrix = load_data(path)
    for item in matrix.get("rounds", {}).get(round_id, {}).get("participation", []):
        if item.get("member_id") == member_id:
            item["shared_review_note"] = args.note
            item["shared_review_evidence"] = evidence[member_id]
    matrix["updated_at"] = now_iso()
    dump_data(path, matrix)
    print(path)


def cmd_validate_stage(args: argparse.Namespace) -> None:
    result = inspect_authoritative_stage(
        args.project_root, args.stage, remote=args.remote
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if (
        result["missing_submissions"]
        or result["invalid_submissions"]
        or result["participation_issues"]
    ):
        raise SopError("Stage has missing or invalid submissions")


def cmd_validate_round(args: argparse.Namespace) -> None:
    round_id = safe_id(args.round)
    result = inspect_authoritative_stage(
        args.project_root, args.stage, round_id, remote=args.remote
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if (
        result["missing_submissions"]
        or result["invalid_submissions"]
        or result["participation_issues"]
    ):
        raise SopError("Round has missing or invalid submissions")


def recorded_missing_exception(
    args: argparse.Namespace, result: dict[str, Any]
) -> dict[str, Any] | None:
    has_issues = bool(
        result["missing_submissions"]
        or result["invalid_submissions"]
        or result.get("participation_issues")
    )
    if not has_issues:
        return None
    if not args.allow_missing:
        raise SopError("Cannot continue with missing, invalid, or incomplete participation")
    reason = str(getattr(args, "missing_reason", "") or "").strip()
    impact = str(getattr(args, "missing_impact", "") or "").strip()
    if not reason or not impact:
        raise SopError(
            "--allow-missing requires both --missing-reason and --missing-impact"
        )
    missing_member_ids = sorted(
        {
            str(item["member_id"])
            for item in result.get("participation_issues", [])
            if isinstance(item, dict) and item.get("member_id")
        }
    )
    return {
        "reason": reason,
        "impact": impact,
        "missing_member_ids": missing_member_ids,
        "missing_assignment_ids": list(result["missing_submissions"]),
        "invalid_submissions": list(result["invalid_submissions"]),
        "participation_issues": list(result.get("participation_issues", [])),
        "recorded_at": now_iso(),
    }


def cmd_supersede_round(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    round_id = safe_id(args.round)
    replacement_round_id = safe_id(args.replacement_round)
    record = state.get("rounds", {}).get(round_id)
    if not isinstance(record, dict):
        raise SopError(f"Unknown round: {round_id}")
    if record.get("status") == "superseded":
        raise SopError(f"Round {round_id} is already superseded")
    if record.get("status") not in {"collecting", "closed"}:
        raise SopError(
            f"Only collecting or closed rounds can be superseded: {round_id}"
        )
    if replacement_round_id == round_id:
        raise SopError("Replacement round must use a new round ID")
    if replacement_round_id in state.get("rounds", {}):
        raise SopError(f"Replacement round already exists: {replacement_round_id}")
    reason = str(args.reason).strip()
    if not reason:
        raise SopError("--reason is required")
    recorded_at = now_iso()
    record["status"] = "superseded"
    record["superseded_at"] = recorded_at
    record["superseded_reason"] = reason
    record["replacement_round_id"] = replacement_round_id
    record["finding_id"] = str(args.finding_id or "").strip() or None
    state["status"] = "returned-to-collection"
    state["updated_at"] = recorded_at
    dump_data(state_path, state)
    decision_path = root / "decisions" / "decision-log.yaml"
    decision_log = load_data(decision_path)
    decisions = decision_log.setdefault("decisions", [])
    decisions.append(
        {
            "decision_id": safe_id(f"DEC-SUPERSEDE-{args.stage}-{round_id}"),
            "decision_type": "round-superseded",
            "stage_id": args.stage,
            "round_id": round_id,
            "replacement_round_id": replacement_round_id,
            "finding_id": record["finding_id"],
            "reason": reason,
            "recorded_at": recorded_at,
        }
    )
    dump_data(decision_path, decision_log)
    refresh_participation_matrix(args.project_root, args.stage)
    refresh_project_state(args.project_root, source="supersede-round")
    print(
        json.dumps(
            {
                "superseded_round": round_id,
                "replacement_round": replacement_round_id,
                "decision_log": str(decision_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_close_round(args: argparse.Namespace) -> None:
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    round_id = safe_id(args.round)
    record = state.get("rounds", {}).get(round_id)
    if not isinstance(record, dict):
        raise SopError(f"Unknown round: {round_id}")
    if record.get("status") != "collecting":
        raise SopError(f"Round {round_id} must be collecting")
    kinds = set(record.get("kinds", []))
    if (
        args.stage == "02-solution-validation"
        and record.get("participation_mode") != "individual-exception"
        and kinds & {"function-design", "system-inventory"}
        and not {"function-design", "system-inventory"}.issubset(kinds)
    ):
        raise SopError(
            "Stage B solution round must contain both function-design and system-inventory"
        )
    result = inspect_authoritative_stage(
        args.project_root, args.stage, round_id, remote=args.remote
    )
    missing_exception = recorded_missing_exception(args, result)
    has_issues = missing_exception is not None
    round_root = stage_path / "aggregation" / "rounds" / round_id
    index = {
        "stage_id": args.stage,
        "round_id": round_id,
        "closed_at": now_iso(),
        "valid_submissions": result["valid_submissions"],
        "missing_submissions": result["missing_submissions"],
        "invalid_submissions": result["invalid_submissions"],
        "continued_with_missing": bool(has_issues and args.allow_missing),
        "collaboration_model": record.get("collaboration_model", "role-based"),
        "participation_mode": record.get("participation_mode", "role-assigned"),
        "missing_exception": missing_exception,
    }
    dump_data(round_root / "submission-index.yaml", index)
    if args.stage == "02-solution-validation" and {
        "function-design", "system-inventory"
    }.issubset(kinds):
        record["shared_review_required"] = True
        summary = round_root / "summary.md"
        if not summary.exists():
            summary.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(asset("round-review-summary.md"), summary)
    if (
        record.get("collaboration_model") == "collective-participation"
        and "shared-review" not in kinds
    ):
        record["shared_review_required"] = True
    if "shared-review" in kinds:
        reviewed_round_id = str(record.get("review_of_round", "")).strip()
        reviewed_record = state.get("rounds", {}).get(reviewed_round_id)
        if not reviewed_round_id or not isinstance(reviewed_record, dict):
            raise SopError("A shared-review round must reference an existing target round")
        valid_reviewers = {
            str(item["member_id"]) for item in result.get("valid_submissions", [])
        }
        reviewed_record["shared_review_required"] = True
        reviewed_record["shared_review_member_ids"] = sorted(valid_reviewers)
        reviewed_record["shared_review_evidence"] = {
            str(item["member_id"]): str(item["submission"])
            for item in result.get("valid_submissions", [])
        }
        if missing_exception:
            reviewed_record.setdefault("missing_exceptions", []).append(missing_exception)
    record["status"] = "closed"
    record["closed_at"] = now_iso()
    if missing_exception:
        record.setdefault("missing_exceptions", []).append(missing_exception)
    state["updated_at"] = now_iso()
    dump_data(state_path, state)
    refresh_participation_matrix(args.project_root, args.stage, round_id)
    print(round_root / "submission-index.yaml")


def cmd_complete_round_review(args: argparse.Namespace) -> None:
    if args.stage != "02-solution-validation":
        raise SopError("Round review is only used for stage 02-solution-validation")
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    round_id = safe_id(args.round)
    record = state.get("rounds", {}).get(round_id)
    if not isinstance(record, dict) or record.get("status") != "closed":
        raise SopError(f"Round {round_id} must be closed before review completion")
    if not {"function-design", "system-inventory"}.issubset(set(record.get("kinds", []))):
        raise SopError("Only a combined design/inventory round can complete solution review")
    summary = stage_path / "aggregation" / "rounds" / round_id / "summary.md"
    if not summary.is_file() or "[[FILL]]" in summary.read_text(encoding="utf-8"):
        raise SopError("Complete the public round review summary before continuing")
    project = load_data(sop_root(args.project_root) / "project-state.yaml")
    if project.get("collaboration_model") == "collective-participation":
        review_round_ids = sorted(
            candidate_id
            for candidate_id, candidate in state.get("rounds", {}).items()
            if isinstance(candidate, dict)
            and candidate.get("review_of_round") == round_id
            and "shared-review" in set(candidate.get("kinds", []))
            and candidate.get("status") in {"closed", "reviewed"}
        )
        if not review_round_ids:
            raise SopError(
                "Collective solution review requires a closed shared-review round "
                f"with review_of_round={round_id}"
            )
        reviewed_members: set[str] = set(
            str(value) for value in record.get("shared_review_member_ids", [])
        )
        review_evidence = dict(record.get("shared_review_evidence", {}))
        combined_missing: list[str] = []
        combined_invalid: list[dict[str, str]] = []
        combined_issues: list[dict[str, Any]] = []
        for review_round_id in review_round_ids:
            inspection = inspect_authoritative_stage(
                args.project_root,
                args.stage,
                review_round_id,
                remote=args.remote,
            )
            reviewed_members.update(
                str(item["member_id"]) for item in inspection["valid_submissions"]
            )
            for item in inspection["valid_submissions"]:
                review_evidence[str(item["member_id"])] = str(item["submission"])
            combined_missing.extend(inspection["missing_submissions"])
            combined_invalid.extend(inspection["invalid_submissions"])
            combined_issues.extend(inspection["participation_issues"])
        expected_members = set(str(value) for value in record.get("expected_member_ids", []))
        missing_reviewers = sorted(expected_members - reviewed_members)
        for member_id in missing_reviewers:
            combined_issues.append(
                {
                    "round_id": round_id,
                    "member_id": member_id,
                    "reason": "shared-review-evidence-missing",
                }
            )
        review_exception = recorded_missing_exception(
            args,
            {
                "missing_submissions": combined_missing,
                "invalid_submissions": combined_invalid,
                "participation_issues": combined_issues,
            },
        )
        record["shared_review_required"] = True
        record["shared_review_member_ids"] = sorted(expected_members & reviewed_members)
        record["shared_review_evidence"] = {
            member_id: review_evidence[member_id]
            for member_id in sorted(expected_members & reviewed_members)
            if member_id in review_evidence
        }
        if review_exception:
            record.setdefault("missing_exceptions", []).append(review_exception)
    record["status"] = "reviewed"
    record["reviewed_at"] = now_iso()
    state["updated_at"] = now_iso()
    dump_data(state_path, state)
    refresh_participation_matrix(args.project_root, args.stage, round_id)
    print(summary)


def cmd_close_stage(args: argparse.Namespace) -> None:
    project = load_data(sop_root(args.project_root) / "project-state.yaml")
    require_current_schema(project)
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    if state.get("status") != "collecting":
        raise SopError(f"Stage must be collecting, not {state.get('status')}")
    if args.stage == "02-solution-validation":
        rounds = state.get("rounds", {})
        if not reviewed_solution_round(state):
            raise SopError("Stage B requires a reviewed design/inventory round")
        validation_rounds = [
            record for record in rounds.values()
            if "prototype-validation" in set(record.get("kinds", []))
        ]
        if not validation_rounds or any(
            record.get("status") not in {"closed", "reviewed"}
            for record in validation_rounds
        ):
            raise SopError("Stage B requires at least one closed prototype-validation round")
        unclosed = [
            round_id for round_id, record in rounds.items()
            if record.get("status") == "collecting"
        ]
        if unclosed:
            raise SopError(f"Close all Stage B rounds first: {', '.join(unclosed)}")
    collective_review_issues: list[dict[str, Any]] = []
    if project.get("collaboration_model") == "collective-participation":
        unclosed = sorted(
            round_id
            for round_id, record in state.get("rounds", {}).items()
            if isinstance(record, dict) and record.get("status") == "collecting"
        )
        if unclosed:
            raise SopError(f"Close all collective rounds first: {', '.join(unclosed)}")
        rounds = state.get("rounds", {})
        for round_id, record in rounds.items():
            if not isinstance(record, dict):
                continue
            kinds = set(str(value) for value in record.get("kinds", []))
            if "shared-review" in kinds:
                continue
            review_rounds = [
                str(review_round_id)
                for review_round_id, review_record in rounds.items()
                if isinstance(review_record, dict)
                and review_record.get("review_of_round") == round_id
                and "shared-review" in set(review_record.get("kinds", []))
                and review_record.get("status") in {"closed", "reviewed"}
            ]
            if not review_rounds:
                collective_review_issues.append(
                    {
                        "round_id": str(round_id),
                        "reason": "closed-shared-review-round-missing",
                    }
                )
    result = inspect_authoritative_stage(
        args.project_root, args.stage, remote=args.remote
    )
    result.setdefault("participation_issues", []).extend(collective_review_issues)
    missing_exception = recorded_missing_exception(args, result)
    has_issues = missing_exception is not None
    build_source_index(args.project_root, args.stage, remote=args.remote)
    index = {
        "stage_id": args.stage,
        "closed_at": now_iso(),
        "valid_submissions": result["valid_submissions"],
        "missing_submissions": result["missing_submissions"],
        "invalid_submissions": result["invalid_submissions"],
        "continued_with_missing": bool(has_issues and args.allow_missing),
        "collaboration_model": project.get("collaboration_model", "role-based"),
        "gate_confirmation_policy": project.get(
            "gate_confirmation_policy", "accountable-members"
        ),
        "missing_exception": missing_exception,
    }
    dump_data(stage_path / "aggregation" / "submission-index.yaml", index)
    state["status"] = "submission-closed"
    for record in state.get("rounds", {}).values():
        if record.get("status") == "collecting":
            record["status"] = "closed"
            record["closed_at"] = now_iso()
    state["missing_submissions"] = result["missing_submissions"]
    state["invalid_submissions"] = result["invalid_submissions"]
    if missing_exception:
        state.setdefault("missing_exceptions", []).append(missing_exception)
    state["updated_at"] = now_iso()
    dump_data(state_path, state)
    refresh_participation_matrix(args.project_root, args.stage)
    print(stage_path / "aggregation" / "submission-index.yaml")


def cmd_transition(args: argparse.Namespace) -> None:
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    current = str(state.get("status"))
    target = args.to
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise SopError(f"Illegal stage transition: {current} -> {target}")
    if target in {"gate-pending", "merge-pending", "baselined"}:
        raise SopError(
            f"Use prepare-gate/approve-gate/merge-approved-gate for transition to {target}"
        )
    state["status"] = target
    state["updated_at"] = now_iso()
    dump_data(state_path, state)
    print(f"{current} -> {target}")


def asset(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "project-template" / name


def dashboard_asset(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "github-dashboard" / name


def trusted_member_cli_asset(name: str = "member_cli.py") -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "remote-validator"
        / name
    )


def provenance_root(stage_path: Path) -> Path:
    return stage_path / "aggregation" / "provenance"


def build_source_index(
    project_root: str | Path, stage: str, remote: str = "origin"
) -> Path:
    root = sop_root(project_root)
    project = load_data(root / "project-state.yaml")
    require_current_schema(project)
    git_root = find_git_root(Path(project_root))
    if git_root is None:
        raise SopError("Document provenance requires a Git repository")
    stage_path = stage_root(project_root, stage)
    state = load_data(stage_path / "stage-state.yaml")
    submissions: list[dict[str, Any]] = []
    source_blocks: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    seen_blocks: set[str] = set()
    for assignment_id in active_assignment_ids(state):
        assignment_path = stage_path / "dispatch" / f"{assignment_id}.yaml"
        if not assignment_path.is_file():
            unavailable.append(
                {"assignment_id": assignment_id, "reason": "assignment-file-missing"}
            )
            continue
        assignment = load_data(assignment_path)
        branch = str(assignment.get("git_branch", "")).strip()
        observed = resolve_observation_ref(git_root, branch, remote)
        if observed is None:
            unavailable.append(
                {
                    "assignment_id": assignment_id,
                    "member_id": assignment.get("member_id"),
                    "git_branch": branch,
                    "reason": "member-branch-not-found",
                }
            )
            continue
        observed_ref, commit = observed
        submission = find_submission(stage_path, assignment)
        manifest = read_git_mapping(
            git_root, observed_ref, submission / "submission-manifest.yaml"
        )
        index = read_git_mapping(
            git_root, observed_ref, submission / "content-block-index.yaml"
        )
        main_text = read_git_text(
            git_root, observed_ref, submission / "main-output.md"
        )
        if manifest is None or index is None or main_text is None:
            unavailable.append(
                {
                    "assignment_id": assignment_id,
                    "member_id": assignment.get("member_id"),
                    "git_branch": branch,
                    "observed_ref": observed_ref,
                    "observed_head": commit,
                    "reason": "submitted-content-or-index-not-found-at-ref",
                }
            )
            continue
        if manifest.get("__parse_error__") or index.get("__parse_error__"):
            raise SopError(
                f"Cannot parse submission provenance for assignment {assignment_id}"
            )
        mismatches = manifest_mismatch_fields(manifest, assignment, project)
        if mismatches or manifest.get("status") != "submitted":
            unavailable.append(
                {
                    "assignment_id": assignment_id,
                    "member_id": assignment.get("member_id"),
                    "git_branch": branch,
                    "observed_ref": observed_ref,
                    "observed_head": commit,
                    "reason": (
                        "manifest-mismatch:"
                        + ",".join(mismatches)
                        if mismatches
                        else "manifest-not-submitted"
                    ),
                }
            )
            continue
        validate_member_content_index(main_text, assignment, manifest, index)
        source_document = str(submission.relative_to(root) / "main-output.md").replace(
            "\\", "/"
        )
        submission_record = {
            "submission_id": manifest.get("submission_id"),
            "assignment_id": assignment_id,
            "member_id": assignment.get("member_id"),
            "round_id": assignment.get("round_id"),
            "assignment_kind": assignment.get("assignment_kind"),
            "source_document": source_document,
            "git_branch": branch,
            "observed_ref": observed_ref,
            "commit": commit,
            "document_hash": index.get("document_hash"),
            "block_count": index.get("block_count"),
        }
        submissions.append(submission_record)
        for block in index.get("blocks", []):
            block_id = str(block.get("source_block_id", ""))
            if block_id in seen_blocks:
                raise SopError(f"Duplicate source block ID across submissions: {block_id}")
            seen_blocks.add(block_id)
            source_blocks.append(
                {
                    "source_block_id": block_id,
                    "member_id": assignment.get("member_id"),
                    "assignment_id": assignment_id,
                    "round_id": assignment.get("round_id"),
                    "assignment_kind": assignment.get("assignment_kind"),
                    "source_document": source_document,
                    "git_branch": branch,
                    "observed_ref": observed_ref,
                    "commit": commit,
                    "ordinal": block.get("ordinal"),
                    "heading_path": block.get("heading_path", []),
                    "content_hash": block.get("content_hash"),
                    "text_excerpt": block.get("text_excerpt"),
                    "evidence_refs": block.get("evidence_refs", []),
                }
            )
    submissions.sort(key=lambda item: str(item["assignment_id"]))
    source_blocks.sort(key=lambda item: str(item["source_block_id"]))
    unavailable.sort(key=lambda item: str(item.get("assignment_id", "")))
    digest_payload = json.dumps(
        {
            "submissions": submissions,
            "source_blocks": source_blocks,
            "unavailable_submissions": unavailable,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    data = {
        "schema_version": "1.0",
        "stage_id": stage,
        "generated_at": now_iso(),
        "remote": remote,
        "source_index_hash": content_hash(digest_payload),
        "submission_count": len(submissions),
        "block_count": len(source_blocks),
        "submissions": submissions,
        "unavailable_submissions": unavailable,
        "source_blocks": source_blocks,
    }
    path = provenance_root(stage_path) / "source-block-index.yaml"
    dump_data(path, data)
    return path


def markdown_target_units(path: Path, relative: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    units: list[dict[str, Any]] = []
    raw_blocks = markdown_content_blocks(text)
    expanded: list[tuple[str, list[str]]] = []
    for raw in raw_blocks:
        content = str(raw["content"])
        lines = content.split("\n")
        if len(lines) >= 2 and all(line.lstrip().startswith("|") for line in lines):
            for index, line in enumerate(lines):
                if index == 0 or re.fullmatch(r"\|?[ :|-]+\|?", line):
                    continue
                expanded.append((line, list(raw.get("heading_path", []))))
        else:
            expanded.append((content, list(raw.get("heading_path", []))))
    for content, headings in expanded:
        refs = sorted(set(PROVENANCE_MARKER_PATTERN.findall(content)))
        exempt_match = re.search(
            r"<!--\s*provenance-exempt:\s*(.+?)\s*-->", content, re.IGNORECASE
        )
        clean = PROVENANCE_MARKER_PATTERN.sub("", content)
        clean = re.sub(r"<!--.*?-->", "", clean, flags=re.DOTALL)
        normalized = normalize_content(clean)
        if len(normalized) < 8:
            continue
        identity_seed = f"{relative}|{'|'.join(refs)}|{normalized}"
        target_id = "TB-" + hashlib.sha256(
            identity_seed.encode("utf-8")
        ).hexdigest()[:16]
        units.append(
            {
                "target_artifact": relative,
                "target_block_id": target_id,
                "target_content_hash": content_hash(normalized),
                "provenance_refs": refs,
                "heading_path": headings,
                "excerpt": normalized.replace("\n", " ")[:200],
                "exempt_reason": exempt_match.group(1).strip() if exempt_match else None,
                "is_p0": bool(re.search(r"\bP0\b", normalized, re.IGNORECASE)),
            }
        )
    return units


def mapping_target_units(path: Path, relative: str) -> list[dict[str, Any]]:
    data = load_data(path)
    units: list[dict[str, Any]] = []

    def walk(value: Any, pointer: str) -> None:
        if isinstance(value, dict):
            refs_raw = value.get("provenance_refs", [])
            refs = (
                sorted(set(str(item) for item in refs_raw))
                if isinstance(refs_raw, list)
                else []
            )
            identifier_keys = sorted(
                key
                for key in value
                if key == "id"
                or (key.endswith("_id") and key not in {"artifact_id", "source_id"})
            )
            is_record = bool(refs or identifier_keys)
            if is_record:
                clean = {
                    key: item
                    for key, item in value.items()
                    if key not in {"provenance_refs", "provenance_exempt_reason"}
                }
                serialized = json.dumps(
                    clean,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                if len(normalize_content(serialized)) >= 8:
                    identity = (
                        str(value.get(identifier_keys[0]))
                        if identifier_keys
                        else pointer
                    )
                    units.append(
                        {
                            "target_artifact": relative,
                            "target_block_id": str(identity),
                            "target_content_hash": content_hash(serialized),
                            "provenance_refs": refs,
                            "heading_path": [],
                            "excerpt": serialized[:200],
                            "exempt_reason": value.get("provenance_exempt_reason"),
                            "is_p0": str(value.get("priority", "")).upper() == "P0",
                        }
                    )
            for key, item in value.items():
                if key not in {"provenance_refs", "provenance_exempt_reason"}:
                    walk(item, f"{pointer}/{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{pointer}/{index}")

    walk(data, "")
    return units


def target_units(path: Path, relative: str) -> list[dict[str, Any]]:
    if path.suffix.lower() in {".yaml", ".yml", ".json"}:
        return mapping_target_units(path, relative)
    return markdown_target_units(path, relative)


def stage_artifact_paths(stage_path: Path) -> list[tuple[str, Path]]:
    manifest_path = stage_path / "aggregation" / "artifact-manifest.yaml"
    manifest = load_data(manifest_path)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise SopError("artifact-manifest artifacts must be a list")
    result: list[tuple[str, Path]] = []
    for item in artifacts:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        relative = str(item["path"]).replace("\\", "/")
        candidate = (stage_path / relative).resolve()
        if not candidate.is_relative_to(stage_path.resolve()):
            raise SopError(f"Artifact path escapes the stage directory: {relative}")
        if not candidate.is_file():
            raise SopError(f"Declared artifact does not exist: {relative}")
        result.append((relative, candidate))
    return result


def load_provenance_ledger(stage_path: Path) -> tuple[Path, dict[str, Any]]:
    path = provenance_root(stage_path) / "provenance-ledger.yaml"
    if not path.is_file():
        raise SopError(f"Provenance ledger does not exist: {path}")
    ledger = load_data(path)
    if not isinstance(ledger.get("targets", []), list):
        raise SopError("provenance-ledger targets must be a list")
    return path, ledger


def cmd_build_source_index(args: argparse.Namespace) -> None:
    path = build_source_index(args.project_root, args.stage, args.remote)
    print(path)


def cmd_trace_content(args: argparse.Namespace) -> None:
    stage_path = stage_root(args.project_root, args.stage)
    provenance_id = args.provenance_id.upper()
    if not PROVENANCE_ID_PATTERN.fullmatch(provenance_id):
        raise SopError("--provenance-id must use P-001 format")
    derivation = args.derivation_type
    source_index_path = build_source_index(
        args.project_root, args.stage, args.remote
    )
    source_index = load_data(source_index_path)
    source_lookup = {
        str(item["source_block_id"]): item
        for item in source_index.get("source_blocks", [])
    }
    requested_sources = list(dict.fromkeys(args.source_block or []))
    member_derived = {
        "verbatim",
        "paraphrased",
        "synthesis",
        "derived",
        "conflict-retained",
    }
    if derivation in member_derived and not requested_sources:
        raise SopError(f"{derivation} provenance requires --source-block")
    missing = sorted(set(requested_sources) - set(source_lookup))
    if missing:
        raise SopError(f"Unknown source blocks: {', '.join(missing)}")
    if derivation in {"human-decision", "coordinator-added"} and not args.decision_ref:
        raise SopError(f"{derivation} provenance requires --decision-ref")
    project = load_data(sop_root(args.project_root) / "project-state.yaml")
    if derivation == "legacy-unattributed":
        policy = project.get("provenance_tracking", {}).get(
            "legacy_content_policy", "disallow-legacy-unattributed"
        )
        if policy != "allow-reviewed-legacy-unattributed":
            raise SopError("legacy-unattributed is not allowed for a new v1.5 project")
        if not args.legacy_reason:
            raise SopError("legacy-unattributed requires --legacy-reason")
    relative = str(args.target).replace("\\", "/")
    target_path = (stage_path / relative).resolve()
    if not target_path.is_relative_to(stage_path.resolve()) or not target_path.is_file():
        raise SopError("--target must be an existing stage-relative artifact")
    matches = [
        unit
        for unit in target_units(target_path, relative)
        if provenance_id in unit.get("provenance_refs", [])
    ]
    if len(matches) != 1:
        raise SopError(
            f"Target artifact must contain {provenance_id} in exactly one content unit"
        )
    if args.review_status in {"reviewed", "approved"} and not args.reviewer:
        raise SopError("reviewed/approved provenance requires --reviewer")
    target = matches[0]
    if derivation == "synthesis" and len(requested_sources) < 2:
        raise SopError("synthesis provenance requires at least two source blocks")
    if derivation == "verbatim":
        if len(requested_sources) != 1:
            raise SopError("verbatim provenance requires exactly one source block")
        if target["target_content_hash"] != source_lookup[requested_sources[0]].get(
            "content_hash"
        ):
            raise SopError("verbatim target content hash does not match its source block")
    sources = []
    for block_id in requested_sources:
        source = source_lookup[block_id]
        sources.append(
            {
                key: source.get(key)
                for key in (
                    "member_id",
                    "assignment_id",
                    "source_document",
                    "source_block_id",
                    "git_branch",
                    "commit",
                    "content_hash",
                    "evidence_refs",
                )
            }
        )
    record = {
        "provenance_id": provenance_id,
        "target_artifact": target["target_artifact"],
        "target_block_id": target["target_block_id"],
        "target_content_hash": target["target_content_hash"],
        "derivation_type": derivation,
        "sources": sources,
        "decision_ref": args.decision_ref,
        "legacy_reason": args.legacy_reason,
        "note": args.note,
        "review_status": args.review_status,
        "reviewed_by": args.reviewer,
        "reviewed_at": (
            now_iso() if args.review_status in {"reviewed", "approved"} else None
        ),
        "updated_at": now_iso(),
    }
    ledger_path, ledger = load_provenance_ledger(stage_path)
    targets = list(ledger.get("targets", []))
    existing = [
        index
        for index, item in enumerate(targets)
        if isinstance(item, dict) and item.get("provenance_id") == provenance_id
    ]
    if existing and not args.replace:
        raise SopError(
            f"{provenance_id} already exists; use --replace after deliberate review"
        )
    if existing:
        targets[existing[0]] = record
    else:
        targets.append(record)
    ledger["targets"] = sorted(
        targets, key=lambda item: str(item.get("provenance_id", ""))
    )
    ledger["source_index_hash"] = source_index.get("source_index_hash")
    ledger["updated_at"] = now_iso()
    dump_data(ledger_path, ledger)
    print(json.dumps(record, ensure_ascii=False, indent=2))


def write_provenance_report(stage_path: Path, report: dict[str, Any]) -> Path:
    lines = [
        "# 文档内容来源追踪报告",
        "",
        f"- 阶段：`{report['stage_id']}`",
        f"- 生成时间：`{report['generated_at']}`",
        f"- 实质内容单元：{report['substantive_units']}",
        f"- 已追踪内容单元：{report['tracked_units']}",
        f"- 豁免内容单元：{report['exempt_units']}",
        f"- 追踪覆盖率：{report['coverage_percent']}%",
        f"- P0 内容覆盖率：{report['p0_coverage_percent']}%",
        f"- 阻塞问题：{len(report['issues'])}",
        "",
        "| 标识 | 汇合产物 | 内容块 | 形成方式 | 成员来源 | 审核状态 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in report.get("targets", []):
        members = ", ".join(item.get("member_ids", [])) or "—"
        lines.append(
            f"| {item.get('provenance_id')} | {item.get('target_artifact')} | "
            f"{item.get('target_block_id')} | {item.get('derivation_type')} | "
            f"{members} | {item.get('review_status')} |"
        )
    lines.extend(["", "## 阻塞问题", ""])
    if report["issues"]:
        lines.extend(f"- {issue}" for issue in report["issues"])
    else:
        lines.append("- 无")
    lines.extend(["", "## 非阻塞提醒", ""])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- 无")
    path = provenance_root(stage_path) / "provenance-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def validate_provenance(
    project_root: str | Path, stage: str, remote: str = "origin"
) -> dict[str, Any]:
    stage_path = stage_root(project_root, stage)
    source_index_path = build_source_index(project_root, stage, remote)
    source_index = load_data(source_index_path)
    source_lookup = {
        str(item["source_block_id"]): item
        for item in source_index.get("source_blocks", [])
    }
    ledger_path, ledger = load_provenance_ledger(stage_path)
    issues: list[str] = []
    warnings: list[str] = []
    all_units: list[dict[str, Any]] = []
    for relative, path in stage_artifact_paths(stage_path):
        all_units.extend(target_units(path, relative))
    substantive = list(all_units)
    exempt: list[dict[str, Any]] = []
    marker_units: dict[str, list[dict[str, Any]]] = {}
    for unit in substantive:
        if unit.get("exempt_reason"):
            issues.append(
                "substantive-provenance-exemption-not-allowed:"
                f"{unit['target_artifact']}#{unit['target_block_id']}"
            )
        refs = unit.get("provenance_refs", [])
        if not refs:
            issues.append(
                "untracked-content:"
                f"{unit['target_artifact']}#{unit['target_block_id']}"
            )
        for ref in refs:
            if not PROVENANCE_ID_PATTERN.fullmatch(str(ref)):
                issues.append(f"invalid-provenance-marker:{ref}")
            marker_units.setdefault(str(ref), []).append(unit)
    for ref, units in marker_units.items():
        if len(units) != 1:
            issues.append(f"duplicate-provenance-marker:{ref}")
    ledger_targets = ledger.get("targets", [])
    target_lookup: dict[str, dict[str, Any]] = {}
    for item in ledger_targets:
        if not isinstance(item, dict):
            issues.append("invalid-ledger-target:not-a-mapping")
            continue
        provenance_id = str(item.get("provenance_id", ""))
        if not PROVENANCE_ID_PATTERN.fullmatch(provenance_id):
            issues.append(f"invalid-ledger-provenance-id:{provenance_id}")
        if provenance_id in target_lookup:
            issues.append(f"duplicate-ledger-provenance-id:{provenance_id}")
            continue
        target_lookup[provenance_id] = item
    for ref in sorted(marker_units):
        if ref not in target_lookup:
            issues.append(f"marker-without-ledger-record:{ref}")
    report_targets: list[dict[str, Any]] = []
    project = load_data(sop_root(project_root) / "project-state.yaml")
    legacy_policy = project.get("provenance_tracking", {}).get(
        "legacy_content_policy", "disallow-legacy-unattributed"
    )
    member_derived = {
        "verbatim",
        "paraphrased",
        "synthesis",
        "derived",
        "conflict-retained",
    }
    source_fields = (
        "member_id",
        "assignment_id",
        "source_document",
        "source_block_id",
        "git_branch",
        "commit",
        "content_hash",
        "evidence_refs",
    )
    # The stage ledger intentionally preserves historical aggregation targets.
    # Gate validation applies to the artifacts currently listed by the manifest,
    # so validate only ledger records referenced by those current target units.
    for provenance_id in sorted(marker_units):
        item = target_lookup.get(provenance_id)
        if item is None:
            continue
        units = marker_units.get(provenance_id, [])
        if len(units) != 1:
            issues.append(f"ledger-record-without-unique-target:{provenance_id}")
            continue
        unit = units[0]
        for field in ("target_artifact", "target_block_id", "target_content_hash"):
            if item.get(field) != unit.get(field):
                issues.append(f"target-{field}-mismatch:{provenance_id}")
        derivation = str(item.get("derivation_type", ""))
        if derivation not in DERIVATION_TYPES:
            issues.append(f"invalid-derivation-type:{provenance_id}")
        sources = item.get("sources", [])
        if not isinstance(sources, list):
            issues.append(f"invalid-sources-list:{provenance_id}")
            sources = []
        if derivation in member_derived and not sources:
            issues.append(f"member-source-required:{provenance_id}")
        if derivation == "synthesis" and len(sources) < 2:
            issues.append(f"synthesis-requires-multiple-sources:{provenance_id}")
        if derivation in {"human-decision", "coordinator-added"} and not item.get(
            "decision_ref"
        ):
            issues.append(f"decision-ref-required:{provenance_id}")
        if derivation == "legacy-unattributed":
            if legacy_policy != "allow-reviewed-legacy-unattributed" or not item.get(
                "legacy_reason"
            ):
                issues.append(f"legacy-attribution-not-authorized:{provenance_id}")
            else:
                warnings.append(f"legacy-unattributed:{provenance_id}")
        member_ids: set[str] = set()
        for source in sources:
            if not isinstance(source, dict):
                issues.append(f"invalid-source-record:{provenance_id}")
                continue
            block_id = str(source.get("source_block_id", ""))
            canonical = source_lookup.get(block_id)
            if canonical is None:
                issues.append(f"source-block-not-found:{provenance_id}:{block_id}")
                continue
            mismatched = [
                field
                for field in source_fields
                if source.get(field) != canonical.get(field)
            ]
            if mismatched:
                issues.append(
                    f"source-metadata-mismatch:{provenance_id}:{block_id}:"
                    + ",".join(mismatched)
                )
            member_ids.add(str(canonical.get("member_id")))
        if derivation == "verbatim":
            if len(sources) != 1:
                issues.append(f"verbatim-requires-one-source:{provenance_id}")
            elif item.get("target_content_hash") != sources[0].get("content_hash"):
                issues.append(f"verbatim-content-hash-mismatch:{provenance_id}")
        review_status = str(item.get("review_status", "draft"))
        if review_status not in {"reviewed", "approved"} or not item.get(
            "reviewed_by"
        ):
            issues.append(f"provenance-not-reviewed:{provenance_id}")
        report_targets.append(
            {
                "provenance_id": provenance_id,
                "target_artifact": item.get("target_artifact"),
                "target_block_id": item.get("target_block_id"),
                "derivation_type": derivation,
                "member_ids": sorted(member_ids),
                "review_status": review_status,
            }
        )
    if ledger.get("source_index_hash") != source_index.get("source_index_hash"):
        issues.append("ledger-source-index-hash-stale")
    tracked_units = sum(1 for unit in substantive if unit.get("provenance_refs"))
    denominator = len(substantive)
    coverage = 100.0 if denominator == 0 else round(tracked_units * 100 / denominator, 2)
    p0_units = [unit for unit in substantive if unit.get("is_p0")]
    tracked_p0 = sum(1 for unit in p0_units if unit.get("provenance_refs"))
    p0_coverage = (
        100.0 if not p0_units else round(tracked_p0 * 100 / len(p0_units), 2)
    )
    if denominator == 0:
        issues.append("no-substantive-artifact-content")
    if coverage != 100.0:
        issues.append(f"substantive-provenance-coverage:{coverage}%")
    if p0_coverage != 100.0:
        issues.append(f"p0-provenance-coverage:{p0_coverage}%")
    report = {
        "schema_version": "1.0",
        "stage_id": stage,
        "generated_at": now_iso(),
        "source_index_hash": source_index.get("source_index_hash"),
        "ledger": str(ledger_path.relative_to(stage_path)).replace("\\", "/"),
        "substantive_units": denominator,
        "tracked_units": tracked_units,
        "exempt_units": len(exempt),
        "coverage_percent": coverage,
        "p0_units": len(p0_units),
        "tracked_p0_units": tracked_p0,
        "p0_coverage_percent": p0_coverage,
        "targets": report_targets,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
        "valid": not issues,
    }
    report_path = write_provenance_report(stage_path, report)
    report["report_path"] = str(report_path)
    manifest_path = stage_path / "aggregation" / "artifact-manifest.yaml"
    manifest = load_data(manifest_path)
    manifest["provenance"] = {
        "source_index": "aggregation/provenance/source-block-index.yaml",
        "ledger": "aggregation/provenance/provenance-ledger.yaml",
        "report": "aggregation/provenance/provenance-report.md",
        "source_index_hash": report["source_index_hash"],
        "substantive_content_coverage": report["coverage_percent"],
        "p0_content_coverage": report["p0_coverage_percent"],
        "validated_at": report["generated_at"],
        "valid": report["valid"],
    }
    dump_data(manifest_path, manifest)
    project_path = sop_root(project_root) / "project-state.yaml"
    project = load_data(project_path)
    tracking = project.setdefault(
        "provenance_tracking",
        {
            "schema_version": "1.0",
            "mode": "enforced",
            "effective_from_project_schema": PROJECT_SCHEMA_VERSION,
            "migrated_from_schema": None,
            "legacy_content_policy": "disallow-legacy-unattributed",
        },
    )
    stages = tracking.setdefault("stages", {})
    stages[stage] = {
        "source_index_hash": report["source_index_hash"],
        "substantive_content_coverage": report["coverage_percent"],
        "p0_content_coverage": report["p0_coverage_percent"],
        "valid": report["valid"],
        "issue_count": len(report["issues"]),
        "report": str(report_path.relative_to(sop_root(project_root))).replace(
            "\\", "/"
        ),
        "validated_at": report["generated_at"],
    }
    project["updated_at"] = now_iso()
    dump_data(project_path, project)
    return report


def cmd_validate_provenance(args: argparse.Namespace) -> None:
    report = validate_provenance(args.project_root, args.stage, args.remote)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        raise SopError("Document provenance validation failed")


def cmd_provenance_report(args: argparse.Namespace) -> None:
    report = validate_provenance(args.project_root, args.stage, args.remote)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def gate_review_path(stage_path: Path) -> Path:
    return stage_path / "gate" / GATE_REVIEW_FILE


def gate_review_required_headings(stage: str) -> tuple[str, ...]:
    if stage not in STAGES:
        raise SopError(f"Unknown stage: {stage}")
    return GATE_REVIEW_COMMON_HEADINGS + GATE_REVIEW_STAGE_HEADINGS[stage]


def gate_review_document_hash(path: Path) -> str:
    return content_hash(path.read_text(encoding="utf-8"))


def parse_gate_review_metadata(text: str) -> dict[str, Any]:
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if not first_line.startswith(GATE_REVIEW_METADATA_PREFIX) or not first_line.endswith("-->"):
        raise SopError("Gate review metadata must be the first line")
    payload = first_line[len(GATE_REVIEW_METADATA_PREFIX) : -3].strip()
    try:
        metadata = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SopError(f"Gate review metadata is not valid JSON: {exc}") from exc
    if not isinstance(metadata, dict):
        raise SopError("Gate review metadata must be a JSON object")
    return metadata


def gate_review_source_state(
    project_root: str | Path, stage: str, remote: str = "origin"
) -> dict[str, Any]:
    root = sop_root(project_root)
    project = load_data(root / "project-state.yaml")
    stage_path = stage_root(project_root, stage)
    git_root = find_git_root(Path(project_root))
    if git_root is None:
        raise SopError("Gate review material requires the shared Git repository")
    source_commit = resolve_git_head(git_root, "HEAD")
    manifest_path = stage_path / "aggregation" / "artifact-manifest.yaml"
    matrix_path = participation_matrix_path(project_root, stage)
    decision_log_path = root / "decisions" / "decision-log.yaml"
    required_paths = [manifest_path, matrix_path, decision_log_path]
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise SopError("Gate review source files are missing: " + ", ".join(missing))
    manifest = load_data(manifest_path)
    artifacts = []
    for item in manifest.get("artifacts", []):
        if not isinstance(item, dict):
            continue
        relative = str(item.get("path", "")).strip()
        candidate = (stage_path / relative).resolve()
        artifacts.append(
            {
                "artifact_type": str(item.get("artifact_type", "")).strip(),
                "path": relative,
                "version": str(item.get("version", "")).strip(),
                "hash": gate_review_document_hash(candidate) if candidate.is_file() else None,
            }
        )
    provenance_paths = [
        stage_path / "aggregation" / "provenance" / "source-block-index.yaml",
        stage_path / "aggregation" / "provenance" / "provenance-ledger.yaml",
        stage_path / "aggregation" / "provenance" / "provenance-report.md",
    ]
    provenance = {
        str(path.relative_to(stage_path)).replace("\\", "/"): gate_review_document_hash(path)
        for path in provenance_paths
        if path.is_file()
    }
    merge_plan = build_gate_merge_plan(project_root, root, project, remote)
    frozen_heads = [
        {
            "member_id": str(item["member_id"]),
            "branch": str(item["branch"]),
            "expected_head": str(item["expected_head"]),
        }
        for item in merge_plan.get("member_branches", [])
    ]
    review_path = gate_review_path(stage_path)
    comparison = {
        "status": "none",
        "path": None,
        "commit": None,
        "hash": None,
    }
    if review_path.is_file():
        metadata = parse_gate_review_metadata(review_path.read_text(encoding="utf-8"))
        metadata_source_commit = str(metadata.get("source_commit", "")).strip()
        if not metadata_source_commit:
            raise SopError("Gate review metadata source_commit is required")
        resolve_git_head(git_root, metadata_source_commit)
        source_commit = metadata_source_commit
        comparison = {
            "status": metadata.get("comparison_status"),
            "path": metadata.get("comparison_path"),
            "commit": metadata.get("comparison_commit"),
            "hash": metadata.get("comparison_hash"),
        }
    return {
        "schema_version": "1.0",
        "stage_id": stage,
        "gate_id": STAGES[stage]["gate"],
        "source_commit": source_commit,
        "manifest_hash": gate_review_document_hash(manifest_path),
        "artifacts": sorted(artifacts, key=lambda item: (item["artifact_type"], item["path"])),
        "provenance": provenance,
        "participation_matrix_hash": gate_review_document_hash(matrix_path),
        "active_member_ids": active_member_ids(root, project),
        "frozen_member_heads": frozen_heads,
        "decision_log_hash": gate_review_document_hash(decision_log_path),
        "comparison": comparison,
    }


def gate_review_source_fingerprint(state: dict[str, Any]) -> str:
    encoded = json.dumps(
        state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _remove_unselected_stage_sections(text: str, selected_gate: str) -> str:
    pattern = re.compile(
        r"<!-- stage-section:(G[123]) -->.*?<!-- /stage-section:\1 -->",
        re.DOTALL,
    )

    def select(match: re.Match[str]) -> str:
        if match.group(1) != selected_gate:
            return ""
        value = match.group(0)
        value = re.sub(r"^<!-- stage-section:G[123] -->\s*", "", value)
        value = re.sub(r"\s*<!-- /stage-section:G[123] -->$", "", value)
        return value

    return pattern.sub(select, text)


def init_gate_review(
    project_root: str | Path,
    stage: str,
    replace: bool = False,
    remote: str = "origin",
) -> Path:
    stage_path = stage_root(project_root, stage)
    destination = gate_review_path(stage_path)
    if destination.exists() and not replace:
        raise SopError(f"Gate review material already exists: {destination}")
    state = gate_review_source_state(project_root, stage, remote)
    text = asset(GATE_REVIEW_FILE).read_text(encoding="utf-8")
    gate_id = str(STAGES[stage]["gate"])
    text = _remove_unselected_stage_sections(text, gate_id)
    stage_names = {
        "01-requirement-contract": "需求合同阶段",
        "02-solution-validation": "方案与验证阶段",
        "03-development-entry": "开发准备阶段",
    }
    replacements = {
        "[[FILL:stage_id]]": stage,
        "[[FILL:gate_id]]": gate_id,
        "[[FILL:stage_name]]": stage_names[stage],
        "[[FILL:source_commit]]": str(state["source_commit"]),
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def _section_body(text: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text
    )
    return match.group(1).strip() if match else None


def _subsection_body(text: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^### {re.escape(heading)}\s*$\n(.*?)(?=^### |^## |\Z)", text
    )
    return match.group(1).strip() if match else None


def _gate_review_source_corpus(root: Path, stage_path: Path, review_path: Path) -> str:
    candidates = [stage_path / "aggregation", stage_path / "submissions", root / "decisions"]
    texts: list[str] = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        files = [candidate] if candidate.is_file() else sorted(candidate.rglob("*"))
        for path in files:
            if path == review_path or not path.is_file():
                continue
            try:
                texts.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
    return "\n".join(texts)


def validate_gate_review(
    project_root: str | Path, stage: str, remote: str = "origin"
) -> dict[str, Any]:
    root = sop_root(project_root)
    stage_path = stage_root(project_root, stage)
    path = gate_review_path(stage_path)
    if not path.is_file():
        raise SopError(f"Gate review material does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    if "[[FILL:" in text:
        raise SopError("Gate review material still contains [[FILL: placeholders")
    metadata = parse_gate_review_metadata(text)
    if metadata.get("stage_id") != stage or metadata.get("gate_id") != STAGES[stage]["gate"]:
        raise SopError("Gate review metadata stage_id/gate_id does not match")
    for heading in gate_review_required_headings(stage):
        body = _section_body(text, heading)
        if body is None or not normalize_content(body):
            raise SopError(f"Gate review section is missing or empty: {heading}")
    for heading in GATE_REVIEW_STAGE_SUBHEADINGS[stage]:
        body = _subsection_body(text, heading)
        if body is None or not normalize_content(body):
            raise SopError(f"Gate review stage section is missing or empty: {heading}")
    expected_members = active_member_ids(root, load_data(root / "project-state.yaml"))
    marked_members = sorted(set(re.findall(r"<!-- member:([a-zA-Z0-9._-]+) -->", text)))
    missing_members = sorted(set(expected_members) - set(marked_members))
    if missing_members:
        raise SopError("Gate review member coverage missing: " + ", ".join(missing_members))
    manifest = load_data(stage_path / "aggregation" / "artifact-manifest.yaml")
    expected_types = sorted(
        str(item.get("artifact_type", "")).strip()
        for item in manifest.get("artifacts", [])
        if isinstance(item, dict) and str(item.get("artifact_type", "")).strip()
    )
    marked_types = sorted(set(re.findall(r"<!-- artifact:([a-zA-Z0-9._-]+) -->", text)))
    missing_types = sorted(set(expected_types) - set(marked_types))
    if missing_types:
        raise SopError("Gate review artifact coverage missing: " + ", ".join(missing_types))
    repository_root = Path(project_root).resolve()
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    for raw_link in links:
        link = raw_link.strip().strip("<>")
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", link) or link.startswith("#"):
            continue
        candidate = (repository_root / link).resolve()
        if not candidate.is_relative_to(repository_root):
            raise SopError(f"Gate review appendix link escapes repository: {link}")
        if not candidate.exists():
            raise SopError(f"Gate review appendix link does not exist: {link}")
    corpus = _gate_review_source_corpus(root, stage_path, path)
    citation_pattern = r"\b(?:P-\d+|SRC-\d+|REQ-[A-Za-z0-9-]+|AC-[A-Za-z0-9-]+|DEC-[A-Za-z0-9-]+)\b"
    citations = sorted(set(re.findall(citation_pattern, text)))
    unknown = [citation for citation in citations if citation not in corpus]
    if unknown:
        raise SopError("Gate review citations are not registered: " + ", ".join(unknown))
    comparison_status = str(metadata.get("comparison_status", ""))
    if comparison_status not in GATE_REVIEW_COMPARISON_STATUSES:
        raise SopError(f"Invalid Gate review comparison_status: {comparison_status}")
    comparison_values = (
        metadata.get("comparison_path"),
        metadata.get("comparison_commit"),
        metadata.get("comparison_hash"),
    )
    if comparison_status == "none" and any(value is not None for value in comparison_values):
        raise SopError("comparison_status none requires null path, commit, and hash")
    if comparison_status != "none":
        comparison_path = str(metadata.get("comparison_path", "")).strip()
        candidate = (repository_root / comparison_path).resolve()
        if not comparison_path or not candidate.is_relative_to(repository_root) or not candidate.exists():
            raise SopError("Gate review comparison_path is missing or invalid")
        if not str(metadata.get("comparison_commit", "")).strip() or not str(
            metadata.get("comparison_hash", "")
        ).startswith("sha256:"):
            raise SopError("Gate review comparison commit and hash are required")
        if comparison_status == "baseline" and "baseline" not in candidate.parts:
            raise SopError("baseline comparison must point to a frozen baseline")
        if comparison_status == "reviewed" and "review" not in corpus.lower():
            raise SopError("reviewed comparison requires a human review record")
    source_state = gate_review_source_state(project_root, stage, remote)
    if metadata.get("source_commit") != source_state["source_commit"]:
        raise SopError("Gate review source_commit is stale")
    return {
        "path": str(path.relative_to(stage_path)).replace("\\", "/"),
        "document_hash": gate_review_document_hash(path),
        "source_fingerprint": gate_review_source_fingerprint(source_state),
        "source_commit": source_state["source_commit"],
        "comparison_status": comparison_status,
        "members": expected_members,
        "artifact_types": expected_types,
        "citations": citations,
    }


def gate_review_material_binding(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(review["path"]),
        "hash_algorithm": "sha256-normalized-v1",
        "document_hash": str(review["document_hash"]),
        "source_fingerprint": str(review["source_fingerprint"]),
        "source_commit": str(review["source_commit"]),
        "comparison_status": str(review["comparison_status"]),
        "review_required": True,
    }


def validate_bound_gate_review(
    binding: Any, current: dict[str, Any]
) -> None:
    if not isinstance(binding, dict) or binding.get("review_required") is not True:
        raise SopError("Gate human review material binding is missing")
    expected = gate_review_material_binding(current)
    for field in (
        "path",
        "hash_algorithm",
        "document_hash",
        "source_fingerprint",
        "source_commit",
        "comparison_status",
        "review_required",
    ):
        if binding.get(field) != expected.get(field):
            raise SopError(f"Gate review material is stale: {field} changed")


def cmd_init_gate_review(args: argparse.Namespace) -> None:
    print(init_gate_review(args.project_root, args.stage, args.replace, args.remote))


def cmd_validate_gate_review(args: argparse.Namespace) -> None:
    result = validate_gate_review(args.project_root, args.stage, args.remote)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def validate_artifact_manifest(stage_path: Path, stage: str, path: Path) -> None:
    data = load_data(path)
    if data.get("stage_id") != stage:
        raise SopError("artifact-manifest stage_id does not match the current stage")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        raise SopError("artifact-manifest artifacts must be a list")
    provided_types: set[str] = set()
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            raise SopError(f"artifact-manifest item {index} must be a mapping")
        artifact_type = str(item.get("artifact_type", "")).strip()
        relative = str(item.get("path", "")).strip()
        version = str(item.get("version", "")).strip()
        if not artifact_type or not relative or not version:
            raise SopError(f"artifact-manifest item {index} needs path, artifact_type, and version")
        candidate = (stage_path / relative).resolve()
        if not candidate.is_relative_to(stage_path.resolve()):
            raise SopError(f"Artifact path escapes the stage directory: {relative}")
        if not candidate.is_file():
            raise SopError(f"Declared artifact does not exist: {relative}")
        provided_types.add(artifact_type)
    missing_types = sorted(REQUIRED_GATE_ARTIFACT_TYPES[stage] - provided_types)
    if missing_types:
        raise SopError(f"Gate artifacts missing required types: {', '.join(missing_types)}")
    traceability = data.get("traceability")
    if not isinstance(traceability, dict):
        raise SopError("artifact-manifest traceability must be a mapping")
    required_coverage = {
        "01-requirement-contract": TRACEABILITY_FIELDS[:5],
        "02-solution-validation": TRACEABILITY_FIELDS[:6],
        "03-development-entry": TRACEABILITY_FIELDS,
    }[stage]
    incomplete = [key for key in required_coverage if traceability.get(key) != 100]
    if incomplete:
        raise SopError(f"P0 traceability must be 100 for: {', '.join(incomplete)}")


def cmd_prepare_gate(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project = load_data(root / "project-state.yaml")
    require_current_schema(project)
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    if state.get("status") != "team-review":
        raise SopError(f"Stage must be in team-review, not {state.get('status')}")
    aggregation = stage_path / "aggregation"
    summary = aggregation / "summary.md"
    manifest = aggregation / "artifact-manifest.yaml"
    if not summary.is_file():
        shutil.copyfile(asset("aggregation-summary.md"), summary)
    if not manifest.is_file():
        shutil.copyfile(asset("artifact-manifest.yaml"), manifest)
    if "[[FILL]]" in summary.read_text(encoding="utf-8"):
        raise SopError("Complete aggregation/summary.md before preparing the gate")
    if "[[FILL]]" in manifest.read_text(encoding="utf-8"):
        raise SopError("Complete aggregation/artifact-manifest.yaml before preparing the gate")
    validate_artifact_manifest(stage_path, args.stage, manifest)
    provenance_report = validate_provenance(args.project_root, args.stage)
    if not provenance_report["valid"]:
        raise SopError(
            "Document provenance must reach 100% coverage with reviewed, valid sources "
            "before preparing the Gate"
        )
    matrix_path = refresh_participation_matrix(args.project_root, args.stage)
    review_result = validate_gate_review(args.project_root, args.stage, args.remote)
    gate_path = stage_path / "gate" / "gate-decision.yaml"
    if gate_path.exists():
        raise SopError(f"Gate decision already exists: {gate_path}")
    gate_data = load_data(asset("gate-decision.yaml"))
    gate_id = STAGES[args.stage]["gate"]
    gate_data["gate_id"] = gate_id
    gate_data["stage_id"] = args.stage
    gate_data["highest_risk_level"] = project.get("highest_risk_level", "R0")
    collaboration_model = project.get("collaboration_model", "role-based")
    policy = project.get("gate_confirmation_policy", "accountable-members")
    gate_data["collaboration_model"] = collaboration_model
    gate_data["gate_confirmation_policy"] = policy
    gate_data["participation_matrix"] = "aggregation/participation-matrix.yaml"
    gate_data["provenance"] = {
        "source_index": "aggregation/provenance/source-block-index.yaml",
        "ledger": "aggregation/provenance/provenance-ledger.yaml",
        "report": "aggregation/provenance/provenance-report.md",
        "source_index_hash": provenance_report.get("source_index_hash"),
        "substantive_content_coverage": provenance_report.get("coverage_percent"),
        "p0_content_coverage": provenance_report.get("p0_coverage_percent"),
        "validated_at": provenance_report.get("generated_at"),
    }
    gate_data["human_review_material"] = gate_review_material_binding(review_result)
    gate_data["required_accountabilities"] = project.get("gate_accountability", {}).get(
        gate_id, {}
    )
    expected_members = active_member_ids(root, project)
    stage_records = (
        project.get("submission_tracking", {})
        .get("stages", {})
        .get(args.stage, {})
        .get("records", {})
    )
    opposed_or_reserved = sorted(
        {
            str(record.get("member_id"))
            for record in stage_records.values()
            if isinstance(record, dict)
            and record.get("human_submission_confirmation", {}).get("status")
            == "confirmed"
            and record.get("human_submission_confirmation", {}).get("requires_review")
            is True
        }
    )
    gate_data["participation_snapshot"] = {
        "expected_human_member_ids": expected_members,
        "confirmed_human_member_ids": [],
        "absent_or_exempt_member_ids": [],
        "opposed_or_reserved_member_ids": opposed_or_reserved,
    }
    gate_data["merge_plan"] = build_gate_merge_plan(
        args.project_root, root, project, args.remote
    )
    matrix = load_data(matrix_path)
    has_exceptions = bool(
        matrix.get("stage_summary", {}).get("has_recorded_exceptions")
        or state.get("missing_exceptions")
        or opposed_or_reserved
    )
    gate_data["consensus_claim"] = (
        "role-reviewed"
        if collaboration_model == "role-based"
        else (
            "collective-with-recorded-exceptions" if has_exceptions else "unanimous"
        )
    )
    dump_data(gate_path, gate_data)
    state["status"] = "gate-pending"
    state["updated_at"] = now_iso()
    dump_data(state_path, state)
    print(gate_path)


def valid_human_approvers(value: Any, active_members: set[str] | None = None) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
        name = str(item.get("name", "")).strip()
        role = str(item.get("role", "")).strip()
        member_id = str(item.get("member_id", "")).strip()
        approved_at = str(item.get("approved_at", "")).strip()
        if (
            not name
            or not role
            or not member_id
            or not approved_at
            or name.lower().startswith("ai-")
        ):
            return False
        if active_members is not None and member_id not in active_members:
            return False
    return True


def human_approver_roles(value: Any, active_members: set[str]) -> set[str]:
    if not valid_human_approvers(value, active_members):
        raise SopError(
            "Gate requires active human approvers with member_id, name, role, and approved_at"
        )
    return {safe_id(str(item["role"])) for item in value}


def human_approver_member_ids(value: Any, active_members: set[str]) -> set[str]:
    if not valid_human_approvers(value, active_members):
        raise SopError(
            "Gate requires active human approvers with member_id, name, role, and approved_at"
        )
    member_ids = [safe_id(str(item["member_id"])) for item in value]
    if len(member_ids) != len(set(member_ids)):
        raise SopError("Gate human_approvers contains duplicate member_id values")
    return set(member_ids)


def validate_conditions(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise SopError("conditional-pass requires explicit conditions")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise SopError(f"conditions[{index}] must be a mapping")
        missing = [
            field for field in ("owner", "due_at", "overdue_action")
            if not str(item.get(field, "")).strip()
        ]
        if missing:
            raise SopError(f"conditions[{index}] missing fields: {', '.join(missing)}")


def copy_aggregation_to_baseline(stage_path: Path, version: str) -> Path:
    target = stage_path / "baseline" / safe_id(version)
    if target.exists():
        raise SopError(f"Baseline already exists: {target}")
    review_source = gate_review_path(stage_path)
    if not review_source.is_file():
        raise SopError("Gate review material is missing during baseline freeze")
    target.mkdir(parents=True)
    for source in (stage_path / "aggregation").iterdir():
        destination = target / source.name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    shutil.copy2(stage_path / "gate" / "gate-decision.yaml", target / "gate-decision.yaml")
    shutil.copy2(review_source, target / GATE_REVIEW_FILE)
    return target


def cmd_approve_gate(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    require_current_schema(project)
    git_root = require_main_git_worktree(args.project_root, project)
    require_git_identity(git_root)
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    if state.get("status") != "gate-pending":
        raise SopError(f"Stage must be gate-pending, not {state.get('status')}")
    decision = load_data(stage_path / "gate" / "gate-decision.yaml")
    if decision.get("gate_id") != STAGES[args.stage]["gate"]:
        raise SopError("Gate decision does not match the stage")
    current_review = validate_gate_review(args.project_root, args.stage, args.remote)
    validate_bound_gate_review(decision.get("human_review_material"), current_review)
    if decision.get("conclusion") not in {"pass", "conditional-pass"}:
        raise SopError("Gate conclusion must be pass or conditional-pass")
    if decision.get("human_confirmed") is not True:
        raise SopError("Gate requires human_confirmed: true")
    gate_id = STAGES[args.stage]["gate"]
    active_members = set(active_member_ids(root, project))
    if not active_members:
        raise SopError("Gate approval requires at least one active registered member")
    approver_roles = human_approver_roles(
        decision.get("human_approvers"), active_members
    )
    approver_member_ids = human_approver_member_ids(
        decision.get("human_approvers"), active_members
    )
    collaboration_model = str(project.get("collaboration_model", "role-based"))
    policy = str(project.get("gate_confirmation_policy", "accountable-members"))
    if decision.get("collaboration_model") != collaboration_model:
        raise SopError("Gate collaboration_model must match project state")
    if decision.get("gate_confirmation_policy") != policy:
        raise SopError("Gate gate_confirmation_policy must match project state")
    if policy == "all-participants":
        missing_participants = sorted(active_members - approver_member_ids)
        if missing_participants:
            raise SopError(
                "Gate requires approval from all active participants: "
                + ", ".join(missing_participants)
            )
    elif policy != "accountable-members":
        raise SopError(f"Unknown gate confirmation policy: {policy}")

    accountability = project.get("gate_accountability", {}).get(gate_id, {})
    missing_assignments: list[str] = []
    missing_confirmations: list[str] = []
    for capacity in sorted(GATE_REQUIRED_CAPACITIES[gate_id]):
        assigned = set(str(value) for value in accountability.get(capacity, [])) & active_members
        if not assigned:
            missing_assignments.append(capacity)
        elif policy == "accountable-members" and not assigned <= approver_member_ids:
            missing_confirmations.append(
                capacity + "=" + ",".join(sorted(assigned - approver_member_ids))
            )
        elif policy == "all-participants" and not assigned & approver_member_ids:
            missing_confirmations.append(capacity)
    if missing_assignments:
        raise SopError(
            "Gate accountability capacities are unassigned: " + ", ".join(missing_assignments)
        )
    if missing_confirmations:
        raise SopError(
            "Gate accountability capacities lack member confirmation: "
            + ", ".join(missing_confirmations)
        )
    risk_level = str(project.get("highest_risk_level", "R0"))
    if decision.get("highest_risk_level") != risk_level:
        raise SopError("Gate highest_risk_level must match project state")
    if RISK_LEVELS.get(risk_level, -1) >= RISK_LEVELS["R2"]:
        risk_roles = set(project.get("risk_owner_roles", []))
        if not risk_roles:
            raise SopError("R2/R3 projects require risk_owner_roles in project state")
        missing_risk_responsibilities = []
        for risk_role in sorted(str(value) for value in risk_roles):
            assigned = set(str(value) for value in accountability.get(risk_role, []))
            covered_by_capacity = bool(assigned & approver_member_ids)
            if risk_role not in approver_roles and not covered_by_capacity:
                missing_risk_responsibilities.append(risk_role)
        if missing_risk_responsibilities:
            raise SopError(
                "Gate missing R2/R3 specialist responsibility confirmations: "
                + ", ".join(missing_risk_responsibilities)
            )
    matrix_path = refresh_participation_matrix(args.project_root, args.stage)
    matrix = load_data(matrix_path)
    snapshot = decision.get("participation_snapshot", {})
    opposed = sorted(
        str(value) for value in snapshot.get("opposed_or_reserved_member_ids", [])
    ) if isinstance(snapshot, dict) else []
    if policy == "all-participants" and opposed:
        raise SopError(
            "all-participants Gate cannot pass with opposed or reserved members: "
            + ", ".join(opposed)
        )
    has_exceptions = bool(
        matrix.get("stage_summary", {}).get("has_recorded_exceptions")
        or state.get("missing_exceptions")
        or opposed
    )
    expected_claim = "role-reviewed"
    if collaboration_model == "collective-participation":
        expected_claim = (
            "unanimous"
            if active_members <= approver_member_ids and not has_exceptions
            else "collective-with-recorded-exceptions"
        )
    if decision.get("consensus_claim") != expected_claim:
        raise SopError(f"Gate consensus_claim must be {expected_claim}")
    if decision.get("blocking_items"):
        raise SopError("Gate cannot pass with blocking_items")
    if decision.get("conclusion") == "conditional-pass":
        validate_conditions(decision.get("conditions"))
    version = str(decision.get("baseline_version", ""))
    expected_prefix = f"{STAGES[args.stage]['gate']}-V"
    if not version.startswith(expected_prefix):
        raise SopError(f"baseline_version must start with {expected_prefix}")
    plan_git_root, merge_plan = validate_gate_merge_plan(
        args.project_root,
        root,
        project,
        decision,
        require_human_coverage=True,
        remote=args.remote,
    )
    if plan_git_root.resolve() != git_root.resolve():
        raise SopError("Gate merge plan resolved to a different Git repository")

    decision["required_accountabilities"] = accountability
    decision["participation_snapshot"] = {
        "expected_human_member_ids": sorted(active_members),
        "confirmed_human_member_ids": sorted(approver_member_ids),
        "absent_or_exempt_member_ids": sorted(active_members - approver_member_ids),
        "opposed_or_reserved_member_ids": opposed,
    }
    dump_data(stage_path / "gate" / "gate-decision.yaml", decision)
    matrix["gate_confirmation"] = {
        "policy": policy,
        "approved_member_ids": sorted(approver_member_ids),
        "confirmed_at": now_iso(),
    }
    for round_record in matrix.get("rounds", {}).values():
        for item in round_record.get("participation", []):
            item["gate_confirmation"] = (
                "confirmed" if item.get("member_id") in approver_member_ids else "not-confirmed"
            )
    matrix["updated_at"] = now_iso()
    dump_data(matrix_path, matrix)

    approval_recorded_at = now_iso()
    merge_plan["status"] = "approved-pending-merge"
    merge_plan["approval_recorded_at"] = approval_recorded_at
    decision["merge_plan"] = merge_plan
    decision["approval_recorded_at"] = approval_recorded_at
    dump_data(stage_path / "gate" / "gate-decision.yaml", decision)
    state["status"] = "merge-pending"
    state["pending_baseline_version"] = version
    state["updated_at"] = now_iso()
    dump_data(state_path, state)
    project["status"] = "human-approved-merge-pending"
    project["git_integration"]["pending_gate"] = {
        "gate_id": gate_id,
        "stage_id": args.stage,
        "baseline_version": version,
        "approved_at": approval_recorded_at,
    }
    project["updated_at"] = now_iso()
    dump_data(project_path, project)
    refresh_project_state(args.project_root, source="approve-gate")
    approval_commit = commit_sop_paths(
        git_root,
        [stage_path / "gate" / "gate-decision.yaml", matrix_path, state_path, project_path],
        f"sop({gate_id}): record human approval pending mandatory merge",
    )
    print(
        json.dumps(
            {
                "status": "merge-pending",
                "gate_id": gate_id,
                "approval_commit": approval_commit,
                "next_command": f"merge-approved-gate --stage {args.stage}",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_merge_approved_gate(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    require_current_schema(project)
    stage_path = stage_root(args.project_root, args.stage)
    state_path = stage_path / "stage-state.yaml"
    state = load_data(state_path)
    if state.get("status") != "merge-pending":
        raise SopError(f"Stage must be merge-pending, not {state.get('status')}")
    decision_path = stage_path / "gate" / "gate-decision.yaml"
    decision = load_data(decision_path)
    gate_id = STAGES[args.stage]["gate"]
    if decision.get("gate_id") != gate_id:
        raise SopError("Gate decision does not match the stage")
    git_root, merge_plan = validate_gate_merge_plan(
        args.project_root,
        root,
        project,
        decision,
        require_human_coverage=True,
        remote=args.remote,
    )
    if merge_plan.get("status") != "approved-pending-merge":
        raise SopError("Gate merge_plan must be approved-pending-merge")
    require_main_git_worktree(args.project_root, project)
    require_git_identity(git_root)
    main_branch = configured_main_branch(project)
    main_before = resolve_git_head(git_root, main_branch)
    temporary_branch = safe_id(
        f"sop-integration-{gate_id.lower()}-{int(time.time())}-{os.getpid()}"
    )
    entries = sorted(
        merge_plan["member_branches"], key=lambda item: str(item["member_id"])
    )
    merged_records: list[dict[str, str]] = []
    temporary_created = False
    try:
        run_git(git_root, "checkout", "-b", temporary_branch, main_branch)
        temporary_created = True
        for entry in entries:
            member_id = str(entry["member_id"])
            expected_head = str(entry["expected_head"])
            run_git(
                git_root,
                "merge",
                "--no-ff",
                "--no-edit",
                "-m",
                f"sop({gate_id}): merge {member_id} from {entry['branch']}",
                expected_head,
            )
            merged_records.append(
                {
                    "member_id": member_id,
                    "branch": str(entry["branch"]),
                    "merged_head": expected_head,
                    "integration_head": run_git(git_root, "rev-parse", "HEAD").stdout.strip(),
                }
            )
        integration_head = run_git(git_root, "rev-parse", "HEAD").stdout.strip()
        run_git(git_root, "checkout", main_branch)
        run_git(git_root, "merge", "--ff-only", temporary_branch)
        temporary_created = False
        run_git(git_root, "branch", "-D", temporary_branch, check=False)
    except SopError as exc:
        run_git(git_root, "merge", "--abort", check=False)
        run_git(git_root, "checkout", main_branch, check=False)
        if temporary_created:
            run_git(git_root, "branch", "-D", temporary_branch, check=False)
        raise SopError(f"Mandatory member-branch integration failed; main was not advanced: {exc}") from exc

    main_after = resolve_git_head(git_root, main_branch)
    for entry in entries:
        result = run_git(
            git_root,
            "merge-base",
            "--is-ancestor",
            str(entry["expected_head"]),
            main_after,
            check=False,
        )
        if result.returncode != 0:
            raise SopError(
                f"Main verification failed for member branch: {entry['member_id']}"
            )

    merged_at = now_iso()
    merge_plan.update(
        {
            "status": "merged-and-verified",
            "target_head_before_merge": main_before,
            "target_head_after_merge": main_after,
            "integration_head": integration_head,
            "merged_member_branches": merged_records,
            "main_verification": {
                "target_branch_checked_out": True,
                "all_member_heads_are_ancestors": True,
            },
            "merged_at": merged_at,
        }
    )
    decision["merge_plan"] = merge_plan
    decision["merge_completed_at"] = merged_at
    dump_data(decision_path, decision)

    version = str(state.get("pending_baseline_version") or decision.get("baseline_version", ""))
    baseline_path = copy_aggregation_to_baseline(stage_path, version)
    state["status"] = "baselined"
    state["baseline_version"] = version
    state["pending_baseline_version"] = None
    state["merge_evidence"] = {
        "target_branch": main_branch,
        "target_head_after_merge": main_after,
        "merged_at": merged_at,
    }
    state["updated_at"] = now_iso()
    dump_data(state_path, state)

    project["baselines"][gate_id] = version
    project["git_integration"]["pending_gate"] = None
    project["git_integration"]["last_completed"] = {
        "gate_id": gate_id,
        "stage_id": args.stage,
        "baseline_version": version,
        "main_branch": main_branch,
        "main_head_after_merge": main_after,
        "merged_at": merged_at,
    }
    next_stage = STAGES[args.stage]["next"]
    if next_stage:
        project["status"] = "pre-development"
        project["current_stage"] = next_stage
        project["next_fixed_gate"] = STAGES[next_stage]["gate"]
        project["skill_release_control"] = {
            "status": "awaiting-confirmation",
            "confirmed_member_skill": project.get("skill_release_control", {}).get(
                "confirmed_member_skill"
            ),
            "after_gate": gate_id,
            "after_baseline": version,
            "requires_post_gate_confirmation": True,
        }
    else:
        project["status"] = "development-entry-approved"
        project["real_development_status"] = "approved-to-start"
        project["next_fixed_gate"] = None
    project["updated_at"] = now_iso()
    dump_data(project_path, project)
    refresh_project_state(args.project_root, source="merge-approved-gate")

    try:
        evidence_commit = commit_sop_paths(
            git_root,
            [decision_path, baseline_path, state_path, project_path],
            f"sop({gate_id}): finalize mandatory main integration for {version}",
        )
    except SopError:
        # A failed commit must not leave an untracked baseline that blocks a safe retry.
        if baseline_path.exists():
            tracked = run_git(
                git_root,
                "ls-files",
                "--error-unmatch",
                git_relative_path(git_root, baseline_path),
                check=False,
            )
            if tracked.returncode != 0:
                shutil.rmtree(baseline_path)
        raise
    print(
        json.dumps(
            {
                "status": "baselined",
                "gate_id": gate_id,
                "baseline_version": version,
                "main_branch": main_branch,
                "main_integration_head": main_after,
                "evidence_commit": evidence_commit,
                "merged_member_ids": [item["member_id"] for item in entries],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def proposed_member_release(args: argparse.Namespace) -> tuple[Path, dict[str, str]]:
    root = Path(args.project_root).resolve()
    git_root = find_git_root(root)
    if git_root is None:
        raise SopError("Skill release discovery requires the shared Git repository")
    release = discover_latest_stable_member_release(git_root)
    release["release_commit"] = run_git(git_root, "rev-parse", "HEAD").stdout.strip()
    return git_root, release


def cmd_prepare_skill_release(args: argparse.Namespace) -> None:
    _, release = proposed_member_release(args)
    print(
        json.dumps(
            {
                "status": "awaiting-human-confirmation",
                "confirmation_token": skill_release_confirmation_token(release),
                "instruction": (
                    "Review the exact stable Member Skill release, then run "
                    "confirm-skill-release with this token."
                ),
                "member_skill": release,
                "gate_effect": "none",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_confirm_skill_release(args: argparse.Namespace) -> None:
    _, release = proposed_member_release(args)
    token = skill_release_confirmation_token(release)
    if args.confirmation_token != token:
        raise SopError("Skill release confirmation token is stale or does not match")
    root = sop_root(args.project_root)
    project_path = root / "project-state.yaml"
    project = load_data(project_path)
    control = project.get("skill_release_control")
    if isinstance(control, dict):
        after_gate = control.get("after_gate")
        after_baseline = control.get("after_baseline")
    else:
        after_gate = None
        after_baseline = None
    project["skill_release_control"] = {
        "status": "confirmed",
        "confirmed_member_skill": release,
        "confirmed_by": project["coordinator_id"],
        "confirmed_at": now_iso(),
        "after_gate": after_gate,
        "after_baseline": after_baseline,
        "confirmation_token": token,
        "requires_post_gate_confirmation": False,
        "gate_effect": "none",
    }
    project["updated_at"] = now_iso()
    dump_data(project_path, project)
    print(
        json.dumps(
            {"status": "confirmed", "member_skill": release, "gate_effect": "none"},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_status(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project = load_data(root / "project-state.yaml")
    stages = {}
    for stage in STAGES:
        state = load_data(root / "stages" / stage / "stage-state.yaml")
        stages[stage] = {
            "status": state.get("status"),
            "expected_assignments": len(state.get("expected_assignments", [])),
            "baseline_version": state.get("baseline_version"),
            "rounds": state.get("rounds", {}),
        }
    print(json.dumps({"project": project, "stages": stages}, ensure_ascii=False, indent=2))


def cmd_refresh_project_state(args: argparse.Namespace) -> None:
    root = sop_root(args.project_root)
    project = load_data(root / "project-state.yaml")
    require_current_schema(project)
    git_root = find_git_root(Path(args.project_root))
    if args.fetch:
        if git_root is None:
            raise SopError("--fetch requires a Git repository")
        run_git(git_root, "fetch", args.remote, "--prune")
    if args.commit:
        require_main_git_worktree(args.project_root, project)
        if git_root is None:
            raise SopError("--commit requires a Git repository")
        require_git_identity(git_root)
    member_cli = (
        Path(args.member_cli).resolve()
        if args.member_cli
        else trusted_member_cli_asset()
    )
    if args.validate_remote and not member_cli.is_file():
        raise SopError(f"Remote validation requires member_cli.py: {member_cli}")
    project_path = refresh_project_state(
        args.project_root,
        source="refresh-project-state",
        remote=args.remote,
        validate_remote=args.validate_remote,
        member_cli=member_cli if args.validate_remote else None,
    )
    result: dict[str, Any] = {
        "project_state": str(project_path),
        "submission_tracking": load_data(project_path).get("submission_tracking", {}),
    }
    if args.commit:
        relative = git_relative_path(git_root, project_path)
        changed = run_git(
            git_root, "status", "--porcelain", "--", relative
        ).stdout.strip()
        result["commit"] = (
            commit_sop_paths(
                git_root,
                [project_path],
                "sop: refresh real-time member submission tracking",
            )
            if changed
            else None
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_install_dashboard(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).resolve()
    project = load_data(sop_root(project_root) / "project-state.yaml")
    require_current_schema(project)
    git_root = find_git_root(project_root)
    if git_root is None:
        raise SopError("README dashboard installation requires a Git repository")
    try:
        relative_project = project_root.relative_to(git_root)
    except ValueError as exc:
        raise SopError("Project root must be inside the detected Git repository") from exc
    state_path = (relative_project / "sop" / "project-state.yaml").as_posix()
    stages_path = (relative_project / "sop" / "stages").as_posix()
    submissions_glob = f"{stages_path}/**/submissions/**"
    acceptances_glob = f"{stages_path}/**/acceptances/**"
    dashboard_path = (relative_project / "dashboard" / "status.svg").as_posix()
    readme_path = "README.md"
    main_branch = str(
        project.get("git_integration", {}).get("main_branch", "main")
    ).strip() or "main"
    member_branches = []
    for member_id in active_member_ids(sop_root(project_root), project):
        role = load_data(sop_root(project_root) / "roles" / f"{member_id}.yaml")
        branch = str(role.get("git_branch", default_member_branch(member_id))).strip()
        if branch and branch != main_branch:
            member_branches.append(branch)
    tracked_branches = [main_branch, *sorted(set(member_branches))]
    tracked_branches_yaml = "\n".join(
        f"      - {json.dumps(branch)}" for branch in tracked_branches
    )
    project_root_path = relative_project.as_posix() or "."
    targets = {
        git_root / ".github" / "workflows" / "sop-readme-dashboard.yml": (
            dashboard_asset("sop-readme-dashboard.yml")
            .read_text(encoding="utf-8")
            .replace("[[MAIN_BRANCH_JSON]]", json.dumps(main_branch))
            .replace("[[TRACKED_BRANCHES_YAML]]", tracked_branches_yaml)
            .replace("[[PROJECT_ROOT_JSON]]", json.dumps(project_root_path))
            .replace("[[STATE_PATH_JSON]]", json.dumps(state_path))
            .replace(
                "[[STAGES_STATE_GLOB_JSON]]",
                json.dumps(f"{stages_path}/**/stage-state.yaml"),
            )
            .replace("[[SUBMISSIONS_GLOB_JSON]]", json.dumps(submissions_glob))
            .replace("[[ACCEPTANCES_GLOB_JSON]]", json.dumps(acceptances_glob))
            .replace("[[DASHBOARD_PATH_JSON]]", json.dumps(dashboard_path))
            .replace("[[README_PATH_JSON]]", json.dumps(readme_path))
        ),
        git_root / ".github" / "scripts" / "sop_readme_dashboard.py": dashboard_asset(
            "sop_readme_dashboard.py"
        ).read_text(encoding="utf-8"),
        git_root / ".github" / "scripts" / "sop_coordinator_cli.py": Path(
            __file__
        ).read_text(encoding="utf-8"),
        git_root / ".github" / "scripts" / "sop_member_cli.py": (
            trusted_member_cli_asset()
        ).read_text(encoding="utf-8"),
        git_root / ".github" / "scripts" / "sop_member_cli_1_8_0.py": (
            trusted_member_cli_asset("member_cli_1_8_0.py")
        ).read_text(encoding="utf-8"),
    }
    existing = [str(path) for path in targets if path.exists()]
    if existing and not args.force:
        raise SopError(
            "Dashboard files already exist; inspect them or rerun with --force: "
            + ", ".join(existing)
        )
    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    renderer = git_root / ".github" / "scripts" / "sop_readme_dashboard.py"
    rendered = subprocess.run(
        [
            sys.executable,
            str(renderer),
            "--state",
            str(git_root / state_path),
            "--output",
            str(git_root / dashboard_path),
            "--readme",
            str(git_root / readme_path),
        ],
        cwd=git_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if rendered.returncode != 0:
        raise SopError(f"README dashboard rendering failed: {rendered.stderr.strip()}")
    print(
        json.dumps(
            {
                "installed": [str(path) for path in targets],
                "generated": [
                    str(git_root / readme_path),
                    str(git_root / dashboard_path),
                ],
                "state_path": state_path,
                "main_branch": main_branch,
                "tracked_member_branches": sorted(set(member_branches)),
                "dashboard_mode": "private-readme-svg",
                "next_step": (
                    f"Commit and push README.md, {dashboard_path}, and the .github files."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("init-project")
    command.add_argument("project_root")
    command.add_argument("--project-id", required=True)
    command.add_argument("--project-name", required=True)
    command.add_argument("--coordinator-id", required=True)
    command.add_argument("--execution-mode", choices=("standard", "lightweight"), default="standard")
    command.add_argument(
        "--collaboration-model", choices=tuple(sorted(COLLABORATION_MODELS)), default="role-based"
    )
    command.add_argument(
        "--ai-dialogue-mode",
        choices=tuple(sorted(AI_DIALOGUE_MODES)),
        default="required",
    )
    command.add_argument(
        "--gate-confirmation-policy", choices=tuple(sorted(GATE_CONFIRMATION_POLICIES))
    )
    command.add_argument("--risk-level", choices=tuple(RISK_LEVELS), default="R1")
    command.add_argument("--risk-owner-role", action="append")
    command.add_argument("--real-development-status", default="not-started")
    command.add_argument("--member", action="append")
    command.add_argument("--member-branch", action="append")
    command.add_argument("--main-branch", default="main")
    command.set_defaults(handler=cmd_init_project)

    command = sub.add_parser("add-member")
    command.add_argument("project_root")
    command.add_argument("--member-id", required=True)
    command.add_argument("--human-owner", required=True)
    command.add_argument("--role")
    command.add_argument("--git-branch")
    command.set_defaults(handler=cmd_add_member)

    command = sub.add_parser("prepare-skill-release")
    command.add_argument("project_root")
    command.set_defaults(handler=cmd_prepare_skill_release)

    command = sub.add_parser("confirm-skill-release")
    command.add_argument("project_root")
    command.add_argument("--confirmation-token", required=True)
    command.set_defaults(handler=cmd_confirm_skill_release)

    command = sub.add_parser("assign-accountability")
    command.add_argument("project_root")
    command.add_argument("--member-id", required=True)
    command.add_argument("--gate", required=True, choices=tuple(sorted(GATE_REQUIRED_CAPACITIES)))
    command.add_argument("--capacity", required=True, action="append")
    command.set_defaults(handler=cmd_assign_accountability)

    command = sub.add_parser("migrate-project")
    command.add_argument("project_root")
    command.add_argument("--execution-mode", choices=("standard", "lightweight"))
    command.add_argument("--risk-level", choices=tuple(RISK_LEVELS))
    command.add_argument("--risk-owner-role", action="append")
    command.add_argument("--main-branch")
    command.set_defaults(handler=cmd_migrate_project)

    command = sub.add_parser("init-gate-review")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--remote", default="origin")
    command.add_argument("--replace", action="store_true")
    command.set_defaults(handler=cmd_init_gate_review)

    command = sub.add_parser("validate-gate-review")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--remote", default="origin")
    command.set_defaults(handler=cmd_validate_gate_review)

    command = sub.add_parser("create-assignment")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--round", required=True)
    command.add_argument("--member-id", required=True)
    command.add_argument("--kind", required=True)
    command.add_argument("--task-source", required=True)
    command.add_argument("--objective", required=True)
    command.add_argument("--scope-in", required=True, action="append")
    command.add_argument("--scope-out", action="append")
    command.add_argument("--input-ref", action="append")
    command.add_argument("--deliverable", required=True, action="append")
    command.add_argument("--acceptance-criterion", required=True, action="append")
    command.add_argument("--constraint", action="append")
    command.add_argument("--dependency", action="append")
    command.add_argument("--priority", choices=tuple(sorted(TASK_PRIORITIES)), default="P1")
    command.add_argument("--coordinator-note", action="append")
    command.add_argument(
        "--human-collaboration-mode",
        choices=("none", "adaptive-grill"),
        default="none",
    )
    command.add_argument("--human-collaboration-max-questions", type=int, default=20)
    command.add_argument(
        "--independence-mode",
        required=True,
        choices=(
            "isolated-discovery",
            "isolated-design",
            "specialized-preparation",
            "shared-review",
        ),
    )
    command.add_argument("--deadline")
    command.add_argument("--review-of-round")
    command.add_argument("--confirm-dispatch")
    command.set_defaults(handler=cmd_create_assignment)

    command = sub.add_parser("create-collective-round")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--round", required=True)
    command.add_argument("--kind", required=True)
    command.add_argument("--task-source", required=True)
    command.add_argument("--objective", required=True)
    command.add_argument("--scope-in", required=True, action="append")
    command.add_argument("--scope-out", action="append")
    command.add_argument("--input-ref", action="append")
    command.add_argument("--deliverable", required=True, action="append")
    command.add_argument("--acceptance-criterion", required=True, action="append")
    command.add_argument("--constraint", action="append")
    command.add_argument("--dependency", action="append")
    command.add_argument("--priority", choices=tuple(sorted(TASK_PRIORITIES)), default="P1")
    command.add_argument("--coordinator-note", action="append")
    command.add_argument(
        "--human-collaboration-mode",
        choices=("none", "adaptive-grill"),
        default="none",
    )
    command.add_argument("--human-collaboration-max-questions", type=int, default=20)
    command.add_argument(
        "--independence-mode",
        required=True,
        choices=(
            "isolated-discovery",
            "isolated-design",
            "specialized-preparation",
            "shared-review",
        ),
    )
    command.add_argument("--deadline")
    command.add_argument("--review-of-round")
    command.add_argument("--confirm-dispatch")
    command.set_defaults(handler=cmd_create_collective_round)

    for name, handler in (
        ("validate-stage", cmd_validate_stage),
        ("close-stage", cmd_close_stage),
        ("prepare-gate", cmd_prepare_gate),
        ("approve-gate", cmd_approve_gate),
        ("merge-approved-gate", cmd_merge_approved_gate),
    ):
        command = sub.add_parser(name)
        command.add_argument("project_root")
        command.add_argument("--stage", required=True, choices=STAGES)
        command.add_argument("--remote", default="origin")
        if name == "close-stage":
            command.add_argument("--allow-missing", action="store_true")
            command.add_argument("--missing-reason")
            command.add_argument("--missing-impact")
        command.set_defaults(handler=handler)

    for name, handler in (
        ("validate-round", cmd_validate_round),
        ("close-round", cmd_close_round),
        ("complete-round-review", cmd_complete_round_review),
    ):
        command = sub.add_parser(name)
        command.add_argument("project_root")
        command.add_argument("--stage", required=True, choices=STAGES)
        command.add_argument("--round", required=True)
        command.add_argument("--remote", default="origin")
        if name in {"close-round", "complete-round-review"}:
            command.add_argument("--allow-missing", action="store_true")
            command.add_argument("--missing-reason")
            command.add_argument("--missing-impact")
        command.set_defaults(handler=handler)

    command = sub.add_parser("supersede-round")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--round", required=True)
    command.add_argument("--replacement-round", required=True)
    command.add_argument("--reason", required=True)
    command.add_argument("--finding-id")
    command.set_defaults(handler=cmd_supersede_round)

    command = sub.add_parser("record-shared-review")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--round", required=True)
    command.add_argument("--member-id", required=True)
    command.add_argument("--artifact-ref", required=True)
    command.add_argument("--note")
    command.set_defaults(handler=cmd_record_shared_review)

    command = sub.add_parser("transition")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--to", required=True, choices=ALLOWED_TRANSITIONS)
    command.set_defaults(handler=cmd_transition)

    command = sub.add_parser("status")
    command.add_argument("project_root")
    command.set_defaults(handler=cmd_status)

    command = sub.add_parser("refresh-project-state")
    command.add_argument("project_root")
    command.add_argument("--remote", default="origin")
    command.add_argument("--fetch", action="store_true")
    command.add_argument("--commit", action="store_true")
    command.add_argument("--validate-remote", action="store_true")
    command.add_argument("--member-cli")
    command.set_defaults(handler=cmd_refresh_project_state)

    command = sub.add_parser("install-dashboard")
    command.add_argument("project_root")
    command.add_argument("--force", action="store_true")
    command.set_defaults(handler=cmd_install_dashboard)

    for name, handler in (
        ("build-source-index", cmd_build_source_index),
        ("validate-provenance", cmd_validate_provenance),
        ("provenance-report", cmd_provenance_report),
    ):
        command = sub.add_parser(name)
        command.add_argument("project_root")
        command.add_argument("--stage", required=True, choices=STAGES)
        command.add_argument("--remote", default="origin")
        command.set_defaults(handler=handler)

    command = sub.add_parser("trace-content")
    command.add_argument("project_root")
    command.add_argument("--stage", required=True, choices=STAGES)
    command.add_argument("--target", required=True)
    command.add_argument("--provenance-id", required=True)
    command.add_argument(
        "--derivation-type", required=True, choices=tuple(sorted(DERIVATION_TYPES))
    )
    command.add_argument("--source-block", action="append")
    command.add_argument("--decision-ref")
    command.add_argument("--legacy-reason")
    command.add_argument("--note")
    command.add_argument(
        "--review-status", choices=("draft", "reviewed", "approved"), default="draft"
    )
    command.add_argument("--reviewer")
    command.add_argument("--remote", default="origin")
    command.add_argument("--replace", action="store_true")
    command.set_defaults(handler=cmd_trace_content)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        with project_lock(args.project_root):
            args.handler(args)
            if args.command not in {
                "status",
                "prepare-skill-release",
                "confirm-skill-release",
                "refresh-project-state",
                "install-dashboard",
                "init-gate-review",
                "validate-gate-review",
                "approve-gate",
                "merge-approved-gate",
            }:
                project_path = sop_root(args.project_root) / "project-state.yaml"
                if project_path.is_file():
                    if args.command in {
                        "validate-stage",
                        "close-stage",
                        "validate-round",
                        "close-round",
                        "complete-round-review",
                        "build-source-index",
                    }:
                        refresh_project_state(
                            args.project_root,
                            source=args.command,
                            remote=args.remote,
                            validate_remote=True,
                            member_cli=default_remote_member_cli(),
                        )
                    else:
                        refresh_project_state(args.project_root, source=args.command)
        return 0
    except SopError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic local helper for ai-sop-member."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


PROTOCOL_VERSION = "1.0"
PROJECT_SCHEMA_VERSION = "1.5"
SUPPORTED_PROTOCOL_MAJOR = PROTOCOL_VERSION.split(".")[0]
SUPPORTED_PROJECT_SCHEMA_MAJOR = PROJECT_SCHEMA_VERSION.split(".")[0]
SKILL_VERSION = "1.8.1"
BUILD_ID = "member-cli-1.8.1-assignment-acceptance-v1"
SOURCE_ID_PATTERN = re.compile(r"^SRC-\d{3,}$")
SOURCE_BLOCK_ID_PATTERN = re.compile(r"^SB-[a-f0-9]{16}(?:-\d+)?$")
RISK_ID_PATTERN = re.compile(r"^RISK-\d{3,}$")
ALLOWED_EVIDENCE_TYPES = {"direct", "indirect", "inference", "simulation"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_CONFLICT_STATUS = {"none", "pending-verification", "conflict"}
ALLOWED_RISK_LEVELS = {"R0", "R1", "R2", "R3"}
ALLOWED_COLLABORATION_MODELS = {"role-based", "collective-participation"}
ALLOWED_PARTICIPATION_MODES = {
    "role-assigned",
    "collective-round",
    "individual-exception",
}
ALLOWED_TASK_PRIORITIES = {"P0", "P1", "P2", "P3"}
REQUIRED_ASSIGNMENT_FIELDS = (
    "assignment_id",
    "assignment_version",
    "project_id",
    "stage_id",
    "round_id",
    "assignment_kind",
    "member_id",
    "role",
    "git_branch",
    "main_branch",
    "collaboration_model",
    "participation_mode",
    "objective",
    "independence_mode",
    "protocol_version",
    "project_schema_version",
    "baseline_version",
    "baseline_refs",
    "required_outputs",
    "return_to",
)
REQUIRED_OUTPUTS = (
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
SUBMISSION_CONFIRMATION_OUTPUT = "human-submission-confirmation.yaml"
SUBMISSION_CONFIRMATION_POSITIONS = (
    "confirm",
    "oppose",
    "question",
    "reserve",
)
ADAPTIVE_GRILL_CONFIRMATIONS = {
    "problem-definition",
    "p0-scope",
    "unresolved-disagreements",
}
ADAPTIVE_GRILL_EVIDENCE_TYPES = {
    "member-direct",
    "member-confirmed-summary",
    "ai-inference",
    "user-direct",
}


class SopError(Exception):
    pass


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SopError(f"Git {' '.join(args)} failed: {detail}")
    return result


def find_git_root(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    result = run_git(start, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def version_tuple(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except ValueError as exc:
        raise SopError(f"Invalid version: {value}") from exc


def validate_string_list(
    value: Any, field: str, *, required: bool = False
) -> list[str]:
    if not isinstance(value, list):
        raise SopError(f"Assignment {field} must be a list")
    normalized = [str(item).strip() for item in value]
    if any(not item for item in normalized):
        raise SopError(f"Assignment {field} cannot contain blank values")
    if required and not normalized:
        raise SopError(f"Assignment {field} must contain at least one value")
    return normalized


def validate_task_contract(data: dict[str, Any]) -> None:
    minimum_skill = str(data.get("minimum_skill_version", "1.0.0"))
    if version_tuple(minimum_skill) < version_tuple("1.7.2"):
        return
    required_fields = (
        "task_source",
        "scope",
        "input_refs",
        "deliverables",
        "acceptance_criteria",
        "constraints",
        "dependencies",
        "priority",
        "coordinator_notes",
        "task_contract_hash",
        "dispatch_confirmation",
    )
    if version_tuple(minimum_skill) >= version_tuple("1.7.4"):
        required_fields += ("human_collaboration",)
    if version_tuple(minimum_skill) >= version_tuple("1.7.5"):
        required_fields += ("submission_confirmation",)
    if version_tuple(minimum_skill) >= version_tuple("1.8.0"):
        required_fields += ("ai_dialogue_collaboration", "required_member_skill")
    if version_tuple(minimum_skill) >= version_tuple("1.8.1"):
        required_fields += ("acceptance_policy",)
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise SopError(f"Assignment task contract missing fields: {', '.join(missing)}")
    if not str(data.get("task_source", "")).strip():
        raise SopError("Assignment task_source cannot be blank")
    if not str(data.get("objective", "")).strip():
        raise SopError("Assignment objective cannot be blank")
    scope = data.get("scope")
    if not isinstance(scope, dict):
        raise SopError("Assignment scope must be a mapping")
    included = validate_string_list(scope.get("included"), "scope.included", required=True)
    excluded = validate_string_list(scope.get("excluded"), "scope.excluded")
    input_refs = validate_string_list(data.get("input_refs"), "input_refs")
    deliverables = validate_string_list(data.get("deliverables"), "deliverables", required=True)
    acceptance = validate_string_list(
        data.get("acceptance_criteria"), "acceptance_criteria", required=True
    )
    constraints = validate_string_list(data.get("constraints"), "constraints")
    dependencies = validate_string_list(data.get("dependencies"), "dependencies")
    notes = validate_string_list(data.get("coordinator_notes"), "coordinator_notes")
    priority = str(data.get("priority", ""))
    if priority not in ALLOWED_TASK_PRIORITIES:
        raise SopError(f"Invalid assignment priority: {priority}")
    contract = {
        "task_source": str(data["task_source"]).strip(),
        "objective": str(data["objective"]).strip(),
        "scope": {"included": included, "excluded": excluded},
        "input_refs": input_refs,
        "deliverables": deliverables,
        "acceptance_criteria": acceptance,
        "constraints": constraints,
        "dependencies": dependencies,
        "priority": priority,
        "coordinator_notes": notes,
    }
    if version_tuple(minimum_skill) >= version_tuple("1.7.4"):
        contract["human_collaboration"] = data["human_collaboration"]
    if version_tuple(minimum_skill) >= version_tuple("1.7.5"):
        contract["submission_confirmation"] = data["submission_confirmation"]
    if version_tuple(minimum_skill) >= version_tuple("1.8.0"):
        contract["ai_dialogue_collaboration"] = data["ai_dialogue_collaboration"]
        contract["required_member_skill"] = data["required_member_skill"]
    if version_tuple(minimum_skill) >= version_tuple("1.8.1"):
        contract["acceptance_policy"] = validate_assignment_acceptance_policy(data)
    expected_hash = hashlib.sha256(
        json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if str(data.get("task_contract_hash")) != expected_hash:
        raise SopError("Assignment task contract hash does not match its task content")
    confirmation = data.get("dispatch_confirmation")
    if not isinstance(confirmation, dict) or confirmation.get("status") != "confirmed":
        raise SopError("Assignment was not explicitly confirmed for dispatch")
    for field in ("confirmation_token", "confirmed_by", "confirmed_at"):
        if not str(confirmation.get(field, "")).strip():
            raise SopError(f"Assignment dispatch_confirmation.{field} cannot be blank")


def validate_human_collaboration(data: dict[str, Any]) -> dict[str, Any]:
    minimum_skill = str(data.get("minimum_skill_version", "1.0.0"))
    value = data.get("human_collaboration")
    if value is None and version_tuple(minimum_skill) < version_tuple("1.7.4"):
        return {"mode": "none", "required": False}
    if not isinstance(value, dict):
        raise SopError("Assignment human_collaboration must be a mapping")
    mode = str(value.get("mode", ""))
    required = value.get("required")
    if mode == "none":
        if required is not False:
            raise SopError("human_collaboration mode none must use required=false")
        return value
    if mode != "adaptive-grill" or required is not True:
        raise SopError("Unsupported or inconsistent human_collaboration configuration")
    if data.get("assignment_kind") != "requirement-analysis":
        raise SopError("adaptive-grill is only valid for requirement-analysis")
    if data.get("independence_mode") != "isolated-discovery":
        raise SopError("adaptive-grill requires isolated-discovery")
    human_owner = str(data.get("human_owner", "")).strip()
    if not human_owner or str(value.get("human_owner", "")).strip() != human_owner:
        raise SopError("adaptive-grill human_owner must match the registered assignment owner")
    topics = validate_string_list(value.get("required_topics"), "human_collaboration.required_topics", required=True)
    confirmations = set(
        validate_string_list(
            value.get("required_confirmations"),
            "human_collaboration.required_confirmations",
            required=True,
        )
    )
    if not ADAPTIVE_GRILL_CONFIRMATIONS.issubset(confirmations):
        raise SopError("adaptive-grill is missing mandatory human confirmations")
    if len(topics) != len(set(topics)):
        raise SopError("adaptive-grill required_topics cannot contain duplicates")
    if value.get("unanswered_policy") != "block":
        raise SopError("adaptive-grill unanswered_policy must be block")
    max_questions = value.get("max_questions")
    if not isinstance(max_questions, int) or not 3 <= max_questions <= 100:
        raise SopError("adaptive-grill max_questions must be an integer between 3 and 100")
    if value.get("allow_early_completion") is not True:
        raise SopError("adaptive-grill must allow completion when all conditions are satisfied")
    return value


def requires_submission_confirmation(data: dict[str, Any]) -> bool:
    minimum_skill = str(data.get("minimum_skill_version", "1.0.0"))
    return version_tuple(minimum_skill) >= version_tuple("1.7.5")


def validate_exact_member_skill(data: dict[str, Any]) -> None:
    minimum_skill = str(data.get("minimum_skill_version", "1.0.0"))
    if version_tuple(minimum_skill) < version_tuple("1.8.0"):
        return
    required = data.get("required_member_skill")
    if not isinstance(required, dict):
        raise SopError("V1.8 assignment requires an exact Member Skill release")
    expected_name = str(required.get("name", ""))
    expected_version = str(required.get("version", ""))
    expected_build = str(required.get("build_id", ""))
    if (
        expected_name != "ai-sop-member"
        or expected_version != SKILL_VERSION
        or expected_build != BUILD_ID
    ):
        raise SopError(
            "Assignment requires exact Member Skill "
            f"{expected_version}/{expected_build}; current {SKILL_VERSION}/{BUILD_ID}"
        )
    for field in ("package_path", "release_commit"):
        if not str(required.get(field, "")).strip():
            raise SopError(f"Exact Member Skill binding is missing {field}")


def validate_ai_dialogue_policy(data: dict[str, Any]) -> dict[str, str] | None:
    minimum_skill = str(data.get("minimum_skill_version", "1.0.0"))
    if version_tuple(minimum_skill) < version_tuple("1.8.0"):
        return None
    value = data.get("ai_dialogue_collaboration")
    if not isinstance(value, dict) or value.get("mode") not in {"required", "optional"}:
        raise SopError("V1.8 assignment AI dialogue mode must be required or optional")
    if value.get("source") != "project-policy":
        raise SopError("AI dialogue policy must come from project-policy")
    return {"mode": str(value["mode"]), "source": "project-policy"}


def requires_assignment_acceptance(data: dict[str, Any]) -> bool:
    minimum_skill = str(data.get("minimum_skill_version", "1.0.0"))
    return version_tuple(minimum_skill) >= version_tuple("1.8.1")


def validate_assignment_acceptance_policy(
    data: dict[str, Any],
) -> dict[str, Any] | None:
    if not requires_assignment_acceptance(data):
        return None
    value = data.get("acceptance_policy")
    expected = {
        "mode": "explicit-member-receipt",
        "required": True,
        "receipt_schema_version": "1.0",
        "gate_effect": "none",
    }
    if value != expected:
        raise SopError("V1.8.1 assignment acceptance_policy is invalid")
    return expected


def default_ai_dialogue_summary(
    assignment: dict[str, Any], member_id: str
) -> dict[str, Any]:
    policy = validate_ai_dialogue_policy(assignment)
    if policy is None:
        raise SopError("Legacy assignments do not use an AI dialogue summary")
    return {
        "schema_version": "1.0",
        "status": "pending",
        "mode": policy["mode"],
        "member_id": member_id,
        "task_understanding": {
            "reviewed": False,
            "member_correction_status": "pending",
        },
        "exploration": {
            "initial_map": False,
            "alternatives_compared": False,
            "counterexamples_discussed": False,
            "risks_discussed": False,
            "tradeoffs_discussed": False,
            "periodic_restatement_confirmed": False,
        },
        "member_position": {
            "confirmed_points": [],
            "opposed_points": [],
            "questions": [],
            "reservations": [],
        },
        "ai_inferences": [],
        "mapped_to_formal_outputs": False,
        "gate_effect": "none",
    }


def validate_ai_dialogue_summary(
    summary: dict[str, Any], assignment: dict[str, Any], member_id: str
) -> None:
    policy = validate_ai_dialogue_policy(assignment)
    if policy is None:
        return
    if summary.get("member_id") != member_id or summary.get("mode") != policy["mode"]:
        raise SopError("AI dialogue summary identity or mode does not match the assignment")
    if summary.get("gate_effect") != "none":
        raise SopError("AI dialogue collaboration must not have Gate effect")
    status = summary.get("status")
    if status == "skipped":
        if policy["mode"] == "required":
            raise SopError("Required AI dialogue collaboration cannot be skipped")
        return
    if status != "completed":
        raise SopError("AI dialogue collaboration is not completed")
    understanding = summary.get("task_understanding")
    exploration = summary.get("exploration")
    if not isinstance(understanding, dict) or understanding.get("reviewed") is not True:
        raise SopError("AI dialogue task understanding was not reviewed")
    if understanding.get("member_correction_status") not in {"confirmed", "corrected"}:
        raise SopError("Member did not confirm or correct the task understanding")
    required_exploration = (
        "initial_map",
        "alternatives_compared",
        "counterexamples_discussed",
        "risks_discussed",
        "tradeoffs_discussed",
        "periodic_restatement_confirmed",
    )
    if not isinstance(exploration, dict) or any(
        exploration.get(field) is not True for field in required_exploration
    ):
        raise SopError("AI dialogue exploration evidence is incomplete")
    position = summary.get("member_position")
    if not isinstance(position, dict) or not any(
        position.get(field)
        for field in ("confirmed_points", "opposed_points", "questions", "reservations")
    ):
        raise SopError("AI dialogue has not converged to a member position")
    if summary.get("mapped_to_formal_outputs") is not True:
        raise SopError("AI dialogue conclusions were not mapped to formal outputs")


def validate_submission_confirmation_policy(data: dict[str, Any]) -> dict[str, Any] | None:
    if not requires_submission_confirmation(data):
        return None
    value = data.get("submission_confirmation")
    if not isinstance(value, dict):
        raise SopError("Assignment submission_confirmation must be a mapping")
    if value.get("required") is not True:
        raise SopError("Assignment submission_confirmation.required must be true")
    human_owner = str(data.get("human_owner", "")).strip()
    if not human_owner:
        raise SopError("Assignment human_owner is required for submission confirmation")
    if str(value.get("human_owner", "")).strip() != human_owner:
        raise SopError("submission_confirmation human_owner must match the assignment")
    if value.get("source_file") != "main-output.md":
        raise SopError("submission_confirmation source_file must be main-output.md")
    if value.get("hash_algorithm") != "sha256-normalized-v1":
        raise SopError("submission_confirmation hash_algorithm must be sha256-normalized-v1")
    subjects = validate_string_list(
        value.get("required_subjects"),
        "submission_confirmation.required_subjects",
        required=True,
    )
    if set(subjects) != {"main-output-hash", "personal-stance"}:
        raise SopError("submission_confirmation must require body hash and personal stance")
    positions = validate_string_list(
        value.get("allowed_positions"),
        "submission_confirmation.allowed_positions",
        required=True,
    )
    if set(positions) != set(SUBMISSION_CONFIRMATION_POSITIONS):
        raise SopError("submission_confirmation allowed_positions are invalid")
    if value.get("stale_policy") != "block":
        raise SopError("submission_confirmation stale_policy must be block")
    if value.get("gate_effect") != "none":
        raise SopError("submission confirmation must not act as a Gate approval")
    return value


def required_output_names(assignment: dict[str, Any]) -> tuple[str, ...]:
    raw = assignment.get("required_outputs")
    if not isinstance(raw, list) or any(not str(name).strip() for name in raw):
        raise SopError("Assignment required_outputs must be a non-empty string list")
    names = tuple(str(name).strip() for name in raw)
    missing_core = [name for name in REQUIRED_OUTPUTS if name not in names]
    if missing_core:
        raise SopError(f"Assignment required_outputs missing core files: {', '.join(missing_core)}")
    collaboration = validate_human_collaboration(assignment)
    if collaboration.get("mode") == "adaptive-grill":
        missing_grill = [name for name in ADAPTIVE_GRILL_OUTPUTS if name not in names]
        if missing_grill:
            raise SopError(
                f"adaptive-grill assignment missing required outputs: {', '.join(missing_grill)}"
            )
    if requires_submission_confirmation(assignment):
        validate_submission_confirmation_policy(assignment)
        if SUBMISSION_CONFIRMATION_OUTPUT not in names:
            raise SopError(
                "Assignment required_outputs missing human-submission-confirmation.yaml"
            )
    return names


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
    # JSON is valid YAML 1.2 and keeps the distributed CLI dependency-free.
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


def markdown_content_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    headings: list[str] = []
    buffer: list[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal buffer
        normalized = normalize_content("\n".join(buffer))
        buffer = []
        if not normalized:
            return
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
            continue
        buffer.append(raw)
    flush()
    return blocks


def build_content_index(
    submission_dir: Path, assignment: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    main_path = submission_dir / "main-output.md"
    text = main_path.read_text(encoding="utf-8")
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
        evidence_refs = sorted(set(re.findall(r"\bSRC-\d{3,}\b", normalized)))
        blocks.append(
            {
                "source_block_id": block_id,
                "ordinal": ordinal,
                "heading_path": raw["heading_path"],
                "content_hash": content_hash(normalized),
                "text_excerpt": normalized.replace("\n", " ")[:200],
                "evidence_refs": evidence_refs,
            }
        )
    return {
        "schema_version": "1.0",
        "submission_id": manifest.get("submission_id", submission_dir.name),
        "assignment_id": assignment["assignment_id"],
        "member_id": assignment["member_id"],
        "source_file": "main-output.md",
        "document_hash": content_hash(text),
        "block_count": len(blocks),
        "indexed_at": now_iso(),
        "blocks": blocks,
    }


def update_content_index(
    submission_dir: Path, assignment: dict[str, Any]
) -> dict[str, Any]:
    manifest_path = submission_dir / "submission-manifest.yaml"
    manifest = load_data(manifest_path)
    index = build_content_index(submission_dir, assignment, manifest)
    dump_data(submission_dir / "content-block-index.yaml", index)
    manifest["content_index"] = "content-block-index.yaml"
    manifest["content_document_hash"] = index["document_hash"]
    manifest["content_block_count"] = index["block_count"]
    dump_data(manifest_path, manifest)
    return index


def validate_content_index(
    submission_dir: Path, assignment: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    actual = load_data(submission_dir / "content-block-index.yaml")
    expected = build_content_index(submission_dir, assignment, manifest)
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
            raise SopError(f"content-block-index.yaml is stale or invalid: {field}")
    for item in actual.get("blocks", []):
        block_id = str(item.get("source_block_id", ""))
        if not SOURCE_BLOCK_ID_PATTERN.fullmatch(block_id):
            raise SopError(f"Invalid source_block_id: {block_id}")
    if manifest.get("content_document_hash") != actual.get("document_hash"):
        raise SopError("Submission manifest content_document_hash is stale")
    if manifest.get("content_block_count") != actual.get("block_count"):
        raise SopError("Submission manifest content_block_count is stale")
    return actual


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


def new_submission_confirmation(
    assignment: dict[str, Any], submission_id: str
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "not-prepared",
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "submission_id": submission_id,
        "member_id": str(assignment["member_id"]),
        "human_owner": str(assignment["human_owner"]),
        "source_file": "main-output.md",
        "hash_algorithm": "sha256-normalized-v1",
        "document_hash": None,
        "personal_stance": {"code": None, "statement": None},
        "confirmed_subjects": {
            "exact_document_hash": False,
            "personal_stance": False,
        },
        "human_collaboration_mode": validate_human_collaboration(assignment)["mode"],
        "authority_scope": "member-contribution-submission-only",
        "gate_effect": "none",
        "prepared_at": None,
        "confirmed_by": None,
        "confirmed_at": None,
        "confirmation_method": None,
        "confirmation_token": None,
    }


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


def validate_human_submission_confirmation(
    submission_dir: Path,
    assignment: dict[str, Any],
    manifest: dict[str, Any],
    document_hash: str,
    *,
    require_confirmed: bool,
) -> dict[str, Any] | None:
    if not requires_submission_confirmation(assignment):
        return None
    validate_submission_confirmation_policy(assignment)
    record = load_data(submission_dir / SUBMISSION_CONFIRMATION_OUTPUT)
    expected_identity = {
        "schema_version": "1.0",
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "submission_id": str(manifest.get("submission_id", submission_dir.name)),
        "member_id": str(assignment["member_id"]),
        "human_owner": str(assignment["human_owner"]),
        "source_file": "main-output.md",
        "hash_algorithm": "sha256-normalized-v1",
        "human_collaboration_mode": validate_human_collaboration(assignment)["mode"],
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
            "Human submission confirmation identity mismatch: " + ", ".join(mismatches)
        )
    status = str(record.get("status", ""))
    if status not in {"not-prepared", "awaiting-human-confirmation", "confirmed"}:
        raise SopError(f"Invalid human submission confirmation status: {status}")
    if manifest.get("human_submission_confirmation") != confirmation_manifest_summary(record):
        raise SopError("Manifest human_submission_confirmation summary is stale")
    if status == "not-prepared":
        if require_confirmed:
            raise SopError(
                "Human owner confirmation is not prepared; run prepare-confirmation first"
            )
        return record
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
    expected_token = submission_confirmation_token(
        assignment,
        str(manifest.get("submission_id", submission_dir.name)),
        document_hash,
        position,
        statement,
    )
    if str(record.get("confirmation_token", "")) != expected_token:
        raise SopError("Human owner confirmation token does not match the current preview")
    if not str(record.get("prepared_at", "")).strip():
        raise SopError("Human owner confirmation prepared_at cannot be blank")
    if status == "awaiting-human-confirmation":
        if require_confirmed:
            raise SopError("Human owner has not confirmed the current body hash and stance")
        return record
    confirmed_subjects = record.get("confirmed_subjects")
    if not isinstance(confirmed_subjects, dict) or any(
        confirmed_subjects.get(field) is not True
        for field in ("exact_document_hash", "personal_stance")
    ):
        raise SopError("Human owner confirmation subjects are incomplete")
    if str(record.get("confirmed_by", "")).strip() != str(assignment["human_owner"]):
        raise SopError("Human owner confirmation was not made by the registered owner")
    if not str(record.get("confirmed_at", "")).strip():
        raise SopError("Human owner confirmation confirmed_at cannot be blank")
    if record.get("confirmation_method") != "explicit-human-owner":
        raise SopError("Human owner confirmation method must be explicit-human-owner")
    return record


def validate_assignment(path: Path, member_id: str) -> dict[str, Any]:
    data = load_data(path)
    missing = [field for field in REQUIRED_ASSIGNMENT_FIELDS if field not in data]
    if missing:
        raise SopError(f"Assignment missing fields: {', '.join(missing)}")
    if str(data["member_id"]) != member_id:
        raise SopError(
            f"Assignment belongs to {data['member_id']}, not current member {member_id}"
        )
    major = str(data["protocol_version"]).split(".")[0]
    if major != SUPPORTED_PROTOCOL_MAJOR:
        raise SopError(
            f"Unsupported protocol {data['protocol_version']}; expected major {SUPPORTED_PROTOCOL_MAJOR}"
        )
    schema_major = str(data["project_schema_version"]).split(".")[0]
    if schema_major != SUPPORTED_PROJECT_SCHEMA_MAJOR:
        raise SopError(
            f"Unsupported project schema {data['project_schema_version']}; "
            f"expected major {SUPPORTED_PROJECT_SCHEMA_MAJOR}"
        )
    minimum_skill = str(data.get("minimum_skill_version", "1.0.0"))
    if version_tuple(SKILL_VERSION) < version_tuple(minimum_skill):
        raise SopError(
            f"Assignment requires ai-sop-member {minimum_skill}, current {SKILL_VERSION}"
        )
    validate_exact_member_skill(data)
    validate_task_contract(data)
    validate_human_collaboration(data)
    validate_ai_dialogue_policy(data)
    validate_assignment_acceptance_policy(data)
    validate_submission_confirmation_policy(data)
    required_output_names(data)
    if path.parent.name != "dispatch":
        raise SopError("Assignment must be stored in a stage dispatch directory")
    if str(data.get("status", "distributed")) not in {"distributed", "acknowledged"}:
        raise SopError(f"Assignment is not executable: status={data.get('status')}")
    if data["collaboration_model"] not in ALLOWED_COLLABORATION_MODELS:
        raise SopError(f"Invalid collaboration_model: {data['collaboration_model']}")
    if data["participation_mode"] not in ALLOWED_PARTICIPATION_MODES:
        raise SopError(f"Invalid participation_mode: {data['participation_mode']}")
    git_branch = str(data.get("git_branch", "")).strip()
    main_branch = str(data.get("main_branch", "")).strip()
    if not git_branch or git_branch.startswith("-"):
        raise SopError("Assignment git_branch is invalid")
    if not main_branch or main_branch.startswith("-"):
        raise SopError("Assignment main_branch is invalid")
    if git_branch == main_branch:
        raise SopError("Member assignment git_branch cannot be the main branch")
    if (
        data["collaboration_model"] == "role-based"
        and data["participation_mode"] != "role-assigned"
    ):
        raise SopError("role-based assignments must use participation_mode role-assigned")
    if (
        data["collaboration_model"] == "collective-participation"
        and data["participation_mode"] == "role-assigned"
    ):
        raise SopError("collective assignments cannot use participation_mode role-assigned")
    if data["assignment_kind"] == "shared-review" and not data.get("review_of_round"):
        raise SopError("shared-review assignment must identify review_of_round")
    baseline_refs = data.get("baseline_refs")
    if not isinstance(baseline_refs, list) or not baseline_refs:
        raise SopError("Assignment baseline_refs must be a non-empty list")
    project_root = next(
        (
            candidate
            for candidate in path.parents
            if (candidate / "sop" / "project-state.yaml").is_file()
        ),
        None,
    )
    if project_root is None:
        raise SopError("Cannot locate project root for assignment baseline validation")
    missing_refs: list[str] = []
    incomplete_refs: list[str] = []
    for raw_ref in baseline_refs:
        reference = str(raw_ref).strip()
        relative = Path(reference)
        if not reference or relative.is_absolute() or ".." in relative.parts:
            raise SopError(f"Assignment baseline_ref is invalid: {raw_ref}")
        target = (project_root / relative).resolve()
        if not target.is_relative_to(project_root):
            raise SopError(f"Assignment baseline_ref escapes the project root: {reference}")
        if not target.exists():
            missing_refs.append(reference)
            continue
        if target.is_file() and target.name == "summary.md":
            text = target.read_text(encoding="utf-8")
            if not text.strip() or "[[FILL]]" in text:
                incomplete_refs.append(reference)
        if target.is_file() and target.name == "submission-index.yaml":
            index = load_data(target)
            if str(index.get("round_id", "")) != target.parent.name:
                incomplete_refs.append(reference)
    if missing_refs:
        raise SopError(f"Assignment baseline_refs are missing: {', '.join(missing_refs)}")
    if incomplete_refs:
        raise SopError(
            "Assignment baseline_refs are incomplete or inconsistent: "
            f"{', '.join(sorted(set(incomplete_refs)))}"
        )
    return data


def validate_git_workspace(
    assignment_path: Path,
    assignment: dict[str, Any],
    *,
    remote: str,
    fetch: bool,
    require_assignment_sync: bool,
    detached_validation: bool = False,
) -> dict[str, Any]:
    git_root = find_git_root(assignment_path)
    if git_root is None:
        raise SopError("Assignment must be used from a dedicated Git checkout or worktree")
    if fetch:
        run_git(git_root, "fetch", remote, "--prune")
    remote_url = run_git(git_root, "remote", "get-url", remote, check=False)
    if remote_url.returncode != 0:
        raise SopError(f"Required Git remote is not configured: {remote}")
    current_branch = run_git(git_root, "branch", "--show-current").stdout.strip()
    expected_branch = str(assignment["git_branch"])
    if not detached_validation and current_branch != expected_branch:
        raise SopError(
            f"Wrong member branch: expected {expected_branch}, current {current_branch or 'detached'}"
        )
    main_ref = f"{remote}/{assignment['main_branch']}"
    member_ref = f"{remote}/{expected_branch}"
    if run_git(git_root, "rev-parse", "--verify", main_ref, check=False).returncode != 0:
        raise SopError(f"Remote main baseline is unavailable: {main_ref}; run git fetch {remote}")
    if run_git(git_root, "rev-parse", "--verify", member_ref, check=False).returncode != 0:
        raise SopError(f"Registered remote member branch is unavailable: {member_ref}")
    head = run_git(git_root, "rev-parse", "HEAD").stdout.strip()
    member_head = run_git(git_root, "rev-parse", member_ref).stdout.strip()
    if detached_validation and head != member_head:
        raise SopError(
            f"Detached validation must use exact registered ref {member_ref}: {member_head}"
        )
    member_ancestor = run_git(git_root, "merge-base", "--is-ancestor", member_ref, "HEAD", check=False)
    if not detached_validation and member_ancestor.returncode != 0:
        raise SopError(
            f"Local branch has diverged from or is behind {member_ref}; stop and contact the coordinator"
        )
    assignment_authorization: dict[str, Any] | None = None
    if require_assignment_sync:
        try:
            assignment_relative = assignment_path.resolve().relative_to(git_root).as_posix()
        except ValueError as exc:
            raise SopError("Assignment path escapes the Git worktree") from exc

        local_assignment = run_git(
            git_root,
            "rev-parse",
            "--verify",
            f"HEAD:{assignment_relative}",
            check=False,
        )
        if local_assignment.returncode != 0:
            raise SopError(
                f"Assignment is not committed on the member branch: {assignment_relative}"
            )

        main_snapshot = ""
        first_parent_history = run_git(
            git_root,
            "rev-list",
            "--first-parent",
            main_ref,
        ).stdout.splitlines()
        for candidate in first_parent_history:
            contained = run_git(
                git_root,
                "merge-base",
                "--is-ancestor",
                candidate,
                "HEAD",
                check=False,
            )
            if contained.returncode == 0:
                main_snapshot = candidate
                break
        if not main_snapshot:
            raise SopError(
                f"Member branch contains no authorized first-parent snapshot of {main_ref}"
            )

        authorized_assignment_ref = main_snapshot if detached_validation else main_ref
        authorized_assignment = run_git(
            git_root,
            "rev-parse",
            "--verify",
            f"{authorized_assignment_ref}:{assignment_relative}",
            check=False,
        )
        if authorized_assignment.returncode != 0:
            if detached_validation:
                raise SopError(
                    "Assignment is not present in the authorized historical main snapshot: "
                    f"{assignment_relative}"
                )
            raise SopError(
                f"Assignment is not published by {main_ref}: {assignment_relative}"
            )
        assignment_commit = run_git(
            git_root,
            "log",
            "-1",
            "--first-parent",
            "--format=%H",
            authorized_assignment_ref,
            "--",
            assignment_relative,
        ).stdout.strip()
        if not assignment_commit:
            raise SopError(
                "Cannot locate the authorized assignment commit on "
                f"{authorized_assignment_ref}: {assignment_relative}"
            )
        if local_assignment.stdout.strip() != authorized_assignment.stdout.strip():
            raise SopError(
                "Member assignment does not match the exact coordinator-authorized task on "
                f"{authorized_assignment_ref}: {assignment_relative}"
            )
        assignment_changes = run_git(
            git_root,
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            assignment_relative,
        ).stdout.strip()
        if assignment_changes:
            raise SopError("Member assignment has uncommitted local changes")

        snapshot_contains_assignment = run_git(
            git_root,
            "merge-base",
            "--is-ancestor",
            assignment_commit,
            main_snapshot,
            check=False,
        )
        if snapshot_contains_assignment.returncode != 0:
            raise SopError(
                "Member branch does not contain the coordinator-authorized assignment "
                f"commit {assignment_commit} in its first-parent main snapshot. Stop and "
                f"contact the coordinator for a verified merge of {main_ref}; do not "
                "rebase, reset, squash, or force-push."
            )

        baseline_paths = [
            str(item).replace("\\", "/") for item in assignment["baseline_refs"]
        ]
        baseline_diff = run_git(
            git_root,
            "diff",
            "--quiet",
            main_snapshot,
            "HEAD",
            "--",
            *baseline_paths,
            check=False,
        )
        if baseline_diff.returncode != 0:
            raise SopError(
                "Authorized baseline files differ from the main snapshot merged for this "
                "assignment"
            )
        baseline_changes = run_git(
            git_root,
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *baseline_paths,
        ).stdout.strip()
        if baseline_changes:
            raise SopError("Authorized baseline files have uncommitted local changes")
        assignment_authorization = {
            "mode": (
                "historical-assignment-main-snapshot"
                if detached_validation
                else "confirmed-assignment-main-snapshot"
            ),
            "assignment_path": assignment_relative,
            "assignment_commit": assignment_commit,
            "main_snapshot": main_snapshot,
            "main_snapshot_method": "latest-contained-first-parent",
            "authorized_assignment_ref": authorized_assignment_ref,
            "remote_main_head": run_git(git_root, "rev-parse", main_ref).stdout.strip(),
        }
    return {
        "git_root": str(git_root),
        "remote": remote,
        "remote_url": remote_url.stdout.strip(),
        "current_branch": current_branch,
        "expected_branch": expected_branch,
        "main_ref": main_ref,
        "head": head,
        "member_cli": {
            "skill_version": SKILL_VERSION,
            "build_id": BUILD_ID,
        },
        "assignment_authorization": assignment_authorization,
    }


def stage_dir_for(assignment_path: Path) -> Path:
    return assignment_path.resolve().parent.parent


def output_dir_for(assignment_path: Path, assignment: dict[str, Any]) -> Path:
    stage_dir = stage_dir_for(assignment_path)
    member_root = (stage_dir / "submissions" / str(assignment["member_id"])).resolve()
    submission_name = f"{assignment['assignment_id']}-v{assignment['assignment_version']}"
    output = (member_root / submission_name).resolve()
    if not output.is_relative_to(member_root):
        raise SopError("Calculated submission path escapes the member-owned directory")
    return output


def acceptance_path_for(assignment_path: Path, assignment: dict[str, Any]) -> Path:
    stage_dir = stage_dir_for(assignment_path)
    member_root = (stage_dir / "acceptances" / str(assignment["member_id"])).resolve()
    receipt_name = f"{assignment['assignment_id']}-v{assignment['assignment_version']}.yaml"
    receipt = (member_root / receipt_name).resolve()
    if not receipt.is_relative_to(member_root):
        raise SopError("Calculated acceptance path escapes the member-owned directory")
    return receipt


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def mapping_hash(value: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def acceptance_receipt_summary(
    receipt: dict[str, Any], receipt_path: Path
) -> dict[str, Any]:
    return {
        "required": True,
        "status": "accepted",
        "accepted_at": receipt["accepted_at"],
        "receipt_path": receipt["receipt_path"],
        "receipt_hash": mapping_hash(receipt),
    }


def validate_assignment_acceptance(
    assignment_path: Path,
    assignment: dict[str, Any],
    *,
    require_accepted: bool = True,
) -> dict[str, Any]:
    if not requires_assignment_acceptance(assignment):
        return {
            "required": False,
            "status": "legacy-not-required",
            "gate_effect": "none",
        }
    policy = validate_assignment_acceptance_policy(assignment)
    receipt_path = acceptance_path_for(assignment_path, assignment)
    if not receipt_path.is_file():
        if require_accepted:
            raise SopError(
                "Assignment has not been explicitly accepted; run accept-assignment first"
            )
        return {
            "required": True,
            "status": "pending",
            "receipt_path": receipt_path.as_posix(),
            "gate_effect": "none",
        }
    receipt = load_data(receipt_path)
    git_root = find_git_root(assignment_path)
    if git_root is None:
        raise SopError("Assignment acceptance requires a Git worktree")
    expected_path = receipt_path.relative_to(git_root).as_posix()
    expected = {
        "schema_version": str(policy["receipt_schema_version"]),
        "status": "accepted",
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "member_id": str(assignment["member_id"]),
        "human_owner": str(assignment.get("human_owner", "")),
        "git_branch": str(assignment["git_branch"]),
        "assignment_path": assignment_path.relative_to(git_root).as_posix(),
        "assignment_document_hash": file_hash(assignment_path),
        "task_contract_hash": str(assignment.get("task_contract_hash", "")),
        "receipt_path": expected_path,
        "acceptance_method": "explicit-member-command",
        "gate_effect": "none",
        "member_skill": {
            "name": "ai-sop-member",
            "version": SKILL_VERSION,
            "build_id": BUILD_ID,
        },
    }
    mismatches = [key for key, value in expected.items() if receipt.get(key) != value]
    if mismatches:
        raise SopError(
            "Assignment acceptance receipt does not match assignment: "
            + ", ".join(mismatches)
        )
    if not str(receipt.get("accepted_at", "")).strip():
        raise SopError("Assignment acceptance receipt accepted_at cannot be blank")
    return acceptance_receipt_summary(receipt, receipt_path)


def cmd_accept_assignment(args: argparse.Namespace) -> None:
    assignment_path = Path(args.assignment).resolve()
    assignment = validate_assignment(assignment_path, args.member_id)
    validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    if not requires_assignment_acceptance(assignment):
        raise SopError("Legacy assignment does not require an acceptance receipt")
    receipt_path = acceptance_path_for(assignment_path, assignment)
    if receipt_path.exists():
        summary = validate_assignment_acceptance(assignment_path, assignment)
        print(json.dumps({"accepted": True, "existing": True, **summary}, ensure_ascii=False))
        return
    git_root = find_git_root(assignment_path)
    if git_root is None:
        raise SopError("Assignment acceptance requires a Git worktree")
    policy = validate_assignment_acceptance_policy(assignment)
    receipt = {
        "schema_version": str(policy["receipt_schema_version"]),
        "status": "accepted",
        "assignment_id": str(assignment["assignment_id"]),
        "assignment_version": str(assignment["assignment_version"]),
        "member_id": str(assignment["member_id"]),
        "human_owner": str(assignment.get("human_owner", "")),
        "git_branch": str(assignment["git_branch"]),
        "assignment_path": assignment_path.relative_to(git_root).as_posix(),
        "assignment_document_hash": file_hash(assignment_path),
        "task_contract_hash": str(assignment.get("task_contract_hash", "")),
        "receipt_path": receipt_path.relative_to(git_root).as_posix(),
        "accepted_at": now_iso(),
        "acceptance_method": "explicit-member-command",
        "gate_effect": "none",
        "member_skill": {
            "name": "ai-sop-member",
            "version": SKILL_VERSION,
            "build_id": BUILD_ID,
        },
    }
    dump_data(receipt_path, receipt)
    summary = validate_assignment_acceptance(assignment_path, assignment)
    print(json.dumps({"accepted": True, "existing": False, **summary}, ensure_ascii=False))


def template_for(kind: str) -> Path:
    base = Path(__file__).resolve().parent.parent / "assets" / "submission-template"
    candidate = base / f"{kind}.md"
    return candidate if candidate.is_file() else base / "generic.md"


def cmd_inspect(args: argparse.Namespace) -> None:
    path = Path(args.assignment).resolve()
    data = validate_assignment(path, args.member_id)
    workspace = validate_git_workspace(
        path,
        data,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    summary = {
        "assignment_id": data["assignment_id"],
        "member_id": data["member_id"],
        "stage_id": data["stage_id"],
        "round_id": data["round_id"],
        "assignment_kind": data["assignment_kind"],
        "collaboration_model": data["collaboration_model"],
        "participation_mode": data["participation_mode"],
        "review_of_round": data.get("review_of_round"),
        "independence_mode": data["independence_mode"],
        "baseline_version": data["baseline_version"],
        "task_source": data.get("task_source"),
        "objective": data["objective"],
        "scope": data.get("scope"),
        "input_refs": data.get("input_refs", []),
        "deliverables": data.get("deliverables", []),
        "acceptance_criteria": data.get("acceptance_criteria", []),
        "constraints": data.get("constraints", []),
        "dependencies": data.get("dependencies", []),
        "priority": data.get("priority"),
        "coordinator_notes": data.get("coordinator_notes", []),
        "task_contract_hash": data.get("task_contract_hash"),
        "dispatch_confirmation": data.get("dispatch_confirmation"),
        "human_collaboration": validate_human_collaboration(data),
        "submission_confirmation": validate_submission_confirmation_policy(data),
        "assignment_acceptance": validate_assignment_acceptance(
            path, data, require_accepted=False
        ),
        "member_cli": {"skill_version": SKILL_VERSION, "build_id": BUILD_ID},
        "output_dir": str(output_dir_for(path, data)),
        "workspace": workspace,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_init(args: argparse.Namespace) -> None:
    assignment_path = Path(args.assignment).resolve()
    assignment = validate_assignment(assignment_path, args.member_id)
    validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    assignment_acceptance = validate_assignment_acceptance(
        assignment_path, assignment
    )
    output = output_dir_for(assignment_path, assignment)
    if output.exists():
        raise SopError(f"Submission already exists: {output}")
    output.mkdir(parents=True)

    collaboration = validate_human_collaboration(assignment)
    required_outputs = required_output_names(assignment)
    task_contract = {
        "task_source": assignment.get("task_source"),
        "objective": assignment["objective"],
        "scope": assignment.get("scope"),
        "input_refs": assignment.get("input_refs", []),
        "deliverables": assignment.get("deliverables", []),
        "acceptance_criteria": assignment.get("acceptance_criteria", []),
        "constraints": assignment.get("constraints", []),
        "dependencies": assignment.get("dependencies", []),
        "priority": assignment.get("priority"),
        "coordinator_notes": assignment.get("coordinator_notes", []),
    }
    if version_tuple(str(assignment.get("minimum_skill_version", "1.0.0"))) >= version_tuple("1.7.4"):
        task_contract["human_collaboration"] = collaboration
    confirmation_policy = validate_submission_confirmation_policy(assignment)
    if confirmation_policy is not None:
        task_contract["submission_confirmation"] = confirmation_policy
    dialogue_policy = validate_ai_dialogue_policy(assignment)
    if dialogue_policy is not None:
        task_contract["ai_dialogue_collaboration"] = dialogue_policy
        task_contract["required_member_skill"] = assignment["required_member_skill"]
    acceptance_policy = validate_assignment_acceptance_policy(assignment)
    if acceptance_policy is not None:
        task_contract["acceptance_policy"] = acceptance_policy
    manifest = {
        "submission_id": output.name,
        "assignment_id": assignment["assignment_id"],
        "assignment_version": str(assignment["assignment_version"]),
        "member_id": assignment["member_id"],
        "human_owner": assignment.get("human_owner", ""),
        "git_branch": assignment["git_branch"],
        "main_branch": assignment["main_branch"],
        "stage_id": assignment["stage_id"],
        "round_id": assignment["round_id"],
        "assignment_kind": assignment["assignment_kind"],
        "collaboration_model": assignment["collaboration_model"],
        "participation_mode": assignment["participation_mode"],
        "review_of_round": assignment.get("review_of_round"),
        "skill_name": "ai-sop-member",
        "skill_version": SKILL_VERSION,
        "protocol_version": str(assignment["protocol_version"]),
        "project_schema_version": str(assignment["project_schema_version"]),
        "baseline_version": str(assignment["baseline_version"]),
        "task_contract_hash": assignment.get("task_contract_hash"),
        "task_contract": task_contract,
        "human_collaboration": collaboration,
        "ai_dialogue_collaboration": dialogue_policy,
        "required_member_skill": assignment.get("required_member_skill"),
        "submission_confirmation": confirmation_policy,
        "assignment_acceptance": assignment_acceptance,
        "started_at": now_iso(),
        "submitted_at": None,
        "status": "in-progress",
        "outputs": list(required_outputs),
        "content_index": "content-block-index.yaml",
        "content_document_hash": None,
        "content_block_count": 0,
        "sources_count": 0,
        "assumptions_count": 0,
        "new_requirements_count": 0,
        "risks_count": 0,
        "confidence": "medium",
    }
    if confirmation_policy is not None:
        confirmation_record = new_submission_confirmation(assignment, output.name)
        manifest["human_submission_confirmation"] = confirmation_manifest_summary(
            confirmation_record
        )
    dump_data(output / "submission-manifest.yaml", manifest)
    shutil.copyfile(template_for(str(assignment["assignment_kind"])), output / "main-output.md")
    dump_data(
        output / "source-ledger.yaml",
        {
            "sources": [],
            "schema_hint": {
                "required": [
                    "source_id", "source_type", "summary", "acquisition_method",
                    "occurred_at", "context", "evidence_type", "confidence",
                    "confidence_reason", "conflict_status"
                ]
            },
        },
    )
    dump_data(output / "assumptions-and-gaps.yaml", {"assumptions": [], "gaps": []})
    dump_data(
        output / "risks-and-new-requirements.yaml",
        {"risks": [], "new_requirements": []},
    )
    if dialogue_policy is not None:
        dump_data(
            output / "ai-dialogue-summary.yaml",
            default_ai_dialogue_summary(assignment, str(assignment["member_id"])),
        )
    if collaboration.get("mode") == "adaptive-grill":
        session_id = f"HC-{assignment['assignment_id']}-v{assignment['assignment_version']}"
        coverage = {
            str(topic).replace("-", "_"): "missing"
            for topic in collaboration["required_topics"]
        }
        dump_data(
            output / "human-collaboration-log.yaml",
            {
                "schema_version": "1.0",
                "session_id": session_id,
                "assignment_id": assignment["assignment_id"],
                "member_id": assignment["member_id"],
                "mode": "adaptive-grill",
                "human_owner": assignment["human_owner"],
                "status": "not-started",
                "collaboration_consent": {
                    "human_owner": assignment["human_owner"],
                    "understands_recording": False,
                    "understands_evidence_boundary": False,
                    "agrees_to_participate": False,
                },
                "exchanges": [],
                "confirmations": [],
                "coverage": coverage,
                "gaps": [],
                "question_count": 0,
                "max_questions": collaboration["max_questions"],
            },
        )
        dump_data(
            output / "grill-summary.yaml",
            {
                "schema_version": "1.0",
                "session_id": session_id,
                "assignment_id": assignment["assignment_id"],
                "member_id": assignment["member_id"],
                "status": "not-started",
                "problem_definition": {
                    "statement": "",
                    "evidence_refs": [],
                    "confirmation": "pending",
                },
                "target_users": [],
                "scenarios": [],
                "member_judgments": [],
                "ai_inferences": [],
                "p0_scope": [],
                "p1_scope": [],
                "excluded_scope": [],
                "risks": [],
                "counterexamples": [],
                "unknowns": [],
                "unresolved_disagreements": [],
                "required_confirmations": {
                    subject: "pending"
                    for subject in collaboration["required_confirmations"]
                },
            },
        )
    if confirmation_policy is not None:
        dump_data(output / SUBMISSION_CONFIRMATION_OUTPUT, confirmation_record)
    update_content_index(output, assignment)
    if collaboration.get("mode") == "adaptive-grill":
        print(
            json.dumps(
                {
                    "output_dir": str(output),
                    "human_collaboration": "adaptive-grill",
                    "status": "awaiting-human-consent",
                    "next_action": (
                        "Read references/adaptive-grill.md, obtain consent from the registered "
                        "human_owner, then ask exactly one question at a time. After the final "
                        "main-output.md is ready, prepare and obtain the separate submission "
                        "confirmation before submit."
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if confirmation_policy is not None:
            print(
                json.dumps(
                    {
                        "output_dir": str(output),
                        "human_collaboration": "none",
                        "grill_required": False,
                        "submission_confirmation_required": True,
                        "next_action": (
                            "Complete the outputs, run prepare-confirmation, show the exact body "
                            "hash and personal stance preview to the registered human_owner, then "
                            "run confirm-submission only after their explicit confirmation."
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(output)


def read_list(path: Path, key: str) -> list[Any]:
    data = load_data(path)
    value = data.get(key, [])
    if not isinstance(value, list):
        raise SopError(f"{path.name}.{key} must be a list")
    return value


def require_mapping_fields(item: Any, fields: tuple[str, ...], label: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise SopError(f"{label} must be a mapping")
    missing = [field for field in fields if item.get(field) in (None, "")]
    if missing:
        raise SopError(f"{label} missing fields: {', '.join(missing)}")
    return item


def validate_sources(sources: list[Any], assignment_kind: str) -> None:
    if assignment_kind == "requirement-analysis" and not sources:
        raise SopError("requirement-analysis requires at least one labeled source")
    seen: set[str] = set()
    fields = (
        "source_id", "source_type", "summary", "acquisition_method", "occurred_at",
        "context", "evidence_type", "confidence", "confidence_reason", "conflict_status",
    )
    for index, raw in enumerate(sources):
        item = require_mapping_fields(raw, fields, f"sources[{index}]")
        source_id = str(item["source_id"])
        if not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise SopError(f"Invalid source_id: {source_id}")
        if source_id in seen:
            raise SopError(f"Duplicate source_id: {source_id}")
        seen.add(source_id)
        if item["evidence_type"] not in ALLOWED_EVIDENCE_TYPES:
            raise SopError(f"Invalid evidence_type for {source_id}")
        if item["confidence"] not in ALLOWED_CONFIDENCE:
            raise SopError(f"Invalid confidence for {source_id}")
        if item["conflict_status"] not in ALLOWED_CONFLICT_STATUS:
            raise SopError(f"Invalid conflict_status for {source_id}")


def validate_risks_and_requirements(risks: list[Any], new_requirements: list[Any]) -> None:
    for index, raw in enumerate(risks):
        item = require_mapping_fields(
            raw, ("risk_id", "level", "description", "gate_trigger", "owner"),
            f"risks[{index}]",
        )
        if not RISK_ID_PATTERN.fullmatch(str(item["risk_id"])):
            raise SopError(f"Invalid risk_id: {item['risk_id']}")
        if item["level"] not in ALLOWED_RISK_LEVELS:
            raise SopError(f"Invalid risk level: {item['level']}")
        if item["level"] in {"R2", "R3"} and item["gate_trigger"] is not True:
            raise SopError(f"{item['risk_id']} at {item['level']} must set gate_trigger: true")
    required = (
        "candidate_id", "source_refs", "target_user", "description", "business_value",
        "suggested_priority", "baseline_impact", "return_to",
    )
    for index, raw in enumerate(new_requirements):
        item = require_mapping_fields(raw, required, f"new_requirements[{index}]")
        if not isinstance(item["source_refs"], list) or not item["source_refs"]:
            raise SopError(f"new_requirements[{index}].source_refs must be a non-empty list")


def validate_user_stories(main_text: str) -> None:
    stories = [line.strip() for line in main_text.splitlines() if "As a " in line]
    if not stories:
        raise SopError("requirement-analysis requires at least one standard user story")
    for index, story in enumerate(stories):
        if ", I want " not in story or ", so that " not in story:
            raise SopError(f"user story {index + 1} does not use As a/I want/so that")
        if not re.search(r"\bSRC-\d{3,}\b", story):
            raise SopError(f"user story {index + 1} must link at least one SRC ID")
        if "[直接证据]" not in story and "[AI 推演]" not in story:
            raise SopError(f"user story {index + 1} must mark [直接证据] or [AI 推演]")


def validate_adaptive_grill(
    submission_dir: Path, assignment: dict[str, Any]
) -> None:
    collaboration = validate_human_collaboration(assignment)
    if collaboration.get("mode") != "adaptive-grill":
        return
    log = load_data(submission_dir / "human-collaboration-log.yaml")
    summary = load_data(submission_dir / "grill-summary.yaml")
    expected_identity = {
        "assignment_id": str(assignment["assignment_id"]),
        "member_id": str(assignment["member_id"]),
    }
    for label, document in (("human collaboration log", log), ("grill summary", summary)):
        for field, expected in expected_identity.items():
            if str(document.get(field, "")) != expected:
                raise SopError(f"{label} {field} does not match the assignment")
        if document.get("status") != "grill-completed":
            raise SopError(f"{label} is not grill-completed")
        if document.get("blocking"):
            raise SopError(f"{label} still contains a blocking condition")
    if log.get("mode") != "adaptive-grill":
        raise SopError("human collaboration log mode must be adaptive-grill")
    if str(log.get("human_owner", "")) != str(assignment.get("human_owner", "")):
        raise SopError("human collaboration log human_owner does not match the assignment")
    consent = log.get("collaboration_consent")
    if not isinstance(consent, dict):
        raise SopError("adaptive-grill collaboration consent is missing")
    if str(consent.get("human_owner", "")) != str(assignment.get("human_owner", "")):
        raise SopError("adaptive-grill consent was not provided by the registered human_owner")
    for field in (
        "understands_recording",
        "understands_evidence_boundary",
        "agrees_to_participate",
    ):
        if consent.get(field) is not True:
            raise SopError(f"adaptive-grill consent is incomplete: {field}")
    exchanges = log.get("exchanges")
    if not isinstance(exchanges, list) or not exchanges:
        raise SopError("adaptive-grill requires at least one recorded exchange")
    exchange_ids: set[str] = set()
    for index, raw in enumerate(exchanges, 1):
        exchange = require_mapping_fields(
            raw,
            (
                "exchange_id",
                "topic",
                "ai_question",
                "human_answer",
                "answer_classification",
                "evidence_type",
            ),
            f"adaptive-grill exchange {index}",
        )
        exchange_id = str(exchange["exchange_id"]).strip()
        if not exchange_id or exchange_id in exchange_ids:
            raise SopError("adaptive-grill exchange IDs must be non-empty and unique")
        exchange_ids.add(exchange_id)
        if not str(exchange["ai_question"]).strip() or not str(exchange["human_answer"]).strip():
            raise SopError(f"adaptive-grill exchange {exchange_id} has a blank question or answer")
        classifications = exchange["answer_classification"]
        if not isinstance(classifications, list) or not classifications:
            raise SopError(f"adaptive-grill exchange {exchange_id} lacks answer classification")
        if str(exchange["evidence_type"]) not in ADAPTIVE_GRILL_EVIDENCE_TYPES:
            raise SopError(f"adaptive-grill exchange {exchange_id} has invalid evidence_type")
    question_count = log.get("question_count")
    if not isinstance(question_count, int) or question_count != len(exchanges):
        raise SopError("adaptive-grill question_count must match the recorded exchanges")
    if question_count > int(collaboration["max_questions"]):
        raise SopError("adaptive-grill exceeded the assignment max_questions")
    coverage = log.get("coverage")
    if not isinstance(coverage, dict):
        raise SopError("adaptive-grill coverage is missing")
    incomplete_topics = [
        str(topic)
        for topic in collaboration["required_topics"]
        if coverage.get(str(topic).replace("-", "_")) != "complete"
    ]
    if incomplete_topics:
        raise SopError(
            f"adaptive-grill required topics are incomplete: {', '.join(incomplete_topics)}"
        )
    gaps = log.get("gaps", [])
    if not isinstance(gaps, list):
        raise SopError("adaptive-grill gaps must be a list")
    if any(isinstance(gap, dict) and gap.get("blocking") is True for gap in gaps):
        raise SopError("adaptive-grill has unresolved blocking gaps")
    confirmations = log.get("confirmations")
    if not isinstance(confirmations, list):
        raise SopError("adaptive-grill confirmations must be a list")
    confirmed_subjects = {
        str(item.get("subject"))
        for item in confirmations
        if isinstance(item, dict) and item.get("status") == "confirmed"
    }
    required_confirmations = set(str(item) for item in collaboration["required_confirmations"])
    if not required_confirmations.issubset(confirmed_subjects):
        raise SopError("adaptive-grill log is missing mandatory human confirmations")
    summary_confirmations = summary.get("required_confirmations")
    if not isinstance(summary_confirmations, dict) or any(
        summary_confirmations.get(subject) != "confirmed"
        for subject in required_confirmations
    ):
        raise SopError("adaptive-grill summary confirmations are incomplete")
    problem = summary.get("problem_definition")
    if (
        not isinstance(problem, dict)
        or not str(problem.get("statement", "")).strip()
        or problem.get("confirmation") != "confirmed"
        or not isinstance(problem.get("evidence_refs"), list)
        or not problem.get("evidence_refs")
    ):
        raise SopError("adaptive-grill confirmed problem definition is incomplete")
    for field in ("target_users", "scenarios", "p0_scope"):
        value = summary.get(field)
        if not isinstance(value, list) or not value:
            raise SopError(f"adaptive-grill summary {field} must contain confirmed content")
    for field in (
        "p1_scope",
        "excluded_scope",
        "risks",
        "counterexamples",
        "unknowns",
        "unresolved_disagreements",
        "member_judgments",
        "ai_inferences",
    ):
        if not isinstance(summary.get(field), list):
            raise SopError(f"adaptive-grill summary {field} must be a list")


def validate_submission(
    submission_dir: Path,
    assignment_path: Path,
    member_id: str,
    require_submitted: bool = False,
    require_confirmation: bool = True,
    check_confirmation: bool = True,
) -> tuple[dict[str, Any], dict[str, int]]:
    assignment = validate_assignment(assignment_path, member_id)
    assignment_acceptance = validate_assignment_acceptance(
        assignment_path, assignment
    )
    expected_root = (stage_dir_for(assignment_path) / "submissions" / member_id).resolve()
    submission_dir = submission_dir.resolve()
    if not submission_dir.is_relative_to(expected_root):
        raise SopError("Submission directory is outside the current member-owned path")
    required_outputs = required_output_names(assignment)
    missing_files = [name for name in required_outputs if not (submission_dir / name).is_file()]
    if missing_files:
        raise SopError(f"Missing submission files: {', '.join(missing_files)}")

    manifest = load_data(submission_dir / "submission-manifest.yaml")
    matches = {
        "assignment_id": assignment["assignment_id"],
        "assignment_version": str(assignment["assignment_version"]),
        "member_id": member_id,
        "git_branch": assignment["git_branch"],
        "main_branch": assignment["main_branch"],
        "stage_id": assignment["stage_id"],
        "round_id": assignment["round_id"],
        "assignment_kind": assignment["assignment_kind"],
        "collaboration_model": assignment["collaboration_model"],
        "participation_mode": assignment["participation_mode"],
        "review_of_round": assignment.get("review_of_round"),
        "protocol_version": str(assignment["protocol_version"]),
        "project_schema_version": str(assignment["project_schema_version"]),
        "baseline_version": str(assignment["baseline_version"]),
    }
    confirmation_policy = None
    if requires_submission_confirmation(assignment):
        matches["human_owner"] = str(assignment["human_owner"])
        confirmation_policy = validate_submission_confirmation_policy(assignment)
    if assignment.get("task_contract_hash"):
        matches["task_contract_hash"] = assignment["task_contract_hash"]
    mismatches = [
        key for key, expected in matches.items() if str(manifest.get(key)) != str(expected)
    ]
    if confirmation_policy is not None and manifest.get(
        "submission_confirmation"
    ) != confirmation_policy:
        mismatches.append("submission_confirmation")
    if manifest.get("assignment_acceptance") != assignment_acceptance:
        mismatches.append("assignment_acceptance")
    if mismatches:
        raise SopError(f"Manifest does not match assignment: {', '.join(mismatches)}")
    if assignment.get("task_contract_hash"):
        expected_contract = {
            "task_source": assignment["task_source"],
            "objective": assignment["objective"],
            "scope": assignment["scope"],
            "input_refs": assignment["input_refs"],
            "deliverables": assignment["deliverables"],
            "acceptance_criteria": assignment["acceptance_criteria"],
            "constraints": assignment["constraints"],
            "dependencies": assignment["dependencies"],
            "priority": assignment["priority"],
            "coordinator_notes": assignment["coordinator_notes"],
        }
        if version_tuple(str(assignment.get("minimum_skill_version", "1.0.0"))) >= version_tuple("1.7.4"):
            expected_contract["human_collaboration"] = validate_human_collaboration(assignment)
        if requires_submission_confirmation(assignment):
            expected_contract["submission_confirmation"] = (
                validate_submission_confirmation_policy(assignment)
            )
        if version_tuple(str(assignment.get("minimum_skill_version", "1.0.0"))) >= version_tuple("1.8.0"):
            expected_contract["ai_dialogue_collaboration"] = validate_ai_dialogue_policy(
                assignment
            )
            expected_contract["required_member_skill"] = assignment["required_member_skill"]
        if requires_assignment_acceptance(assignment):
            expected_contract["acceptance_policy"] = validate_assignment_acceptance_policy(
                assignment
            )
        if manifest.get("task_contract") != expected_contract:
            raise SopError("Manifest task_contract does not match the confirmed assignment")
    if manifest.get("human_collaboration") != validate_human_collaboration(assignment):
        raise SopError("Manifest human_collaboration does not match the assignment")
    dialogue_policy = validate_ai_dialogue_policy(assignment)
    if manifest.get("ai_dialogue_collaboration") != dialogue_policy:
        raise SopError("Manifest AI dialogue policy does not match the assignment")
    if dialogue_policy is not None:
        summary_path = submission_dir / "ai-dialogue-summary.yaml"
        if not summary_path.is_file():
            raise SopError("Missing auxiliary ai-dialogue-summary.yaml")
        validate_ai_dialogue_summary(load_data(summary_path), assignment, member_id)
    if require_submitted and manifest.get("status") != "submitted":
        raise SopError("Submission manifest is not in submitted state")

    content_index = validate_content_index(submission_dir, assignment, manifest)
    if check_confirmation:
        validate_human_submission_confirmation(
            submission_dir,
            assignment,
            manifest,
            str(content_index["document_hash"]),
            require_confirmed=require_confirmation,
        )

    main_text = (submission_dir / "main-output.md").read_text(encoding="utf-8").strip()
    if len(main_text) < 120:
        raise SopError("main-output.md is too short to be a complete submission")
    if "[[FILL]]" in main_text:
        raise SopError("main-output.md still contains [[FILL]] placeholders")

    kind = str(assignment["assignment_kind"])
    if kind == "requirement-analysis":
        validate_user_stories(main_text)
    validate_adaptive_grill(submission_dir, assignment)
    if kind == "function-design" and ("REQ-" not in main_text or "AC-REQ-" not in main_text):
        raise SopError("function-design must link functions to REQ and AC IDs")

    sources = read_list(submission_dir / "source-ledger.yaml", "sources")
    validate_sources(sources, kind)
    assumptions = read_list(submission_dir / "assumptions-and-gaps.yaml", "assumptions")
    read_list(submission_dir / "assumptions-and-gaps.yaml", "gaps")
    risks = read_list(submission_dir / "risks-and-new-requirements.yaml", "risks")
    new_requirements = read_list(
        submission_dir / "risks-and-new-requirements.yaml", "new_requirements"
    )
    validate_risks_and_requirements(risks, new_requirements)
    counts = {
        "sources_count": len(sources),
        "assumptions_count": len(assumptions),
        "risks_count": len(risks),
        "new_requirements_count": len(new_requirements),
    }
    return manifest, counts


def cmd_validate(args: argparse.Namespace) -> None:
    assignment_path = Path(args.assignment).resolve()
    assignment = validate_assignment(assignment_path, args.member_id)
    validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    manifest, counts = validate_submission(
        Path(args.submission), assignment_path, args.member_id
    )
    print(
        json.dumps(
            {
                "valid": True,
                "status": manifest.get("status"),
                "submission_confirmation": manifest.get(
                    "human_submission_confirmation",
                    {"status": "legacy-not-required"},
                ),
                "member_cli": {"skill_version": SKILL_VERSION, "build_id": BUILD_ID},
                **counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_index_content(args: argparse.Namespace) -> None:
    submission_dir = Path(args.submission).resolve()
    assignment_path = Path(args.assignment).resolve()
    assignment = validate_assignment(assignment_path, args.member_id)
    validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    expected = output_dir_for(assignment_path, assignment)
    if submission_dir != expected:
        raise SopError("Submission directory does not match the assignment output path")
    manifest = load_data(submission_dir / "submission-manifest.yaml")
    if manifest.get("status") == "submitted":
        raise SopError("Submitted content is immutable; request a new assignment version")
    index = update_content_index(submission_dir, assignment)
    print(json.dumps(index, ensure_ascii=False, indent=2))


def cmd_prepare_confirmation(args: argparse.Namespace) -> None:
    submission_dir = Path(args.submission).resolve()
    assignment_path = Path(args.assignment).resolve()
    assignment = validate_assignment(assignment_path, args.member_id)
    if not requires_submission_confirmation(assignment):
        raise SopError("This legacy assignment does not use submission confirmation")
    validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    expected = output_dir_for(assignment_path, assignment)
    if submission_dir != expected:
        raise SopError("Submission directory does not match the assignment output path")
    current_manifest = load_data(submission_dir / "submission-manifest.yaml")
    if current_manifest.get("status") == "submitted":
        raise SopError("Submitted content is immutable; request a new assignment version")
    position = str(args.position).strip()
    statement = str(args.position_statement).strip()
    if position not in SUBMISSION_CONFIRMATION_POSITIONS:
        raise SopError(f"Invalid human owner personal stance: {position}")
    if not statement:
        raise SopError("Human owner personal stance statement cannot be blank")
    update_content_index(submission_dir, assignment)
    manifest, _ = validate_submission(
        submission_dir,
        assignment_path,
        args.member_id,
        require_confirmation=False,
        check_confirmation=False,
    )
    content_index = load_data(submission_dir / "content-block-index.yaml")
    document_hash = str(content_index["document_hash"])
    token = submission_confirmation_token(
        assignment,
        str(manifest["submission_id"]),
        document_hash,
        position,
        statement,
    )
    record = new_submission_confirmation(assignment, str(manifest["submission_id"]))
    record.update(
        {
            "status": "awaiting-human-confirmation",
            "document_hash": document_hash,
            "personal_stance": {"code": position, "statement": statement},
            "prepared_at": now_iso(),
            "confirmation_token": token,
        }
    )
    dump_data(submission_dir / SUBMISSION_CONFIRMATION_OUTPUT, record)
    manifest["human_submission_confirmation"] = confirmation_manifest_summary(record)
    dump_data(submission_dir / "submission-manifest.yaml", manifest)
    validate_submission(
        submission_dir,
        assignment_path,
        args.member_id,
        require_confirmation=False,
    )
    print(
        json.dumps(
            {
                "status": "awaiting-human-confirmation",
                "human_owner": assignment["human_owner"],
                "source_file": "main-output.md",
                "document_hash": document_hash,
                "personal_stance": record["personal_stance"],
                "confirmation_token": token,
                "confirmation_statement": (
                    "I confirm the displayed main-output.md body and hash, and the recorded "
                    "personal stance. This authorizes only this member contribution submission "
                    "and is not a Gate approval, merge approval, baseline freeze, development "
                    "approval, or release approval."
                ),
                "next_action": (
                    "Show this exact preview to the registered human_owner. Run "
                    "confirm-submission only after that owner explicitly confirms it."
                ),
                "member_cli": {"skill_version": SKILL_VERSION, "build_id": BUILD_ID},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_confirm_submission(args: argparse.Namespace) -> None:
    submission_dir = Path(args.submission).resolve()
    assignment_path = Path(args.assignment).resolve()
    assignment = validate_assignment(assignment_path, args.member_id)
    if not requires_submission_confirmation(assignment):
        raise SopError("This legacy assignment does not use submission confirmation")
    validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    expected = output_dir_for(assignment_path, assignment)
    if submission_dir != expected:
        raise SopError("Submission directory does not match the assignment output path")
    manifest = load_data(submission_dir / "submission-manifest.yaml")
    if manifest.get("status") == "submitted":
        raise SopError("Submitted content is immutable; request a new assignment version")
    validate_submission(
        submission_dir,
        assignment_path,
        args.member_id,
        require_confirmation=False,
    )
    record = load_data(submission_dir / SUBMISSION_CONFIRMATION_OUTPUT)
    if record.get("status") != "awaiting-human-confirmation":
        raise SopError("Submission confirmation is not awaiting the human owner")
    if str(args.confirmed_by).strip() != str(assignment["human_owner"]):
        raise SopError("--confirmed-by must match the registered human_owner")
    if str(args.document_hash).strip() != str(record.get("document_hash", "")):
        raise SopError("--document-hash does not match the prepared confirmation preview")
    if str(args.confirmation_token).strip() != str(record.get("confirmation_token", "")):
        raise SopError("--confirmation-token does not match the prepared preview")
    record.update(
        {
            "status": "confirmed",
            "confirmed_subjects": {
                "exact_document_hash": True,
                "personal_stance": True,
            },
            "confirmed_by": str(assignment["human_owner"]),
            "confirmed_at": now_iso(),
            "confirmation_method": "explicit-human-owner",
        }
    )
    dump_data(submission_dir / SUBMISSION_CONFIRMATION_OUTPUT, record)
    manifest["human_submission_confirmation"] = confirmation_manifest_summary(record)
    dump_data(submission_dir / "submission-manifest.yaml", manifest)
    validate_submission(submission_dir, assignment_path, args.member_id)
    print(
        json.dumps(
            {
                "confirmed": True,
                "human_owner": assignment["human_owner"],
                "document_hash": record["document_hash"],
                "personal_stance": record["personal_stance"],
                "gate_effect": "none",
                "member_cli": {"skill_version": SKILL_VERSION, "build_id": BUILD_ID},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_submit(args: argparse.Namespace) -> None:
    submission_dir = Path(args.submission).resolve()
    assignment_path = Path(args.assignment).resolve()
    current_manifest = load_data(submission_dir / "submission-manifest.yaml")
    if current_manifest.get("status") == "submitted":
        raise SopError("Submission is already submitted; request a new assignment version")
    assignment = validate_assignment(assignment_path, args.member_id)
    validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    update_content_index(submission_dir, assignment)
    manifest, counts = validate_submission(
        submission_dir, assignment_path, args.member_id
    )
    manifest.update(counts)
    manifest["status"] = "submitted"
    manifest["submitted_at"] = now_iso()
    dump_data(submission_dir / "submission-manifest.yaml", manifest)
    validate_submission(submission_dir, assignment_path, args.member_id, require_submitted=True)
    print(
        json.dumps(
            {
                "submitted": True,
                "submission": str(submission_dir),
                "human_submission_confirmation": manifest.get(
                    "human_submission_confirmation",
                    {"status": "legacy-not-required"},
                ),
                "member_cli": {"skill_version": SKILL_VERSION, "build_id": BUILD_ID},
            },
            ensure_ascii=False,
        )
    )


def cmd_workspace_check(args: argparse.Namespace) -> None:
    assignment_path = Path(args.assignment).resolve()
    assignment = validate_assignment(assignment_path, args.member_id)
    result = validate_git_workspace(
        assignment_path,
        assignment,
        remote=args.remote,
        fetch=args.fetch,
        require_assignment_sync=True,
        detached_validation=args.detached_validation,
    )
    print(
        json.dumps(
            {
                "valid": True,
                "member_cli": {"skill_version": SKILL_VERSION, "build_id": BUILD_ID},
                "assignment_acceptance": validate_assignment_acceptance(
                    assignment_path, assignment, require_accepted=False
                ),
                **result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in (
        ("workspace-check", cmd_workspace_check),
        ("inspect", cmd_inspect),
        ("init", cmd_init),
    ):
        command = sub.add_parser(name)
        command.add_argument("assignment")
        command.add_argument("--member-id", required=True)
        command.add_argument("--remote", default="origin")
        command.add_argument("--fetch", action="store_true")
        command.add_argument("--detached-validation", action="store_true", help=argparse.SUPPRESS)
        command.set_defaults(handler=handler)
    accept = sub.add_parser("accept-assignment")
    accept.add_argument("assignment")
    accept.add_argument("--member-id", required=True)
    accept.add_argument("--remote", default="origin")
    accept.add_argument("--fetch", action="store_true")
    accept.add_argument("--detached-validation", action="store_true", help=argparse.SUPPRESS)
    accept.set_defaults(handler=cmd_accept_assignment)
    for name, handler in (
        ("index-content", cmd_index_content),
        ("validate", cmd_validate),
        ("submit", cmd_submit),
    ):
        command = sub.add_parser(name)
        command.add_argument("submission")
        command.add_argument("--assignment", required=True)
        command.add_argument("--member-id", required=True)
        command.add_argument("--remote", default="origin")
        command.add_argument("--fetch", action="store_true")
        command.add_argument("--detached-validation", action="store_true", help=argparse.SUPPRESS)
        command.set_defaults(handler=handler)
    prepare = sub.add_parser("prepare-confirmation")
    prepare.add_argument("submission")
    prepare.add_argument("--assignment", required=True)
    prepare.add_argument("--member-id", required=True)
    prepare.add_argument("--position", choices=SUBMISSION_CONFIRMATION_POSITIONS, required=True)
    prepare.add_argument("--position-statement", required=True)
    prepare.add_argument("--remote", default="origin")
    prepare.add_argument("--fetch", action="store_true")
    prepare.add_argument("--detached-validation", action="store_true", help=argparse.SUPPRESS)
    prepare.set_defaults(handler=cmd_prepare_confirmation)
    confirm = sub.add_parser("confirm-submission")
    confirm.add_argument("submission")
    confirm.add_argument("--assignment", required=True)
    confirm.add_argument("--member-id", required=True)
    confirm.add_argument("--confirmed-by", required=True)
    confirm.add_argument("--document-hash", required=True)
    confirm.add_argument("--confirmation-token", required=True)
    confirm.add_argument("--remote", default="origin")
    confirm.add_argument("--fetch", action="store_true")
    confirm.add_argument("--detached-validation", action="store_true", help=argparse.SUPPRESS)
    confirm.set_defaults(handler=cmd_confirm_submission)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.handler(args)
        return 0
    except SopError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

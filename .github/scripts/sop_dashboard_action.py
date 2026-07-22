#!/usr/bin/env python3
"""Authorize a low-risk SOP dashboard request and emit an inert action plan.

The module deliberately does not execute the plan or mutate repository state.  A
trusted GitHub Actions workflow is expected to validate this plan and map its
``operation`` to an allow-listed implementation.

All ``.yaml`` inputs handled here must contain JSON.  This keeps the script in
the Python standard library and makes parsing deterministic in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NoReturn


SCHEMA_VERSION = "1.0"
SUPPORTED_ACTIONS = frozenset(
    {"notification-test", "refresh-state", "rerun-validation", "task-reminder"}
)
REMINDABLE_STATUSES = frozenset({"missing", "blocked"})
REMINDABLE_VALIDATIONS = frozenset({"not-submitted", "invalid"})
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
ASSIGNMENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
MAX_REMINDER_DETAIL_LENGTH = 500


class ActionDenied(RuntimeError):
    """A safe, expected refusal that can be returned to the dashboard."""

    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def deny(code: str, message: str, **details: Any) -> NoReturn:
    raise ActionDenied(code, message, **details)


def load_json_yaml(path: Path, label: str) -> dict[str, Any]:
    """Load a JSON-compatible YAML file as an object."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        deny("input-not-found", f"{label} file does not exist", path=str(path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        deny(
            "invalid-json-input",
            f"{label} must be a readable JSON-compatible YAML file",
            path=str(path),
            reason=str(exc),
        )
    if not isinstance(value, dict):
        deny("invalid-json-input", f"{label} root must be an object", path=str(path))
    return value


def require_sha(value: str, label: str) -> str:
    normalized = str(value or "").strip().lower()
    if not SHA_RE.fullmatch(normalized):
        deny("invalid-request", f"{label} must be an exact 40-character commit SHA")
    return normalized


def state_revision(state: dict[str, Any]) -> int:
    tracking = state.get("submission_tracking")
    if not isinstance(tracking, dict):
        deny("invalid-project-state", "submission_tracking must be an object")
    revision = tracking.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        deny("invalid-project-state", "submission_tracking.revision must be a non-negative integer")
    return revision


def reminder_detail(value: str | None) -> str:
    normalized = str(value or "").strip()
    if len(normalized) > MAX_REMINDER_DETAIL_LENGTH:
        deny(
            "invalid-reminder-detail",
            f"reminder_detail must not exceed {MAX_REMINDER_DETAIL_LENGTH} characters",
        )
    if CONTROL_CHAR_RE.search(normalized):
        deny(
            "invalid-reminder-detail",
            "reminder_detail must not contain control characters",
        )
    return normalized


def authorize(
    policy: dict[str, Any], action: str, actor: str
) -> tuple[list[str], dict[str, Any]]:
    if policy.get("enabled") is not True:
        deny("dashboard-disabled", "dashboard actions are disabled by policy")

    actors = policy.get("actors")
    if not isinstance(actors, dict):
        deny("invalid-policy", "policy.actors must be an object")
    actor_policy = actors.get(actor)
    if not isinstance(actor_policy, dict) or actor_policy.get("enabled") is not True:
        deny("actor-not-authorized", "GitHub actor is not enabled", actor=actor)
    roles = actor_policy.get("roles")
    if not isinstance(roles, list) or not roles or not all(
        isinstance(role, str) and role for role in roles
    ):
        deny("invalid-policy", "enabled actor must have a non-empty roles list", actor=actor)

    actions = policy.get("actions")
    if not isinstance(actions, dict):
        deny("invalid-policy", "policy.actions must be an object")
    action_policy = actions.get(action)
    if not isinstance(action_policy, dict):
        deny("action-not-authorized", "action is not enabled by policy", action=action)
    if action_policy.get("enabled") is not True:
        deny("action-not-authorized", "action is disabled by policy", action=action)
    if action_policy.get("risk") != "low":
        deny(
            "risk-not-supported",
            "this engine only authorizes low-risk actions",
            action=action,
        )
    allowed_roles = action_policy.get("allowed_roles")
    if not isinstance(allowed_roles, list) or not all(
        isinstance(role, str) and role for role in allowed_roles
    ):
        deny("invalid-policy", "action.allowed_roles must be a list of role names")
    if not set(roles).intersection(allowed_roles):
        deny(
            "actor-not-authorized",
            "actor roles do not permit this action",
            actor=actor,
            action=action,
        )
    return sorted(set(roles)), action_policy


def find_assignment(root: Path, assignment_id: str) -> tuple[Path, dict[str, Any]]:
    """Resolve one exact assignment from the trusted dispatch directories."""

    if not ASSIGNMENT_ID_RE.fullmatch(assignment_id):
        deny("invalid-assignment-id", "assignment_id contains unsafe characters")
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in root.glob("sop/stages/*/dispatch/*.yaml"):
        assignment = load_json_yaml(path, "assignment")
        if str(assignment.get("assignment_id", "")) == assignment_id:
            matches.append((path, assignment))
    if len(matches) != 1:
        deny(
            "assignment-not-unique",
            "expected exactly one assignment with the requested ID",
            assignment_id=assignment_id,
            match_count=len(matches),
        )
    return matches[0]


def find_state_record(
    state: dict[str, Any], assignment: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    assignment_id = str(assignment.get("assignment_id", ""))
    stage_id = str(assignment.get("stage_id", ""))
    if not assignment_id or not stage_id:
        deny("invalid-assignment", "assignment requires assignment_id and stage_id")
    tracking = state.get("submission_tracking")
    stages = tracking.get("stages") if isinstance(tracking, dict) else None
    stage = stages.get(stage_id) if isinstance(stages, dict) else None
    records = stage.get("records") if isinstance(stage, dict) else None
    record = records.get(assignment_id) if isinstance(records, dict) else None
    if not isinstance(record, dict):
        deny(
            "state-record-not-found",
            "project state has no trusted record for the assignment",
            assignment_id=assignment_id,
            stage_id=stage_id,
        )
    if str(record.get("assignment_id", "")) != assignment_id:
        deny("invalid-project-state", "state record assignment_id does not match its key")
    if str(record.get("member_id", "")) != str(assignment.get("member_id", "")):
        deny("invalid-project-state", "state record member_id does not match assignment")
    if str(record.get("stage_id", stage_id)) != stage_id:
        deny("invalid-project-state", "state record stage_id does not match assignment")
    return stage_id, record


def build_action_plan(
    *,
    root: Path,
    policy_path: Path,
    project_state_path: Path,
    action: str,
    actor: str,
    base_main_sha: str,
    current_main_sha: str,
    base_revision: int,
    assignment_id: str | None = None,
    reminder_detail_value: str | None = None,
) -> dict[str, Any]:
    """Validate a request and return a non-executable, allow-listed action plan."""

    if action not in SUPPORTED_ACTIONS:
        deny("unsupported-action", "action is not supported", action=action)
    actor = str(actor or "").strip()
    if not actor:
        deny("invalid-request", "GitHub actor is required")
    if isinstance(base_revision, bool) or not isinstance(base_revision, int) or base_revision < 0:
        deny("invalid-request", "base_revision must be a non-negative integer")

    base_sha = require_sha(base_main_sha, "base_main_sha")
    current_sha = require_sha(current_main_sha, "current_main_sha")
    policy = load_json_yaml(policy_path, "dashboard policy")
    state = load_json_yaml(project_state_path, "project state")
    current_revision = state_revision(state)
    roles, action_policy = authorize(policy, action, actor)
    detail = reminder_detail(reminder_detail_value)

    if base_sha != current_sha:
        deny(
            "stale-main-sha",
            "dashboard request was based on an older main commit",
            base_main_sha=base_sha,
            current_main_sha=current_sha,
        )
    if base_revision != current_revision:
        deny(
            "stale-project-revision",
            "dashboard request was based on an older project-state revision",
            base_revision=base_revision,
            current_revision=current_revision,
        )

    operation: dict[str, Any]
    target: dict[str, Any]
    if action == "refresh-state":
        if assignment_id:
            deny("invalid-request", "refresh-state does not accept assignment_id")
        if detail:
            deny("invalid-request", "refresh-state does not accept reminder_detail")
        operation = {
            "name": "refresh-project-state",
            "inputs": {"validate_remote": True},
        }
        target = {"type": "project", "project_id": state.get("project_id")}
    elif action == "rerun-validation":
        if assignment_id:
            deny("invalid-request", "rerun-validation does not accept assignment_id")
        if detail:
            deny("invalid-request", "rerun-validation does not accept reminder_detail")
        stage_id = str(state.get("current_stage", "")).strip()
        if not stage_id:
            deny("invalid-project-state", "current_stage is required for rerun-validation")
        operation = {
            "name": "refresh-project-state",
            "inputs": {"validate_remote": True, "stage_id": stage_id},
        }
        target = {"type": "stage", "stage_id": stage_id}
    elif action == "notification-test":
        if assignment_id:
            deny("invalid-request", "notification-test does not accept assignment_id")
        if detail:
            deny("invalid-request", "notification-test does not accept reminder_detail")
        operation = {
            "name": "notification-test",
            "inputs": {},
        }
        target = {
            "type": "notification-channel",
            "channel": "dingtalk",
            "environment": "sop-notifications",
        }
    else:
        if not assignment_id:
            deny("invalid-request", "task-reminder requires assignment_id")
        assignment_path, assignment = find_assignment(root, assignment_id)
        stage_id, record = find_state_record(state, assignment)
        status = str(record.get("status", "")).strip()
        validation = str(record.get("validation_status", "")).strip()
        if status not in REMINDABLE_STATUSES and validation not in REMINDABLE_VALIDATIONS:
            deny(
                "task-not-remindable",
                "task state does not allow a reminder",
                assignment_id=assignment_id,
                status=status,
                validation_status=validation,
            )
        relative_path = assignment_path.relative_to(root).as_posix()
        operation = {
            "name": "task-reminder",
            "inputs": {
                "assignment_id": assignment_id,
                "reminder_detail": detail,
            },
        }
        target = {
            "type": "assignment",
            "assignment_id": assignment_id,
            "assignment_path": relative_path,
            "stage_id": stage_id,
            "member_id": assignment.get("member_id"),
            "status": status,
            "validation_status": validation,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "decision": "approved",
        "action": action,
        "risk": action_policy.get("risk"),
        "actor": actor,
        "actor_roles": roles,
        "preconditions": {
            "base_main_sha": base_sha,
            "current_main_sha": current_sha,
            "base_revision": base_revision,
            "current_revision": current_revision,
        },
        "target": target,
        "plan": {
            "executor": "trusted-github-actions-workflow",
            "operation": operation,
            "execution_mode": "plan-only",
            "engine_executed": False,
        },
    }


class JsonArgumentParser(argparse.ArgumentParser):
    """Keep command-line refusals machine-readable for workflow consumers."""

    def error(self, message: str) -> NoReturn:
        deny("invalid-request", message)


def parser() -> argparse.ArgumentParser:
    result = JsonArgumentParser(
        description="Authorize a low-risk SOP dashboard request and emit JSON only."
    )
    result.add_argument("--action", required=True, choices=sorted(SUPPORTED_ACTIONS))
    result.add_argument("--actor", default=os.environ.get("GITHUB_ACTOR", ""))
    result.add_argument("--base-main-sha", required=True)
    result.add_argument(
        "--current-main-sha",
        default=os.environ.get("GITHUB_SHA", ""),
        help="Trusted current main SHA; defaults to GITHUB_SHA.",
    )
    result.add_argument("--base-revision", required=True, type=int)
    result.add_argument("--assignment-id")
    result.add_argument("--reminder-detail", default="")
    result.add_argument("--policy", default="sop/dashboard-policy.yaml")
    result.add_argument("--project-state", default="sop/project-state.yaml")
    result.add_argument("--root", default=".")
    return result


def emit(value: dict[str, Any], stream: Any = None) -> None:
    if stream is None:
        stream = sys.stdout
    json.dump(value, stream, ensure_ascii=False, sort_keys=True)
    stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        root = Path(args.root).resolve()
        policy_path = (root / args.policy).resolve()
        project_state_path = (root / args.project_state).resolve()
        plan = build_action_plan(
            root=root,
            policy_path=policy_path,
            project_state_path=project_state_path,
            action=args.action,
            actor=args.actor,
            base_main_sha=args.base_main_sha,
            current_main_sha=args.current_main_sha,
            base_revision=args.base_revision,
            assignment_id=args.assignment_id,
            reminder_detail_value=args.reminder_detail,
        )
    except ActionDenied as exc:
        emit(
            {
                "schema_version": SCHEMA_VERSION,
                "decision": "denied",
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            }
        )
        return 2
    emit(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Member-side development delivery CLI for SOP V2.0."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SKILL_NAME = "ai-sop-member"
SKILL_VERSION = "2.0.0"
BUILD_ID = "member-dev-cli-2.0.0-v1"
SCHEMA_VERSION = "2.0"


class CliError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot read JSON-compatible YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CliError(f"document must be an object: {path}")
    return value


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def digest(value) -> str:
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        raw = str(value).replace("\r\n", "\n")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True)
    if check and result.returncode:
        raise CliError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def repo_root() -> Path:
    return Path(git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()


def rel(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError as exc:
        raise CliError(f"path is outside repository: {path}") from exc


def require_assignment(path: Path, member_id: str) -> tuple[dict, Path]:
    data = load(path)
    required = ("assignment_id", "assignment_version", "member_id", "human_owner", "goal", "allowed_scope", "required_checks", "git")
    missing = [key for key in required if key not in data]
    if missing:
        raise CliError(f"assignment missing fields: {', '.join(missing)}")
    if data.get("project_schema_version") != SCHEMA_VERSION or data.get("stage_id") != "04-development":
        raise CliError("assignment is not a SOP V2.0 development assignment")
    if data["member_id"] != member_id:
        raise CliError("member-id does not match assignment")
    expected = {"name": SKILL_NAME, "version": SKILL_VERSION, "build_id": BUILD_ID}
    if data.get("required_member_skill") != expected:
        raise CliError(f"required member skill must be exactly {expected}")
    if data.get("dispatch_confirmation", {}).get("status") != "confirmed":
        raise CliError("assignment dispatch is not confirmed")
    repo = repo_root()
    if git(repo, "branch", "--show-current") != data["git"].get("working_branch"):
        raise CliError("current branch does not match assigned working branch")
    base = data["git"].get("base_commit", "")
    git(repo, "cat-file", "-e", f"{base}^{{commit}}")
    return data, repo


def evidence_path(repo: Path, assignment: dict) -> Path:
    return repo / "sop" / "stages" / "04-development" / "submissions" / assignment["member_id"] / f"{assignment['assignment_id']}-v{assignment['assignment_version']}"


def acceptance_path(repo: Path, assignment: dict) -> Path:
    return repo / "sop" / "stages" / "04-development" / "acceptances" / assignment["member_id"] / f"{assignment['assignment_id']}-v{assignment['assignment_version']}.yaml"


def cmd_accept(args) -> dict:
    assignment, repo = require_assignment(args.assignment, args.member_id)
    receipt = {
        "project_schema_version": SCHEMA_VERSION,
        "assignment_id": assignment["assignment_id"],
        "assignment_version": assignment["assignment_version"],
        "member_id": args.member_id,
        "human_owner": assignment["human_owner"],
        "assignment_hash": digest(assignment),
        "working_branch": assignment["git"]["working_branch"],
        "base_commit": assignment["git"]["base_commit"],
        "member_skill": {"name": SKILL_NAME, "version": SKILL_VERSION, "build_id": BUILD_ID},
        "status": "accepted",
        "gate_effect": "none",
        "accepted_at": now(),
    }
    target = acceptance_path(repo, assignment)
    save(target, receipt)
    return {"status": "accepted", "acceptance_path": rel(repo, target)}


def require_acceptance(repo: Path, assignment: dict) -> dict:
    path = acceptance_path(repo, assignment)
    if not path.exists():
        raise CliError("assignment has not been explicitly accepted")
    receipt = load(path)
    if receipt.get("status") != "accepted" or receipt.get("assignment_hash") != digest(assignment):
        raise CliError("assignment acceptance is stale")
    return receipt


def cmd_init(args) -> dict:
    assignment, repo = require_assignment(args.assignment, args.member_id)
    require_acceptance(repo, assignment)
    target = evidence_path(repo, assignment)
    target.mkdir(parents=True, exist_ok=True)
    placeholders = {
        "implementation-plan.md": "# Implementation plan\n\n[[FILL]]\n",
        "test-plan.md": "# Test plan\n\n[[FILL]]\n",
        "completion-report.md": "# Completion report\n\n[[FILL]]\n",
    }
    for name, content in placeholders.items():
        path = target / name
        if not path.exists():
            path.write_text(content, encoding="utf-8")
    manifest = target / "development-manifest.yaml"
    if not manifest.exists():
        save(manifest, {
            "project_schema_version": SCHEMA_VERSION,
            "assignment_id": assignment["assignment_id"],
            "assignment_version": assignment["assignment_version"],
            "member_id": args.member_id,
            "assignment_hash": digest(assignment),
            "status": "in-progress",
            "checks": {},
            "created_at": now(),
        })
    confirmation = target / "development-submission-confirmation.yaml"
    if not confirmation.exists():
        save(confirmation, {"status": "not-prepared"})
    return {"status": "initialized", "submission_dir": rel(repo, target)}


def context(args) -> tuple[dict, Path, Path, dict]:
    assignment, repo = require_assignment(args.assignment, args.member_id)
    require_acceptance(repo, assignment)
    evidence = args.evidence.resolve()
    if evidence != evidence_path(repo, assignment).resolve():
        raise CliError("submission directory does not match assignment")
    manifest_path = evidence / "development-manifest.yaml"
    if not manifest_path.exists():
        raise CliError("development submission is not initialized")
    return assignment, repo, evidence, load(manifest_path)


def cmd_record_check(args) -> dict:
    assignment, repo, evidence, manifest = context(args)
    if args.name not in assignment["required_checks"]:
        raise CliError("check is not declared in required_checks")
    manifest.setdefault("checks", {})[args.name] = {
        "status": args.status, "command": args.command, "recorded_at": now()
    }
    save(evidence / "development-manifest.yaml", manifest)
    return {"status": "recorded", "check": args.name}


def ensure_documents(evidence: Path) -> None:
    for name in ("implementation-plan.md", "test-plan.md", "completion-report.md"):
        path = evidence / name
        if not path.exists() or not path.read_text(encoding="utf-8").strip() or "[[FILL]]" in path.read_text(encoding="utf-8"):
            raise CliError(f"required evidence is incomplete: {name}")


def within(path: str, scope: str) -> bool:
    scope = scope.replace("\\", "/").rstrip("/")
    return path == scope or path.startswith(scope + "/")


def validate_scope(repo: Path, assignment: dict, commit: str) -> None:
    base = assignment["git"]["base_commit"]
    git(repo, "cat-file", "-e", f"{commit}^{{commit}}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, commit], cwd=repo).returncode:
        raise CliError("implementation commit does not descend from assigned base")
    paths = git(repo, "diff", "--name-only", f"{base}..{commit}").splitlines()
    code_paths = [p for p in paths if not p.startswith("sop/stages/")]
    forbidden = assignment.get("forbidden_scope", [])
    invalid = [p for p in code_paths if any(within(p, s) for s in forbidden) or not any(within(p, s) for s in assignment["allowed_scope"])]
    if invalid:
        raise CliError("changed paths exceed assignment scope: " + ", ".join(invalid))


def cmd_prepare(args) -> dict:
    assignment, repo, evidence, manifest = context(args)
    ensure_documents(evidence)
    validate_scope(repo, assignment, args.implementation_commit)
    report_hash = digest((evidence / "completion-report.md").read_text(encoding="utf-8"))
    payload = {
        "assignment_id": assignment["assignment_id"], "member_id": args.member_id,
        "human_owner": assignment["human_owner"], "implementation_commit": args.implementation_commit,
        "completion_report_hash": report_hash, "position": args.position,
        "position_statement": args.position_statement,
    }
    token = digest(payload)
    save(evidence / "development-submission-confirmation.yaml", {
        **payload, "status": "awaiting-human-confirmation", "confirmation_token": token,
        "prepared_at": now(),
    })
    manifest["implementation_commit"] = args.implementation_commit
    manifest["status"] = "awaiting-human-confirmation"
    save(evidence / "development-manifest.yaml", manifest)
    return {"status": "awaiting-human-confirmation", "confirmation_token": token, "preview": payload}


def cmd_confirm(args) -> dict:
    assignment, repo, evidence, manifest = context(args)
    confirmation = load(evidence / "development-submission-confirmation.yaml")
    if args.confirmed_by != assignment["human_owner"]:
        raise CliError("confirmed-by must be the assigned human owner")
    if confirmation.get("status") != "awaiting-human-confirmation" or confirmation.get("confirmation_token") != args.confirmation_token:
        raise CliError("confirmation token is invalid or stale")
    current_hash = digest((evidence / "completion-report.md").read_text(encoding="utf-8"))
    if current_hash != confirmation.get("completion_report_hash"):
        raise CliError("confirmation is stale because the completion report changed")
    confirmation.update({"status": "confirmed", "confirmed_by": args.confirmed_by, "confirmed_at": now()})
    save(evidence / "development-submission-confirmation.yaml", confirmation)
    manifest["status"] = "confirmed"
    save(evidence / "development-manifest.yaml", manifest)
    return {"status": "confirmed"}


def validate_submission(args) -> tuple[dict, Path, Path, dict]:
    assignment, repo, evidence, manifest = context(args)
    ensure_documents(evidence)
    if manifest.get("assignment_hash") != digest(assignment):
        raise CliError("submission is stale because the assignment changed")
    confirmation = load(evidence / "development-submission-confirmation.yaml")
    if confirmation.get("status") != "confirmed":
        raise CliError("submission lacks human confirmation")
    report_hash = digest((evidence / "completion-report.md").read_text(encoding="utf-8"))
    if report_hash != confirmation.get("completion_report_hash"):
        raise CliError("human confirmation is stale because the completion report changed")
    commit = confirmation.get("implementation_commit", "")
    validate_scope(repo, assignment, commit)
    checks = manifest.get("checks", {})
    failed = [name for name in assignment["required_checks"] if checks.get(name, {}).get("status") != "passed"]
    if failed:
        raise CliError("required checks not passed: " + ", ".join(failed))
    return assignment, repo, evidence, manifest


def cmd_validate(args) -> dict:
    assignment, repo, evidence, manifest = validate_submission(args)
    return {"status": "valid", "assignment_id": assignment["assignment_id"], "submission_dir": rel(repo, evidence)}


def cmd_submit(args) -> dict:
    assignment, repo, evidence, manifest = validate_submission(args)
    manifest.update({"status": "submitted", "submitted_at": now()})
    save(evidence / "development-manifest.yaml", manifest)
    return {"status": "submitted", "assignment_id": assignment["assignment_id"], "submission_dir": rel(repo, evidence)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("accept-assignment"); a.add_argument("assignment", type=Path); a.add_argument("--member-id", required=True); a.set_defaults(func=cmd_accept)
    a = sub.add_parser("init"); a.add_argument("assignment", type=Path); a.add_argument("--member-id", required=True); a.set_defaults(func=cmd_init)
    for name, func in (("record-check", cmd_record_check), ("prepare-confirmation", cmd_prepare), ("confirm-submission", cmd_confirm), ("validate", cmd_validate), ("submit", cmd_submit)):
        a = sub.add_parser(name); a.add_argument("evidence", type=Path); a.add_argument("--assignment", type=Path, required=True); a.add_argument("--member-id", required=True); a.set_defaults(func=func)
        if name == "record-check":
            a.add_argument("--name", required=True); a.add_argument("--status", choices=("passed", "failed"), required=True); a.add_argument("--command", required=True)
        elif name == "prepare-confirmation":
            a.add_argument("--implementation-commit", required=True); a.add_argument("--position", choices=("confirm", "reject"), required=True); a.add_argument("--position-statement", required=True)
        elif name == "confirm-submission":
            a.add_argument("--confirmed-by", required=True); a.add_argument("--confirmation-token", required=True)
    return p


def main() -> int:
    try:
        args = parser().parse_args()
        print(json.dumps(args.func(args), ensure_ascii=False))
        return 0
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

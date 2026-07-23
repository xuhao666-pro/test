#!/usr/bin/env python3
"""Coordinator-side development, integration, and release-gate CLI for SOP V2.0."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SKILL_VERSION = "2.0.0"
BUILD_ID = "coordinator-dev-cli-2.0.0-v1"
MEMBER_SKILL = {"name": "ai-sop-member", "version": "2.0.0", "build_id": "member-dev-cli-2.0.0-v1"}
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
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True)
    if check and result.returncode:
        raise CliError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def root(path: Path) -> Path:
    repo = Path(git(path.resolve(), "rev-parse", "--show-toplevel")).resolve()
    if repo != path.resolve():
        raise CliError("repository argument must be the Git repository root")
    return repo


def relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo).as_posix()


def dev_root(repo: Path) -> Path:
    return repo / "sop" / "stages" / "04-development"


def release_root(repo: Path) -> Path:
    return repo / "sop" / "stages" / "05-release"


def dev_state_path(repo: Path) -> Path:
    return dev_root(repo) / "stage-state.yaml"


def release_state_path(repo: Path) -> Path:
    return release_root(repo) / "stage-state.yaml"


def update_project_state(repo: Path, dev: dict | None = None, release: dict | None = None) -> None:
    path = repo / "sop" / "project-state.yaml"
    state = load(path) if path.exists() else {"project_schema_version": SCHEMA_VERSION}
    if dev is not None:
        state["development_tracking"] = {
            "status": dev.get("status"), "task_counts": task_counts(dev), "updated_at": now()
        }
    if release is not None:
        state["release_tracking"] = {
            "status": release.get("status"), "g4": release.get("g4", {}).get("status"),
            "rollout_percentage": release.get("rollout", {}).get("percentage", 0),
            "g5": release.get("g5", {}).get("status"), "updated_at": now(),
        }
    save(path, state)


def task_counts(state: dict) -> dict:
    counts: dict[str, int] = {}
    for task in state.get("tasks", {}).values():
        status = task.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def cmd_init(args) -> dict:
    repo = root(args.repo)
    git(repo, "cat-file", "-e", f"{args.g3_baseline.split('@')[-1]}^{{commit}}")
    for name in ("dispatch", "acceptances", "plans", "submissions", "reviews", "integration", "blockers"):
        (dev_root(repo) / name).mkdir(parents=True, exist_ok=True)
    for name in ("gate", "rollout", "monitoring", "incidents", "retrospectives", "baseline"):
        (release_root(repo) / name).mkdir(parents=True, exist_ok=True)
    dev = {"project_schema_version": SCHEMA_VERSION, "status": "active", "g3_baseline": args.g3_baseline, "tasks": {}, "initialized_at": now()}
    release = {"project_schema_version": SCHEMA_VERSION, "status": "not-started", "g4": {"status": "not-prepared"}, "rollout": {"percentage": 0, "observation": "pending"}, "g5": {"status": "not-prepared"}, "open_incidents": 0}
    save(dev_state_path(repo), dev); save(release_state_path(repo), release)
    update_project_state(repo, dev, release)
    return {"status": "initialized", "g3_baseline": args.g3_baseline}


def require_initialized(repo: Path) -> tuple[dict, dict]:
    if not dev_state_path(repo).exists() or not release_state_path(repo).exists():
        raise CliError("development stage is not initialized")
    return load(dev_state_path(repo)), load(release_state_path(repo))


def validate_spec(repo: Path, spec: dict, state: dict) -> None:
    required = ("task_id", "assignment_version", "member_id", "human_owner", "goal", "requirement_refs", "acceptance_refs", "allowed_scope", "test_requirements", "required_checks", "reviewers", "working_branch", "target_branch", "base_commit")
    missing = [key for key in required if key not in spec or spec[key] in (None, "", [])]
    if missing:
        raise CliError("task spec missing fields: " + ", ".join(missing))
    if spec["member_id"] in spec["reviewers"]:
        raise CliError("task author cannot be a reviewer")
    if spec["task_id"] in state.get("tasks", {}):
        raise CliError("task id already exists")
    for task in state.get("tasks", {}).values():
        if task.get("working_branch") == spec["working_branch"]:
            raise CliError("working branch is already assigned")
    git(repo, "cat-file", "-e", f"{spec['base_commit']}^{{commit}}")


def assignment_from(spec: dict, confirmed: bool) -> dict:
    return {
        "project_schema_version": SCHEMA_VERSION,
        "assignment_id": spec["task_id"], "assignment_version": spec["assignment_version"],
        "stage_id": "04-development", "assignment_kind": "implementation",
        "member_id": spec["member_id"], "human_owner": spec["human_owner"], "goal": spec["goal"],
        "requirement_refs": spec["requirement_refs"], "acceptance_criteria": spec["acceptance_refs"],
        "allowed_scope": spec["allowed_scope"], "forbidden_scope": spec.get("forbidden_scope", []),
        "test_requirements": spec["test_requirements"], "required_checks": spec["required_checks"],
        "reviewers": spec["reviewers"], "risk_owners": spec.get("risk_owners", []), "risk_level": spec.get("risk_level", "R0"),
        "git": {"working_branch": spec["working_branch"], "target_branch": spec["target_branch"], "base_commit": spec["base_commit"]},
        "required_member_skill": MEMBER_SKILL,
        "dispatch_confirmation": {"status": "confirmed" if confirmed else "awaiting-human-confirmation"},
    }


def cmd_create_task(args) -> dict:
    repo = root(args.repo); state, release = require_initialized(repo); spec = load(args.spec)
    validate_spec(repo, spec, state)
    preview = assignment_from(spec, False)
    token = digest(preview)
    if not args.confirm_dispatch:
        return {"status": "awaiting-human-confirmation", "confirmation_token": token, "preview": preview}
    if args.confirm_dispatch != token:
        raise CliError("dispatch confirmation token is invalid or stale")
    assignment = assignment_from(spec, True)
    assignment["dispatch_confirmation"].update({"confirmation_token": token, "confirmed_at": now()})
    path = dev_root(repo) / "dispatch" / spec["member_id"] / f"{spec['task_id']}-v{spec['assignment_version']}.yaml"
    save(path, assignment)
    state.setdefault("tasks", {})[spec["task_id"]] = {
        "member_id": spec["member_id"], "human_owner": spec["human_owner"], "status": "distributed",
        "working_branch": spec["working_branch"], "target_branch": spec["target_branch"],
        "assignment_path": relative(repo, path), "updated_at": now(),
    }
    save(dev_state_path(repo), state); update_project_state(repo, dev=state)
    return {"status": "distributed", "assignment_path": relative(repo, path)}


def find_assignment(repo: Path, state: dict, task_id: str) -> tuple[dict, dict]:
    task = state.get("tasks", {}).get(task_id)
    if not task:
        raise CliError(f"unknown task: {task_id}")
    return task, load(repo / task["assignment_path"])


def cmd_review(args) -> dict:
    repo = root(args.repo); state, release = require_initialized(repo); task, assignment = find_assignment(repo, state, args.task_id)
    if args.reviewer == assignment["member_id"]:
        raise CliError("self review is forbidden")
    if args.reviewer not in assignment["reviewers"]:
        raise CliError("reviewer is not assigned to this task")
    git(repo, "cat-file", "-e", f"{args.commit}^{{commit}}")
    if args.verdict == "approved" and (args.p0 != 0 or args.p1 != 0):
        raise CliError("approved review requires zero P0 and P1 findings")
    review = {"project_schema_version": SCHEMA_VERSION, "task_id": args.task_id, "author": assignment["member_id"], "reviewer": args.reviewer, "commit": args.commit, "verdict": args.verdict, "findings": {"p0": args.p0, "p1": args.p1}, "reviewed_at": now()}
    path = dev_root(repo) / "reviews" / args.task_id / f"{args.reviewer}.yaml"; save(path, review)
    task.update({"status": "review-approved" if args.verdict == "approved" else "changes-requested", "review_commit": args.commit, "updated_at": now()})
    save(dev_state_path(repo), state); update_project_state(repo, dev=state)
    return {"status": task["status"], "review_path": relative(repo, path)}


def approved_review(repo: Path, task_id: str, commit: str, author: str) -> bool:
    folder = dev_root(repo) / "reviews" / task_id
    if not folder.exists():
        return False
    return any((r.get("verdict") == "approved" and r.get("commit") == commit and r.get("reviewer") != author and r.get("findings", {}).get("p0") == 0 and r.get("findings", {}).get("p1") == 0) for r in (load(p) for p in folder.glob("*.yaml")))


def is_ancestor(repo: Path, commit: str, target: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, target], cwd=repo, capture_output=True).returncode == 0


def cmd_integration(args) -> dict:
    repo = root(args.repo); state, release = require_initialized(repo); task, assignment = find_assignment(repo, state, args.task_id)
    if not approved_review(repo, args.task_id, args.commit, assignment["member_id"]):
        raise CliError("exact commit lacks an independent approved review")
    git(repo, "cat-file", "-e", f"{args.target_ref}^{{commit}}")
    if not is_ancestor(repo, args.commit, args.target_ref):
        raise CliError("reviewed commit has not been merged into target ref")
    record = {"project_schema_version": SCHEMA_VERSION, "task_id": args.task_id, "commit": args.commit, "target_ref": args.target_ref, "target_commit": git(repo, "rev-parse", args.target_ref), "status": "integrated", "verified_at": now()}
    path = dev_root(repo) / "integration" / f"{args.task_id}.yaml"; save(path, record)
    task.update({"status": "integrated", "integrated_commit": args.commit, "target_commit": record["target_commit"], "updated_at": now()})
    save(dev_state_path(repo), state); update_project_state(repo, dev=state)
    return {"status": "integrated", "integration_path": relative(repo, path)}


def cmd_prepare_g4(args) -> dict:
    repo = root(args.repo); state, release = require_initialized(repo)
    pending = [task_id for task_id, task in state.get("tasks", {}).items() if task.get("status") != "integrated"]
    if pending:
        raise CliError("tasks not integrated: " + ", ".join(pending))
    git(repo, "cat-file", "-e", f"{args.release_candidate}^{{commit}}")
    for task_id, task in state.get("tasks", {}).items():
        if not is_ancestor(repo, task["integrated_commit"], args.release_candidate):
            raise CliError(f"integrated task {task_id} is absent from release candidate")
    payload = {"gate": "G4", "release_candidate": args.release_candidate, "integrated_tasks": {k: v["integrated_commit"] for k, v in sorted(state.get("tasks", {}).items())}}
    token = digest(payload)
    decision = {**payload, "status": "awaiting-human-approval", "confirmation_token": token, "prepared_at": now()}
    save(release_root(repo) / "gate" / "g4-decision.yaml", decision)
    (release_root(repo) / "gate" / "g4-review-pack.md").write_text("# G4 review pack\n\nRelease candidate: `" + args.release_candidate + "`\n\nAll distributed tasks are independently reviewed and integrated.\n", encoding="utf-8")
    release.update({"status": "g4-review", "g4": decision}); save(release_state_path(repo), release); update_project_state(repo, release=release)
    return {"status": "awaiting-human-approval", "confirmation_token": token, "preview": payload}


def approve_gate(repo: Path, gate: str, token: str, approved_by: str) -> dict:
    state = load(release_state_path(repo)); path = release_root(repo) / "gate" / f"{gate.lower()}-decision.yaml"; decision = load(path)
    if decision.get("status") != "awaiting-human-approval" or decision.get("confirmation_token") != token:
        raise CliError(f"{gate} confirmation token is invalid or stale")
    decision.update({"status": "passed", "approved_by": approved_by, "approved_at": now()}); save(path, decision); state[gate.lower()] = decision
    return state


def cmd_approve_g4(args) -> dict:
    repo = root(args.repo); state = approve_gate(repo, "G4", args.confirmation_token, args.approved_by); state["status"] = "rollout"; save(release_state_path(repo), state); update_project_state(repo, release=state); return {"status": "passed", "gate": "G4"}


def cmd_rollout(args) -> dict:
    repo = root(args.repo); dev, state = require_initialized(repo)
    if state.get("g4", {}).get("status") != "passed":
        raise CliError("G4 has not passed")
    old = int(state.get("rollout", {}).get("percentage", 0))
    if not 0 <= args.percentage <= 100 or args.percentage < old:
        raise CliError("rollout percentage must be monotonic and between 0 and 100")
    record = {"percentage": args.percentage, "observation": args.observation, "recorded_at": now()}; state["rollout"] = record; state["status"] = "monitoring"
    save(release_root(repo) / "rollout" / "current.yaml", record); save(release_state_path(repo), state); update_project_state(repo, release=state)
    return {"status": "recorded", **record}


def cmd_prepare_g5(args) -> dict:
    repo = root(args.repo); dev, state = require_initialized(repo)
    if state.get("g4", {}).get("status") != "passed" or state.get("rollout", {}).get("percentage") != 100 or state.get("rollout", {}).get("observation") != "passed" or state.get("open_incidents", 0) != 0:
        raise CliError("G5 prerequisites are not satisfied")
    payload = {"gate": "G5", "g4_release_candidate": state["g4"]["release_candidate"], "rollout": state["rollout"], "open_incidents": 0}
    token = digest(payload); decision = {**payload, "status": "awaiting-human-approval", "confirmation_token": token, "prepared_at": now()}
    save(release_root(repo) / "gate" / "g5-decision.yaml", decision)
    (release_root(repo) / "gate" / "g5-review-pack.md").write_text("# G5 review pack\n\nRollout reached 100%, observation passed, and no incidents remain open.\n", encoding="utf-8")
    state.update({"status": "g5-review", "g5": decision}); save(release_state_path(repo), state); update_project_state(repo, release=state)
    return {"status": "awaiting-human-approval", "confirmation_token": token, "preview": payload}


def cmd_approve_g5(args) -> dict:
    repo = root(args.repo); state = approve_gate(repo, "G5", args.confirmation_token, args.approved_by); state["status"] = "closed"; state["delivery_status"] = "closed"; save(release_state_path(repo), state)
    baseline = release_root(repo) / "baseline" / f"G5-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}" / "delivery.json"; save(baseline, {"delivery_status": "closed", "release_candidate": state["g4"]["release_candidate"], "approved_by": args.approved_by, "closed_at": now()})
    update_project_state(repo, release=state); return {"status": "passed", "gate": "G5", "delivery_status": "closed", "baseline_path": relative(repo, baseline)}


def cmd_status(args) -> dict:
    repo = root(args.repo); dev, release = require_initialized(repo); return {"development": dev, "release": release, "task_counts": task_counts(dev)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("init-development"); a.add_argument("repo", type=Path); a.add_argument("--g3-baseline", required=True); a.set_defaults(func=cmd_init)
    a = sub.add_parser("create-task"); a.add_argument("repo", type=Path); a.add_argument("--spec", type=Path, required=True); a.add_argument("--confirm-dispatch"); a.set_defaults(func=cmd_create_task)
    a = sub.add_parser("record-review"); a.add_argument("repo", type=Path); a.add_argument("--task-id", required=True); a.add_argument("--reviewer", required=True); a.add_argument("--commit", required=True); a.add_argument("--verdict", choices=("approved", "changes-requested"), required=True); a.add_argument("--p0", type=int, default=0); a.add_argument("--p1", type=int, default=0); a.set_defaults(func=cmd_review)
    a = sub.add_parser("record-integration"); a.add_argument("repo", type=Path); a.add_argument("--task-id", required=True); a.add_argument("--commit", required=True); a.add_argument("--target-ref", required=True); a.set_defaults(func=cmd_integration)
    a = sub.add_parser("prepare-g4"); a.add_argument("repo", type=Path); a.add_argument("--release-candidate", required=True); a.set_defaults(func=cmd_prepare_g4)
    for name, func in (("approve-g4", cmd_approve_g4), ("approve-g5", cmd_approve_g5)):
        a = sub.add_parser(name); a.add_argument("repo", type=Path); a.add_argument("--confirmation-token", required=True); a.add_argument("--approved-by", required=True); a.set_defaults(func=func)
    a = sub.add_parser("record-rollout"); a.add_argument("repo", type=Path); a.add_argument("--percentage", type=int, required=True); a.add_argument("--observation", choices=("pending", "passed", "failed"), required=True); a.set_defaults(func=cmd_rollout)
    a = sub.add_parser("prepare-g5"); a.add_argument("repo", type=Path); a.set_defaults(func=cmd_prepare_g5)
    a = sub.add_parser("status"); a.add_argument("repo", type=Path); a.set_defaults(func=cmd_status)
    return p


def main() -> int:
    try:
        args = parser().parse_args(); print(json.dumps(args.func(args), ensure_ascii=False)); return 0
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())

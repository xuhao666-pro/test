#!/usr/bin/env python3
"""Create idempotent, reminder-only GitHub Issue notifications for AI SOP facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class NotificationError(RuntimeError):
    pass


EVENTS = {
    "task-dispatched": ("任务已正式下发", "dispatched"),
    "submission-received": ("成员提交已收到，待可信校验", "pending-validation"),
    "submission-valid": ("成员提交可信校验通过", "valid"),
    "submission-invalid": ("成员提交可信校验失败", "invalid"),
    "task-blocked": ("成员报告阻塞", "blocked"),
}
STATE_LABELS = {value[1] for value in EVENTS.values()}
LABEL_COLORS = {
    "sop-task": "1f6feb",
    "dispatched": "8250df",
    "pending-validation": "bf8700",
    "valid": "1a7f37",
    "invalid": "cf222e",
    "blocked": "d1242f",
}
LOGIN_RE = re.compile(r"^(?!-)[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def validate_github_login(value: str) -> str:
    value = str(value).strip()
    if not LOGIN_RE.fullmatch(value):
        raise NotificationError(f"Invalid GitHub login: {value!r}")
    return value


def issue_marker(assignment_id: str) -> str:
    return f"<!-- sop-notification:assignment:{assignment_id} -->"


def event_marker(assignment_id: str, event: str, identity: str) -> str:
    digest = hashlib.sha256(f"{assignment_id}|{event}|{identity}".encode()).hexdigest()[:20]
    return f"<!-- sop-notification:event:{digest} -->"


def sanitize_detail(detail: str) -> str:
    text = " ".join(str(detail or "").splitlines())[:500]
    text = re.sub(r"(?i)(token|secret|password|authorization)\s*[:=]\s*\S+", r"\1=[redacted]", text)
    return text


def transition_labels(current: list[str], event: str) -> list[str]:
    if event not in EVENTS:
        raise NotificationError(f"Unsupported notification event: {event}")
    if "valid" in current and event != "submission-valid":
        return sorted(set(current))
    target = EVENTS[event][1]
    retained = sorted({label for label in current if label not in STATE_LABELS})
    return retained + [target]


def render_event(
    event: str,
    assignment: dict[str, Any],
    *,
    member_login: str,
    coordinator_login: str,
    commit_sha: str,
    assignment_path: str,
    run_url: str,
    detail: str = "",
) -> dict[str, Any]:
    if event not in EVENTS:
        raise NotificationError(f"Unsupported notification event: {event}")
    member_login = validate_github_login(member_login)
    coordinator_login = validate_github_login(coordinator_login)
    assignment_id = str(assignment.get("assignment_id", "")).strip()
    member_id = str(assignment.get("member_id", "")).strip()
    if not assignment_id or not member_id:
        raise NotificationError("Assignment requires assignment_id and member_id")
    if not SHA_RE.fullmatch(commit_sha):
        raise NotificationError("Commit must be an exact 7-40 character hexadecimal SHA")
    if assignment_path.startswith(("/", "\\")) or ".." in Path(assignment_path).parts:
        raise NotificationError("Assignment path must be repository-relative")

    phrase, state_label = EVENTS[event]
    mention = f"@{member_login}" if event == "task-dispatched" else f"@{coordinator_login}"
    if event == "submission-invalid":
        mention = f"@{member_login} @{coordinator_login}"
    marker = event_marker(assignment_id, event, commit_sha)
    lines = [
        marker,
        f"{mention} **{phrase}**",
        "",
        f"- 任务：`{assignment_id}`",
        f"- 成员：`{member_id}`",
        f"- 精确提交：`{commit_sha}`",
        f"- 任务文件：`{assignment_path}`",
        f"- Actions：[查看运行记录]({run_url})",
    ]
    safe_detail = sanitize_detail(detail)
    if safe_detail:
        lines.append(f"- 摘要：{safe_detail}")
    lines.extend(["", "> 此 Issue 仅用于提醒，不构成 SOP 状态、人工确认或 Gate 批准。"])

    if event == "task-dispatched":
        title = f"[SOP 新任务] {assignment_id}"
        body = "\n".join(
            [
                issue_marker(assignment_id),
                f"@{member_login} **任务已正式下发**",
                "",
                f"- 任务：`{assignment_id}`",
                f"- 摘要：{assignment.get('summary', '')}",
                f"- 任务文件：`{assignment_path}`",
                f"- 登记分支：`{assignment.get('git_branch', '')}`",
                f"- 最低 Member Skill：`{assignment.get('minimum_skill_version', '')}`",
                f"- 精确提交：`{commit_sha}`",
                "",
                "> 此 Issue 仅用于提醒，不构成 SOP 状态、人工确认或 Gate 批准。",
            ]
        )
        return {"title": title, "body": body, "labels": ["sop-task", state_label], "marker": marker}
    return {"title": "", "body": "\n".join(lines), "labels": ["sop-task", state_label], "marker": marker}


class GitHubClient:
    def __init__(self, repository: str, token: str):
        if repository.count("/") != 1 or not token:
            raise NotificationError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
        self.base = f"https://api.github.com/repos/{repository}"
        self.token = token

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ai-sop-coordinator-notifier",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read() or b"null")
        except urllib.error.HTTPError as exc:
            message = exc.read().decode(errors="replace")[:500]
            raise NotificationError(f"GitHub API {method} {path} failed ({exc.code}): {message}") from exc

    def find_issue(self, marker: str) -> dict[str, Any] | None:
        for issue in self.request("GET", "/issues?state=all&labels=sop-task&per_page=100"):
            if marker in str(issue.get("body", "")) and "pull_request" not in issue:
                return issue
        return None

    def comment_exists(self, number: int, marker: str) -> bool:
        comments = self.request("GET", f"/issues/{number}/comments?per_page=100")
        return any(marker in str(comment.get("body", "")) for comment in comments)

    def ensure_labels(self, labels: list[str]) -> None:
        existing = {item["name"] for item in self.request("GET", "/labels?per_page=100")}
        for label in labels:
            if label not in existing:
                self.request("POST", "/labels", {"name": label, "color": LABEL_COLORS[label]})


def load_json_yaml(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NotificationError(f"Expected JSON-compatible YAML at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise NotificationError(f"Expected an object at {path}")
    return value


def discover_events(
    project_root: Path,
    git_ref: str,
    commit_sha: str,
    changed_paths: list[str],
) -> list[dict[str, str]]:
    """Map one exact push to notification events without reading Issue input."""
    root = project_root.resolve()
    dispatches: dict[str, str] = {}
    for path in root.glob("sop/stages/*/dispatch/*.yaml"):
        try:
            assignment = load_json_yaml(path)
        except NotificationError:
            continue
        assignment_id = str(assignment.get("assignment_id", ""))
        if assignment_id:
            dispatches[assignment_id] = path.relative_to(root).as_posix()

    if git_ref == "refs/heads/main":
        events = []
        changed = set(changed_paths)
        for assignment_id, path in sorted(dispatches.items()):
            if path in changed:
                events.append({"event": "task-dispatched", "assignment": path, "detail": ""})
        return events

    state_path = root / "sop/project-state.yaml"
    if not state_path.exists():
        return []
    state = load_json_yaml(state_path)
    stages = dict(state.get("submission_tracking", {})).get("stages", {})
    events = []
    for stage in dict(stages).values():
        for record in dict(stage.get("records", {})).values():
            if str(record.get("observed_head", "")) != commit_sha:
                continue
            assignment_id = str(record.get("assignment_id", ""))
            assignment_path = dispatches.get(assignment_id)
            if not assignment_path:
                continue
            if record.get("status") == "blocked":
                events.append({"event": "task-blocked", "assignment": assignment_path, "detail": ""})
                continue
            if record.get("status") != "submitted":
                continue
            events.append({"event": "submission-received", "assignment": assignment_path, "detail": ""})
            validation = str(record.get("validation_status", ""))
            if validation == "valid":
                events.append({"event": "submission-valid", "assignment": assignment_path, "detail": ""})
            elif validation == "invalid":
                events.append(
                    {
                        "event": "submission-invalid",
                        "assignment": assignment_path,
                        "detail": sanitize_detail(str(record.get("validation_reason", ""))),
                    }
                )
    return events


def deliver(args: argparse.Namespace) -> None:
    config = load_json_yaml(Path(args.config))
    if not bool(config.get("enabled", False)):
        print(json.dumps({"delivered": False, "reason": "notifications-disabled"}))
        return
    assignment = load_json_yaml(Path(args.assignment))
    member_id = str(assignment.get("member_id", ""))
    member = dict(config.get("members", {})).get(member_id, {})
    if not member or not bool(member.get("enabled", True)):
        raise NotificationError(f"No enabled GitHub notification mapping for member {member_id}")
    rendered = render_event(
        args.event,
        assignment,
        member_login=str(member.get("github_login", "")),
        coordinator_login=str(config.get("coordinator_github_login", "")),
        commit_sha=args.commit,
        assignment_path=args.assignment.replace("\\", "/"),
        run_url=args.run_url,
        detail=args.detail,
    )
    client = GitHubClient(os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_TOKEN", ""))
    client.ensure_labels(["sop-task", *STATE_LABELS])
    issue = client.find_issue(issue_marker(str(assignment["assignment_id"])))
    if args.event == "task-dispatched" and issue is None:
        issue = client.request("POST", "/issues", {key: rendered[key] for key in ("title", "body", "labels")})
    elif issue is None:
        raise NotificationError("Assignment Issue does not exist; deliver task-dispatched first")
    number = int(issue["number"])
    if args.event != "task-dispatched" and not client.comment_exists(number, rendered["marker"]):
        client.request("POST", f"/issues/{number}/comments", {"body": rendered["body"]})
    current = [item["name"] for item in issue.get("labels", [])]
    labels = transition_labels(current or ["sop-task"], args.event)
    payload: dict[str, Any] = {"labels": labels}
    if args.event == "submission-valid":
        payload["state"] = "closed"
    client.request("PATCH", f"/issues/{number}", payload)
    print(json.dumps({"delivered": True, "issue": number, "event": args.event}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, choices=sorted(EVENTS))
    parser.add_argument("--assignment", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--config", default="sop/notification-config.yaml")
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--detail", default="")
    return parser


def main() -> int:
    try:
        deliver(build_parser().parse_args())
        return 0
    except NotificationError as exc:
        print(f"notification error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

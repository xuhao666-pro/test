#!/usr/bin/env python3
"""Send reminder-only AI SOP events to a signed DingTalk custom robot."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class NotificationError(RuntimeError):
    pass


EVENTS = {
    "task-dispatched": "任务已正式下发",
    "task-reminder": "任务催办提醒",
    "submission-received": "成员提交已收到，待可信校验",
    "submission-valid": "成员提交可信校验通过",
    "submission-invalid": "成员提交可信校验失败",
    "task-blocked": "成员报告阻塞",
}
SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
MOBILE_RE = re.compile(r"^\+?[0-9]{6,20}$")
USER_ID_RE = re.compile(r"^[A-Za-z0-9._:@-]{1,128}$")


def sanitize_detail(detail: str) -> str:
    text = " ".join(str(detail or "").splitlines())[:500]
    return re.sub(
        r"(?i)(token|secret|password|authorization|webhook)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        text,
    )


def create_signature(timestamp: int, secret: str) -> str:
    if not secret:
        raise NotificationError("DINGSECRET is required")
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def signed_webhook(webhook: str, secret: str, timestamp: int) -> str:
    normalized = str(webhook or "").strip()
    if not normalized:
        raise NotificationError("DINGWEBHOOK is empty")
    if normalized.upper().startswith("DINGWEBHOOK="):
        raise NotificationError("DINGWEBHOOK value must not include the DINGWEBHOOK= prefix")
    if "${{" in normalized:
        raise NotificationError("DINGWEBHOOK value must not be a GitHub expression")
    if normalized[:1] in {"'", '"'} or normalized[-1:] in {"'", '"'}:
        raise NotificationError("DINGWEBHOOK value must not be wrapped in quotes")
    if not normalized.startswith("https://"):
        raise NotificationError("DINGWEBHOOK must start with https://")

    parsed = urllib.parse.urlsplit(normalized)
    hostname = (parsed.hostname or "").lower()
    if not (
        hostname == "dingtalk.com" or hostname.endswith(".dingtalk.com")
    ):
        raise NotificationError("DINGWEBHOOK hostname must be dingtalk.com")
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.extend(
        [
            ("timestamp", str(timestamp)),
            ("sign", create_signature(timestamp, secret)),
        ]
    )
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
    )


def load_json_yaml(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NotificationError(f"Expected JSON-compatible YAML at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise NotificationError(f"Expected an object at {path}")
    return value


def load_member_targets(raw: str, member_id: str) -> dict[str, list[str]]:
    if not raw.strip():
        return {"atMobiles": [], "atUserIds": []}
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NotificationError("DING_MEMBER_MAP must be valid JSON") from exc
    if not isinstance(mapping, dict):
        raise NotificationError("DING_MEMBER_MAP must be a JSON object")
    target = mapping.get(member_id, {})
    if target is None:
        target = {}
    if not isinstance(target, dict):
        raise NotificationError(f"DingTalk target for {member_id} must be an object")

    def string_list(key: str, pattern: re.Pattern[str]) -> list[str]:
        value = target.get(key, [])
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise NotificationError(f"DingTalk target {member_id}.{key} must be a string list")
        result = [item.strip() for item in value if item.strip()]
        if any(not pattern.fullmatch(item) for item in result):
            raise NotificationError(f"DingTalk target {member_id}.{key} contains an invalid value")
        return result

    return {
        "atMobiles": string_list("atMobiles", MOBILE_RE),
        "atUserIds": string_list("atUserIds", USER_ID_RE),
    }


def render_event(
    event: str,
    assignment: dict[str, Any],
    *,
    commit_sha: str,
    assignment_path: str,
    run_url: str,
    detail: str = "",
    at_mobiles: list[str] | None = None,
    at_user_ids: list[str] | None = None,
) -> dict[str, Any]:
    if event not in EVENTS:
        raise NotificationError(f"Unsupported notification event: {event}")
    if not SHA_RE.fullmatch(commit_sha):
        raise NotificationError("Commit must be an exact 7-40 character hexadecimal SHA")
    assignment_id = str(assignment.get("assignment_id", "")).strip()
    member_id = str(assignment.get("member_id", "")).strip()
    human_owner = str(assignment.get("human_owner", member_id)).strip()
    if not assignment_id or not member_id:
        raise NotificationError("Assignment requires assignment_id and member_id")
    if assignment_path.startswith(("/", "\\")) or ".." in Path(assignment_path).parts:
        raise NotificationError("Assignment path must be repository-relative")

    title = f"[SOP 提醒] {EVENTS[event]}"
    at_mobiles = list(at_mobiles or [])
    at_user_ids = list(at_user_ids or [])
    mention = " ".join(f"@{mobile}" for mobile in at_mobiles)
    lines = [
        f"### {title}",
        "",
        *([f"{mention} 请处理以下任务。"] if mention else [f"请 {human_owner} 处理以下任务。"]),
        "",
        f"- 任务：`{assignment_id}`",
        f"- 成员：`{member_id}`",
        f"- 精确提交：`{commit_sha}`",
        f"- 任务文件：`{assignment_path}`",
        f"- [查看 Actions 运行记录]({run_url})",
    ]
    safe_detail = sanitize_detail(detail)
    if safe_detail:
        lines.append(f"- 摘要：{safe_detail}")
    lines.extend(
        [
            "",
            "> 此消息仅用于提醒，不构成 SOP 状态、人工确认、授权、Gate 批准或合并依据。",
        ]
    )
    return {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": "\n".join(lines)},
        "at": {
            "atMobiles": at_mobiles,
            "atUserIds": at_user_ids,
            "isAtAll": False,
        },
    }


def render_test(run_url: str) -> dict[str, Any]:
    title = "[SOP 提醒] 钉钉通道测试"
    text = "\n".join(
        [
            f"### {title}",
            "",
            "钉钉自定义机器人已成功接入 GitHub Actions。",
            "",
            f"- [查看 Actions 运行记录]({run_url})",
            "",
            "> 这是一条通道测试消息，仅用于验证提醒投递，不改变任何 SOP 状态。",
        ]
    )
    return {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
        "at": {"isAtAll": False},
    }


def send(payload: dict[str, Any], *, webhook: str, secret: str, timestamp: int | None = None) -> None:
    timestamp = int(time.time() * 1000) if timestamp is None else timestamp
    url = signed_webhook(webhook, secret, timestamp)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        message = exc.read().decode(errors="replace")[:300]
        raise NotificationError(f"DingTalk API request failed ({exc.code}): {message}") from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise NotificationError(f"DingTalk API request failed: {exc}") from exc
    if int(result.get("errcode", -1)) != 0:
        raise NotificationError(
            f"DingTalk rejected the reminder: errcode={result.get('errcode')}, "
            f"errmsg={str(result.get('errmsg', 'unknown'))[:200]}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", choices=sorted(EVENTS))
    parser.add_argument("--assignment")
    parser.add_argument("--commit")
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--detail", default="")
    parser.add_argument("--test", action="store_true")
    return parser


def deliver(args: argparse.Namespace) -> None:
    if args.test:
        payload = render_test(args.run_url)
        event = "integration-test"
    else:
        if not args.event or not args.assignment or not args.commit:
            raise NotificationError("--event, --assignment and --commit are required")
        assignment = load_json_yaml(Path(args.assignment))
        targets = load_member_targets(
            os.environ.get("DING_MEMBER_MAP", ""),
            str(assignment.get("member_id", "")),
        )
        payload = render_event(
            args.event,
            assignment,
            commit_sha=args.commit,
            assignment_path=args.assignment.replace("\\", "/"),
            run_url=args.run_url,
            detail=args.detail,
            at_mobiles=targets["atMobiles"],
            at_user_ids=targets["atUserIds"],
        )
        event = args.event
    send(
        payload,
        webhook=os.environ.get("DINGWEBHOOK", ""),
        secret=os.environ.get("DINGSECRET", ""),
    )
    print(json.dumps({"delivered": True, "channel": "dingtalk", "event": event}))


def main() -> int:
    try:
        deliver(build_parser().parse_args())
        return 0
    except NotificationError as exc:
        print(f"notification error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

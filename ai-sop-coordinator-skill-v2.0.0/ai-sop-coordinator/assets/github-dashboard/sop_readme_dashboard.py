#!/usr/bin/env python3
"""Render a private repository README dashboard as a static SVG."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


START_MARKER = "<!-- ai-sop-readme-dashboard:start -->"
END_MARKER = "<!-- ai-sop-readme-dashboard:end -->"
DASHBOARD_RENDERER_VERSION = "2.2"
STAGE_NAMES = {
    "01-requirement-contract": "需求契约",
    "02-solution-validation": "方案验证",
    "03-development-entry": "开发准入",
}
STATUS_LABELS = {
    "pre-development": "研发准备",
    "development-entry-approved": "已准入开发",
    "human-approved-merge-pending": "人工已通过 · 待合并",
    "not-started": "未开始",
    "approved-to-start": "已批准开始",
    "preparing": "待开始",
    "collecting": "进行中",
    "returned-to-collection": "已退回",
    "submission-closed": "提交已关闭",
    "aggregating": "汇总中",
    "team-review": "团队评审",
    "gate-pending": "待人工 Gate",
    "merge-pending": "待合并 main",
    "baselined": "已建立",
    "next-stage": "已进入下一阶段",
    "terminated": "已终止",
    "submitted": "已提交",
    "in-progress": "进行中",
    "missing": "待提交",
    "valid": "校验通过",
    "pending-validation": "待校验",
    "not-submitted": "未提交",
    "invalid": "校验失败",
    "none": "未建立",
}
KIND_LABELS = {
    "requirement-analysis": "需求分析",
    "function-design": "功能设计",
    "system-inventory": "系统盘点",
    "prototype-validation": "原型验证",
    "technical-design": "技术设计",
    "test-task-packaging": "测试与任务拆分",
    "shared-review": "共同评审",
    "generic": "通用任务",
}
BASELINE_DESCRIPTIONS = {
    "G1": "需求范围、验收口径、边界",
    "G2": "接口、数据、页面结构",
    "G3": "测试、上线、回滚条件",
}
EXECUTION_MODE_LABELS = {
    "standard": "标准模式",
    "lightweight": "轻量模式",
}
COLLABORATION_LABELS = {
    "role-based": "角色分工",
    "collective-participation": "共同参与",
}


def load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"状态文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{path} 必须使用当前 Skill 生成的 JSON 兼容 YAML 格式"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError("项目状态根节点必须是对象")
    return data


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def shorten(value: Any, limit: int = 32) -> str:
    text_value = str(value or "-").replace("\n", " ").strip()
    return text_value if len(text_value) <= limit else text_value[: limit - 1] + "…"


def format_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "尚未刷新"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(ZoneInfo("Asia/Shanghai"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except (ValueError, ZoneInfoNotFoundError):
        return shorten(raw, 24)


def value_label(value: Any) -> str:
    raw = str(value or "-")
    return STATUS_LABELS.get(raw, raw)


def progress(done: int, total: int) -> tuple[int, str]:
    if total <= 0:
        return 0, "待开始"
    ratio = max(0.0, min(1.0, done / total))
    return round(ratio * 100), f"{ratio:.0%}"


def blockers_text(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "当前无阻塞项"
    items = []
    for item in value:
        if isinstance(item, dict):
            items.append(
                str(
                    item.get("title")
                    or item.get("description")
                    or item.get("reason")
                    or "未命名阻塞项"
                )
            )
        else:
            items.append(str(item))
    return "；".join(items)


def visual_units(value: Any) -> int:
    return sum(2 if ord(char) > 127 else 1 for char in str(value or ""))


def shorten_visual(value: Any, max_units: int) -> str:
    text_value = str(value or "-").replace("\n", " ").strip()
    if visual_units(text_value) <= max_units:
        return text_value
    kept: list[str] = []
    used = 0
    for char in text_value:
        char_units = 2 if ord(char) > 127 else 1
        if used + char_units > max_units - 2:
            break
        kept.append(char)
        used += char_units
    return "".join(kept) + "…"


def svg_text(
    x: int,
    y: int,
    value: Any,
    css_class: str = "body",
    *,
    limit: int = 60,
    anchor: str | None = None,
    visual_limit: int | None = None,
) -> str:
    anchor_attr = f' text-anchor="{anchor}"' if anchor else ""
    display = (
        shorten_visual(value, visual_limit)
        if visual_limit is not None
        else shorten(value, limit)
    )
    return (
        f'<text x="{x}" y="{y}" class="{css_class}"{anchor_attr}>'
        f"{escape(display)}</text>"
    )


def rect(
    x: int,
    y: int,
    width: int,
    height: int,
    css_class: str,
    *,
    radius: int = 16,
    extra: str = "",
) -> str:
    suffix = f" {extra.strip()}" if extra.strip() else ""
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{radius}" class="{css_class}"{suffix}/>'
    )


def status_tone(value: Any) -> str:
    raw = str(value or "")
    if raw in {
        "valid",
        "submitted",
        "baselined",
        "next-stage",
        "development-entry-approved",
    }:
        return "green"
    if raw in {"invalid", "terminated", "R2", "R3"}:
        return "red"
    if raw in {
        "collecting",
        "in-progress",
        "aggregating",
        "team-review",
        "pending-validation",
        "gate-pending",
        "merge-pending",
    }:
        return "blue"
    if raw in {"R1", "returned-to-collection"}:
        return "orange"
    return "gray"


def pill(
    x: int,
    y: int,
    label: Any,
    tone: str = "gray",
    *,
    min_width: int = 50,
) -> tuple[str, int]:
    display = shorten_visual(label, 24)
    width = pill_width(display, min_width)
    return (
        "\n".join(
            [
                rect(x, y, width, 26, f"pill-{tone}", radius=13),
                svg_text(x + width // 2, y + 18, display, f"pill-text-{tone}", anchor="middle"),
            ]
        ),
        width,
    )


def pill_width(label: Any, min_width: int = 50) -> int:
    display = shorten_visual(label, 24)
    return max(min_width, min(190, 18 + visual_units(display) * 7))


def baseline_status(
    gate: str,
    value: Any,
    next_gate: str,
    pending_gate: str,
) -> tuple[str, str]:
    if gate == pending_gate:
        return "待合并", "orange"
    if gate == next_gate and value in (None, "", "none"):
        return "当前 Gate", "blue"
    if value in (None, "", "none"):
        return "未建立", "gray"
    return shorten(value, 18), "green"


def task_sort_key(item: tuple[str, Any]) -> tuple[int, str]:
    assignment_id, raw_record = item
    record = raw_record if isinstance(raw_record, dict) else {}
    status = str(record.get("validation_status") or record.get("status") or "")
    priority = {
        "invalid": 0,
        "pending-validation": 1,
        "not-submitted": 2,
        "missing": 2,
        "in-progress": 3,
        "valid": 4,
    }
    return priority.get(status, 5), assignment_id


def acceptance_label(record: dict[str, Any]) -> str:
    acceptance = record.get("assignment_acceptance", {})
    acceptance = acceptance if isinstance(acceptance, dict) else {}
    status = str(acceptance.get("status") or "legacy-not-required")
    if status == "accepted":
        observed_at = acceptance.get("observed_at") or acceptance.get("accepted_at")
        return "已接受" + (f" {format_timestamp(observed_at)}" if observed_at else "")
    return {
        "pending": "待接受",
        "invalid": "接受凭证异常",
        "legacy-not-required": "",
    }.get(status, status)


def render_svg(state: dict[str, Any]) -> str:
    tracking = state.get("submission_tracking", {})
    tracking = tracking if isinstance(tracking, dict) else {}
    totals = tracking.get("totals", {})
    totals = totals if isinstance(totals, dict) else {}
    stages = tracking.get("stages", {})
    stages = stages if isinstance(stages, dict) else {}
    baselines = state.get("baselines", {})
    baselines = baselines if isinstance(baselines, dict) else {}
    expected = safe_int(totals.get("expected_count"))
    valid = safe_int(totals.get("valid_count"))
    submitted = safe_int(totals.get("submitted_count"))
    pending = safe_int(totals.get("pending_validation_count"))
    invalid = safe_int(totals.get("invalid_count"))
    missing = safe_int(totals.get("missing_count"))
    current_stage_id = str(state.get("current_stage", ""))
    current_stage = stages.get(current_stage_id, {})
    current_stage = current_stage if isinstance(current_stage, dict) else {}
    records = current_stage.get("records", {})
    records = records if isinstance(records, dict) else {}
    current_round_id = str(current_stage.get("current_round_id") or "")
    current_round_records = {
        assignment_id: record
        for assignment_id, record in records.items()
        if isinstance(record, dict)
        and str(record.get("round_id") or "") == current_round_id
    }
    task_pool = current_round_records if current_round_records else records
    task_rows = list(sorted(task_pool.items(), key=task_sort_key))[:8]
    hidden_task_count = max(0, len(task_pool) - len(task_rows))
    task_grid_rows = max(1, (len(task_rows) + 1) // 2)
    task_section_y = 908
    footer_y = task_section_y + 68 + task_grid_rows * 108
    height = footer_y + 132
    percent, percent_text = progress(valid, expected)
    risk = str(state.get("highest_risk_level", "R0"))
    refresh_time = format_timestamp(
        tracking.get("last_refreshed_at") or state.get("updated_at")
    )
    current_stage_name = STAGE_NAMES.get(current_stage_id, current_stage_id or "待同步")
    stage_ids = list(STAGE_NAMES)
    current_stage_index = stage_ids.index(current_stage_id) if current_stage_id in stage_ids else -1
    coordination_store = state.get("coordination_store", {})
    coordination_store = coordination_store if isinstance(coordination_store, dict) else {}
    git_integration = state.get("git_integration", {})
    git_integration = git_integration if isinstance(git_integration, dict) else {}
    git_detected = bool(coordination_store.get("git_detected"))
    remote_name = str(tracking.get("remote") or "").strip()
    git_connected = git_detected and bool(remote_name)
    git_required = bool(git_integration.get("required", True))
    main_branch = str(git_integration.get("main_branch") or "main")
    merge_policy = str(git_integration.get("merge_policy") or "")
    next_gate = str(state.get("next_fixed_gate") or "")
    pending_gate_value = git_integration.get("pending_gate")
    if isinstance(pending_gate_value, dict):
        pending_gate = str(pending_gate_value.get("gate_id") or "")
    else:
        pending_gate = str(pending_gate_value or "")
    current_valid = safe_int(current_stage.get("valid_count"))
    current_pending = safe_int(current_stage.get("pending_validation_count"))
    current_invalid = safe_int(current_stage.get("invalid_count"))
    current_missing = safe_int(current_stage.get("missing_count"))
    current_acceptance_required = safe_int(current_stage.get("acceptance_required_count"))
    current_acceptance_accepted = safe_int(current_stage.get("acceptance_accepted_count"))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" '
        f'viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(str(state.get("project_name", "项目")))} 项目状态看板</title>',
        '<desc id="desc">由 SOP 项目状态自动生成的只读进度看板</desc>',
        """<defs>
          <filter id="softShadow" x="-20%" y="-20%" width="140%" height="160%">
            <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#111827" flood-opacity="0.08"/>
          </filter>
        </defs>
        <style>
          text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif; }
          .bg { fill: #ffffff; }
          .soft-card { fill: #f5f5f7; }
          .white-card { fill: #ffffff; stroke: #ececef; stroke-width: 1; }
          .shadow-card { fill: #f5f5f7; filter: url(#softShadow); }
          .eyebrow { fill: #8b8b90; font-size: 13px; font-weight: 500; letter-spacing: 0.4px; }
          .title { fill: #1d1d1f; font-size: 30px; font-weight: 720; }
          .subtitle { fill: #8b8b90; font-size: 13px; }
          .label { fill: #8b8b90; font-size: 13px; }
          .metric { fill: #1d1d1f; font-size: 22px; font-weight: 700; }
          .metric-small { fill: #1d1d1f; font-size: 18px; font-weight: 680; }
          .section { fill: #1d1d1f; font-size: 20px; font-weight: 700; }
          .section-note { fill: #a0a0a5; font-size: 12px; }
          .body { fill: #2f2f32; font-size: 14px; }
          .body-strong { fill: #1d1d1f; font-size: 14px; font-weight: 650; }
          .muted { fill: #99999e; font-size: 12px; }
          .tiny { fill: #a0a0a5; font-size: 11px; }
          .nav-active { fill: #1d1d1f; font-size: 13px; font-weight: 680; }
          .nav-idle { fill: #8b8b90; font-size: 13px; }
          .nav-underline { stroke: #3b93ff; stroke-width: 3; stroke-linecap: round; }
          .track { fill: #efeff1; }
          .bar { fill: #3b93ff; }
          .bar-green { fill: #34c759; }
          .line { stroke: #ececef; stroke-width: 1; }
          .timeline-line { stroke: #e6e6e9; stroke-width: 2; }
          .timeline-line-active { stroke: #3b93ff; stroke-width: 2; }
          .timeline-node { fill: #ffffff; stroke: #dedee2; stroke-width: 2; }
          .timeline-node-active { fill: #3b93ff; stroke: #3b93ff; stroke-width: 2; }
          .baseline-dot { fill: #f2f2f4; }
          .pill-blue { fill: #e7f2ff; }
          .pill-green { fill: #e7f8ed; }
          .pill-orange { fill: #fff0e6; }
          .pill-red { fill: #ffebeb; }
          .pill-gray { fill: #f0f0f2; }
          .pill-text-blue { fill: #2d87ed; font-size: 12px; font-weight: 650; }
          .pill-text-green { fill: #248a4b; font-size: 12px; font-weight: 650; }
          .pill-text-orange { fill: #c66a2b; font-size: 12px; font-weight: 650; }
          .pill-text-red { fill: #d33d3d; font-size: 12px; font-weight: 650; }
          .pill-text-gray { fill: #737378; font-size: 12px; font-weight: 650; }
          .ok-dot { fill: #34c759; }
          .warn-dot { fill: #ff9f0a; }
          .danger-dot { fill: #ff453a; }
        </style>""",
        f'<rect width="1200" height="{height}" class="bg"/>',
        svg_text(42, 38, "项目状态驾驶舱", "eyebrow"),
        svg_text(
            42,
            78,
            state.get("project_name", state.get("project_id", "项目")),
            "title",
            visual_limit=48,
        ),
        svg_text(
            42,
            104,
            f"项目 ID · {state.get('project_id', '-')} · {state.get('real_development_status', '-')}",
            "subtitle",
            visual_limit=112,
        ),
        rect(900, 28, 258, 116, "shadow-card"),
        svg_text(920, 58, "状态更新时间", "label"),
        svg_text(920, 91, refresh_time, "metric-small"),
        svg_text(920, 116, f"来源 · project-state.yaml · r{safe_int(tracking.get('revision'))}", "tiny"),
    ]

    chip_x = 42
    for label, tone in (
        (value_label(state.get("status")), "orange"),
        (f"当前阶段 · {current_stage_name}", "blue"),
        (
            EXECUTION_MODE_LABELS.get(
                str(state.get("execution_mode", "")),
                str(state.get("execution_mode", "-")),
            ),
            "blue",
        ),
        (
            COLLABORATION_LABELS.get(
                str(state.get("collaboration_model", "")),
                str(state.get("collaboration_model", "-")),
            ),
            "gray",
        ),
    ):
        markup, chip_width = pill(chip_x, 122, label, tone)
        parts.append(markup)
        chip_x += chip_width + 10

    summary_cards = [
        (42, "协议版本", state.get("protocol_version", "-"), "protocol-version"),
        (322, "项目结构版本", state.get("project_schema_version", "-"), "project-schema-version"),
        (602, "协调器", state.get("coordinator_id", "-"), "coordinator-id"),
        (882, "最高风险", risk, "highest-risk-level"),
    ]
    for card_x, label, metric, field_name in summary_cards:
        parts.extend(
            [
                rect(card_x, 172, 258, 94, "soft-card"),
                svg_text(card_x + 16, 201, label, "label"),
                svg_text(card_x + 16, 232, metric, "metric", visual_limit=24),
                svg_text(card_x + 16, 251, field_name, "tiny"),
            ]
        )

    parts.extend(
        [
            svg_text(42, 312, "总览视图", "nav-active"),
            '<line x1="42" y1="322" x2="94" y2="322" class="nav-underline"/>',
            svg_text(122, 312, "协同状态", "nav-idle"),
            svg_text(202, 312, "校验状态", "nav-idle"),
            svg_text(1158, 312, "自动生成 · 只读投影", "section-note", anchor="end"),
            svg_text(42, 366, "阶段推进", "section"),
            svg_text(
                1158,
                366,
                (
                    f"当前停在第 {current_stage_index + 1} 阶段"
                    if current_stage_index >= 0
                    else "当前阶段待同步"
                ),
                "section-note",
                anchor="end",
            ),
        ]
    )

    timeline_xs = [54, 430, 806]
    timeline_y = 410
    for index in range(len(timeline_xs) - 1):
        line_class = "timeline-line-active" if index < current_stage_index else "timeline-line"
        parts.append(
            f'<line x1="{timeline_xs[index] + 8}" y1="{timeline_y}" '
            f'x2="{timeline_xs[index + 1] - 8}" y2="{timeline_y}" class="{line_class}"/>'
        )
    for index, stage_id in enumerate(stage_ids):
        stage = stages.get(stage_id, {})
        stage = stage if isinstance(stage, dict) else {}
        node_class = (
            "timeline-node-active"
            if current_stage_index >= 0 and index <= current_stage_index
            else "timeline-node"
        )
        parts.extend(
            [
                f'<circle cx="{timeline_xs[index]}" cy="{timeline_y}" r="7" class="{node_class}"/>',
                svg_text(timeline_xs[index] - 8, 443, STAGE_NAMES[stage_id], "body-strong"),
                svg_text(
                    timeline_xs[index] - 8,
                    466,
                    (
                        "当前"
                        if current_stage_index >= 0 and index == current_stage_index
                        else value_label(stage.get("stage_status"))
                    ),
                    "muted",
                ),
            ]
        )

    parts.extend(
        [
            svg_text(42, 526, "模块进度", "section"),
            svg_text(750, 526, f"整体有效进度 {percent_text}", "section-note", anchor="end"),
            svg_text(800, 526, "基线状态", "section"),
            svg_text(1158, 526, "G1–G3", "section-note", anchor="end"),
        ]
    )

    module_y = 558
    for index, stage_id in enumerate(stage_ids):
        stage = stages.get(stage_id, {})
        stage = stage if isinstance(stage, dict) else {}
        row_y = module_y + index * 84
        stage_expected = safe_int(stage.get("expected_count"))
        stage_valid = safe_int(stage.get("valid_count"))
        stage_submitted = safe_int(stage.get("submitted_count"))
        stage_percent, stage_percent_text = progress(stage_valid, stage_expected)
        label = value_label(stage.get("stage_status"))
        status_markup, _ = pill(
            138, row_y - 17, label, status_tone(stage.get("stage_status")), min_width=54
        )
        parts.extend(
            [
                svg_text(42, row_y, STAGE_NAMES[stage_id], "body-strong"),
                status_markup,
                svg_text(750, row_y, stage_percent_text, "body-strong", anchor="end"),
                rect(42, row_y + 14, 708, 10, "track", radius=5),
                rect(42, row_y + 14, round(708 * stage_percent / 100), 10, "bar", radius=5),
                svg_text(
                    42,
                    row_y + 44,
                    f"有效 {stage_valid}/{stage_expected} · 已提交 {stage_submitted}",
                    "muted",
                ),
                f'<line x1="42" y1="{row_y + 61}" x2="750" y2="{row_y + 61}" class="line"/>',
            ]
        )

    git_row_y = module_y + 3 * 84
    if git_connected:
        git_status_label = "远程已连接"
        git_status_tone = "green"
        git_bar_width = 708
        git_bar_class = "bar-green"
        git_right_label = "已连接"
    elif git_detected:
        git_status_label = "本地已检测"
        git_status_tone = "blue"
        git_bar_width = 460
        git_bar_class = "bar"
        git_right_label = "待远程"
    else:
        git_status_label = "未检测"
        git_status_tone = "red" if git_required else "gray"
        git_bar_width = 0
        git_bar_class = "bar"
        git_right_label = "必需" if git_required else "可选"
    merge_policy_label = (
        "人工审核后强制合并"
        if merge_policy == "all-active-member-branches-after-human-approval"
        else "按项目合并策略执行"
    )
    git_status_markup, _ = pill(
        158,
        git_row_y - 17,
        git_status_label,
        git_status_tone,
        min_width=54,
    )
    parts.extend(
        [
            svg_text(42, git_row_y, "Git 协同存储", "body-strong"),
            git_status_markup,
            svg_text(750, git_row_y, git_right_label, "body-strong", anchor="end"),
            rect(42, git_row_y + 14, 708, 10, "track", radius=5),
            rect(
                42,
                git_row_y + 14,
                git_bar_width,
                10,
                git_bar_class,
                radius=5,
            ),
            svg_text(
                42,
                git_row_y + 44,
                (
                    f"远程 · {remote_name} · " if remote_name else ""
                )
                + f"主分支 · {main_branch} · {merge_policy_label}",
                "muted",
                visual_limit=94,
            ),
            f'<line x1="42" y1="{git_row_y + 61}" x2="750" y2="{git_row_y + 61}" class="line"/>',
        ]
    )

    baseline_y = 554
    for index, gate in enumerate(("G1", "G2", "G3")):
        row_y = baseline_y + index * 84
        label, tone = baseline_status(gate, baselines.get(gate), next_gate, pending_gate)
        baseline_pill_width = pill_width(label, 70)
        status_markup, _ = pill(
            1158 - baseline_pill_width,
            row_y + 3,
            label,
            tone,
            min_width=70,
        )
        parts.extend(
            [
                f'<circle cx="818" cy="{row_y + 19}" r="17" class="baseline-dot"/>',
                svg_text(818, row_y + 24, gate, "body-strong", anchor="middle"),
                svg_text(850, row_y + 17, f"{gate} 基线", "body-strong"),
                svg_text(850, row_y + 39, BASELINE_DESCRIPTIONS[gate], "muted"),
                status_markup,
                f'<line x1="800" y1="{row_y + 62}" x2="1158" y2="{row_y + 62}" class="line"/>',
            ]
        )

    parts.extend(
        [
            svg_text(42, task_section_y, "当前阶段任务", "section"),
            svg_text(
                1158,
                task_section_y,
                (
                    (
                        f"接受 {current_acceptance_accepted}/{current_acceptance_required} · "
                        if current_acceptance_required
                        else ""
                    )
                    + f"有效 {current_valid} · 待校验 {current_pending} · "
                    f"缺失 {current_missing} · 失败 {current_invalid}"
                    + (f" · 另 {hidden_task_count} 项" if hidden_task_count else "")
                ),
                "section-note",
                anchor="end",
            ),
        ]
    )
    if not task_rows:
        parts.extend(
            [
                rect(42, task_section_y + 28, 1116, 82, "soft-card"),
                svg_text(62, task_section_y + 63, "当前阶段暂无任务", "body-strong"),
                svg_text(62, task_section_y + 87, "任务分发后会在此显示成员、类型和校验状态", "muted"),
            ]
        )
    for index, (assignment_id, raw_record) in enumerate(task_rows):
        record = raw_record if isinstance(raw_record, dict) else {}
        column = index % 2
        row = index // 2
        card_x = 42 + column * 570
        card_y = task_section_y + 28 + row * 108
        status_value = record.get("validation_status") or record.get("status")
        task_status_label = value_label(status_value)
        task_pill_width = pill_width(task_status_label, 84)
        status_markup, _ = pill(
            card_x + 528 - task_pill_width,
            card_y + 16,
            task_status_label,
            status_tone(status_value),
            min_width=84,
        )
        task_kind = str(record.get("assignment_kind") or record.get("kind") or "generic")
        submitted_at = record.get("submitted_at")
        submission_time = (
            format_timestamp(submitted_at) if submitted_at else "尚未提交"
        )
        acceptance = acceptance_label(record)
        member_line = f"成员 · {record.get('member_id', '-')}"
        if acceptance:
            member_line += f" · {acceptance}"
        parts.extend(
            [
                rect(card_x, card_y, 546, 88, "soft-card"),
                svg_text(card_x + 18, card_y + 28, KIND_LABELS.get(task_kind, task_kind), "body-strong"),
                svg_text(
                    card_x + 18,
                    card_y + 51,
                    member_line,
                    "muted",
                    visual_limit=48,
                ),
                svg_text(card_x + 18, card_y + 72, assignment_id, "tiny", limit=52),
                status_markup,
                svg_text(
                    card_x + 528,
                    card_y + 68,
                    f"提交 · {submission_time}",
                    "tiny",
                    anchor="end",
                ),
            ]
        )

    blockers = blockers_text(state.get("blocking_items"))
    has_blockers = blockers != "当前无阻塞项"
    parts.extend(
        [
            rect(42, footer_y, 1116, 86, "white-card"),
            f'<circle cx="64" cy="{footer_y + 29}" r="5" class="{("warn-dot" if has_blockers else "ok-dot")}"/>',
            svg_text(80, footer_y + 34, blockers, "body-strong", visual_limit=130),
            svg_text(
                80,
                footer_y + 59,
                f"整体有效 {valid}/{expected} · 已提交 {submitted} · renderer {DASHBOARD_RENDERER_VERSION}",
                "muted",
            ),
            svg_text(1138, footer_y + 59, refresh_time, "muted", anchor="end"),
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def update_readme(path: Path, image_path: str) -> None:
    block = (
        f"{START_MARKER}\n"
        "## 项目状态看板\n\n"
        f"![项目状态看板]({image_path})\n\n"
        "> 由 SOP 状态自动生成的只读驾驶舱。\n"
        f"{END_MARKER}"
    )
    if path.exists():
        content = path.read_text(encoding="utf-8")
    else:
        content = "# 项目状态\n"
    start_count = content.count(START_MARKER)
    end_count = content.count(END_MARKER)
    if (
        start_count != end_count
        or start_count > 1
        or (start_count == 1 and content.index(END_MARKER) < content.index(START_MARKER))
    ):
        raise RuntimeError("README 看板标记缺失、重复或不成对，请人工修复后重试")
    if start_count == 1:
        start = content.index(START_MARKER)
        end = content.index(END_MARKER, start) + len(END_MARKER)
        content = content[:start].rstrip() + "\n\n" + block + content[end:]
    else:
        content = content.rstrip() + "\n\n" + block + "\n"
    atomic_write(path, content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--readme", required=True)
    args = parser.parse_args()
    try:
        state_path = Path(args.state).resolve()
        output_path = Path(args.output).resolve()
        readme_path = Path(args.readme).resolve()
        state = load_state(state_path)
        try:
            image_path = output_path.relative_to(readme_path.parent).as_posix()
        except ValueError as exc:
            raise RuntimeError("看板图片必须位于 README 所在仓库目录内") from exc
        atomic_write(output_path, render_svg(state))
        update_readme(readme_path, image_path)
        print(json.dumps({"svg": str(output_path), "readme": str(readme_path)}, ensure_ascii=False))
        return 0
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

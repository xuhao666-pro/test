#!/usr/bin/env python3
"""Fail closed or no-op before project-scoped GitHub Actions run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class GuardError(RuntimeError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GuardError(f"{path} must contain an object")
    return value


def evaluate(root: Path, required_capabilities: list[str]) -> tuple[bool, str]:
    system_path = root / ".github" / "sop-system.json"
    system = load_object(system_path)
    if system.get("schema_version") != "1.0":
        raise GuardError("sop-system schema_version must be 1.0")
    lifecycle = system.get("lifecycle")
    if lifecycle == "bootstrap":
        return False, "system-bootstrap"
    if lifecycle != "active":
        raise GuardError("lifecycle must be bootstrap or active")
    if system.get("project_initialized") is not True:
        raise GuardError("active lifecycle requires project_initialized=true")
    if system.get("project_data_included") is not True:
        raise GuardError("active lifecycle requires project_data_included=true")
    capabilities = system.get("capabilities")
    if not isinstance(capabilities, dict):
        raise GuardError("capabilities must be an object")
    missing = [name for name in required_capabilities if capabilities.get(name) is not True]
    if missing:
        return False, "capability-disabled:" + ",".join(sorted(missing))
    state_path = root / "sop" / "project-state.yaml"
    state = load_object(state_path)
    if not state:
        raise GuardError("project-state must not be empty")
    return True, "active"


def write_output(path: Path, active: bool, reason: str) -> None:
    safe_reason = reason.replace("\r", " ").replace("\n", " ")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"active={'true' if active else 'false'}\n")
        stream.write(f"reason={safe_reason}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--github-output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()
    try:
        active, reason = evaluate(root, list(args.capability))
        if args.github_output:
            write_output(Path(args.github_output), active, reason)
    except GuardError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"active": active, "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
}

BLOCKED_FILE_PATTERNS = [
    re.compile(r"closedloopoptimization", re.IGNORECASE),
    re.compile(r"mechanism_module", re.IGNORECASE),
    re.compile(r"machanism_module", re.IGNORECASE),
    re.compile(r"fallback_strategy_module", re.IGNORECASE),
    re.compile(r"e2e_prediction_module", re.IGNORECASE),
    re.compile(r"input_protection\.yml", re.IGNORECASE),
    re.compile(r"load_conditions\.csv", re.IGNORECASE),
    re.compile(r"model_.*\.pkl$", re.IGNORECASE),
    re.compile(r"model_.*\.joblib$", re.IGNORECASE),
    re.compile(r"\.pyc$", re.IGNORECASE),
]

BLOCKED_CONTENT_PATTERNS = [
    re.compile(r"from\s+closed_loop_optimization_formal\s+import", re.IGNORECASE),
    re.compile(r"heartbeat_management", re.IGNORECASE),
    re.compile(r"boilerefficiency", re.IGNORECASE),
    re.compile(r"mechanism_plan_[ab]", re.IGNORECASE),
]


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def scan() -> list[str]:
    findings: list[str] = []

    for root, _, files in os.walk(REPO_ROOT):
        root_path = Path(root)
        if should_skip(root_path):
            continue

        for filename in files:
            file_path = root_path / filename
            rel = file_path.relative_to(REPO_ROOT)
            rel_str = str(rel)

            if rel_str == "tools/sensitive_scan.py":
                continue

            for pattern in BLOCKED_FILE_PATTERNS:
                if pattern.search(rel_str):
                    findings.append(f"blocked filename pattern: {rel_str} matches {pattern.pattern}")
                    break

            if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".zip", ".gz"}:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:  # noqa: BLE001
                findings.append(f"file read failure: {rel_str} ({exc})")
                continue

            for pattern in BLOCKED_CONTENT_PATTERNS:
                if pattern.search(content):
                    findings.append(f"blocked content pattern: {rel_str} matches {pattern.pattern}")

    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("Sensitive scan failed. Findings:")
        for item in findings:
            print(f"- {item}")
        return 1

    print("Sensitive scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

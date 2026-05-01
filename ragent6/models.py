from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CaseSpec:
    case_id: str
    dimension_id: str
    title: str
    objective: str
    prompt_file: str
    checker: str
    audit_tier: str = "discriminative"
    fixtures: list[dict[str, Any]] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    runner_mode: str = "single_turn"
    timeout_seconds: int = 60
    max_turns: int = 1
    max_tool_calls: int | None = None
    followup_prompt_files: list[str] = field(default_factory=list)
    expected: dict[str, Any] = field(default_factory=dict)
    mock_trace_file: str | None = None
    locale: str = "en-US"


@dataclass
class Manifest:
    suite_name: str
    suite_version: str
    cases: list[str]
    locale: str = "en-US"
    dimension_weights: dict[str, float] = field(default_factory=dict)
    dimension_labels: dict[str, str] = field(default_factory=dict)


@dataclass
class CaseResult:
    case_id: str
    dimension_id: str
    status: str
    score: int | None
    checker: str
    reason_code: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    trace_file: str | None = None


@dataclass
class RunSummary:
    suite_name: str
    suite_version: str
    locale: str
    adapter: str
    total_cases: int
    graded_cases: int
    invalid_cases: int
    total_score: int
    total_possible: int
    weighted_score: float | None
    dimensions: dict[str, dict[str, int]]
    out_dir: str


def relpath(base: Path, target: Path) -> str:
    return str(target.relative_to(base))

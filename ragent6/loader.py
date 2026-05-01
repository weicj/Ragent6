from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CaseSpec, Manifest


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(path: Path) -> Manifest:
    data = load_json(path)
    return Manifest(
        suite_name=data["suite_name"],
        suite_version=data["suite_version"],
        locale=str(data.get("locale") or "en-US"),
        cases=data["cases"],
        dimension_weights={str(k): float(v) for k, v in data.get("dimension_weights", {}).items()},
        dimension_labels={str(k): str(v) for k, v in data.get("dimension_labels", {}).items()},
    )


def load_case(path: Path) -> CaseSpec:
    data = load_json(path)
    return CaseSpec(
        case_id=data["case_id"],
        dimension_id=data["dimension_id"],
        title=data["title"],
        objective=data["objective"],
        prompt_file=data["prompt_file"],
        checker=data["checker"],
        audit_tier=data.get("audit_tier", "discriminative"),
        fixtures=data.get("fixtures", []),
        allowed_tools=data.get("allowed_tools", []),
        runner_mode=data.get("runner_mode", "single_turn"),
        timeout_seconds=int(data.get("timeout_seconds", 60)),
        max_turns=int(data.get("max_turns", 1)),
        max_tool_calls=data.get("max_tool_calls"),
        followup_prompt_files=data.get("followup_prompt_files", []),
        expected=data.get("expected", {}),
        mock_trace_file=data.get("mock_trace_file"),
    )

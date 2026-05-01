from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragent6.models import CaseSpec


def run_case(case: CaseSpec, case_dir: Path) -> dict[str, Any]:
    if not case.mock_trace_file:
        raise RuntimeError(f"{case.case_id} missing mock_trace_file")
    trace_path = case_dir / case.mock_trace_file
    return json.loads(trace_path.read_text(encoding="utf-8"))

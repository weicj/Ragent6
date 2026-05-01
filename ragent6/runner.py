from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import mock
from .adapters import native_local
from .checkers import run_checker
from .constraints import common_constraint_verdict
from .loader import load_case, load_manifest
from .models import CaseResult, RunSummary, relpath


ADAPTERS = {
    "mock": mock.run_case,
    "native_local": native_local,
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_dimension_weights(manifest_weights: dict[str, float] | None = None) -> dict[str, float]:
    if manifest_weights:
        return dict(manifest_weights)
    dims_path = PROJECT_ROOT / "dimensions" / "dimensions.json"
    if not dims_path.is_file():
        return {}
    data = json.loads(dims_path.read_text(encoding="utf-8"))
    out: dict[str, float] = {}
    for item in data.get("dimensions", []):
        dim_id = str(item.get("id", "")).strip()
        weight = item.get("weight")
        if not dim_id or weight is None:
            continue
        out[dim_id] = float(weight)
    return out


def resolve_case_path(manifest_path: Path, case_rel: str) -> Path:
    candidates = [
        manifest_path.parent / case_rel,
        manifest_path.parent.parent / case_rel,
        PROJECT_ROOT / case_rel,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def build_summary_dimension_ids(manifest: Any, manifest_path: Path) -> list[str]:
    """Map case results onto the public summary dimensions.

    Ragent6 reports an R1-R6 surface where each block contains
    10 cases. If a custom manifest omits public dimension labels, fall back to
    the case-level dimension IDs.
    """
    public_dims = list((manifest.dimension_labels or {}).keys())
    if public_dims and set(public_dims) == set((manifest.dimension_weights or {}).keys()):
        if len(manifest.cases) % len(public_dims) == 0:
            block_size = len(manifest.cases) // len(public_dims)
            return [public_dims[i // block_size] for i in range(len(manifest.cases))]

    summary_dims: list[str] = []
    for case_rel in manifest.cases:
        case_path = resolve_case_path(manifest_path, case_rel)
        case = load_case(case_path)
        summary_dims.append(case.dimension_id)
    return summary_dims


def summarize_dimension_totals(summary_dim_ids: list[str]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for dim_id in summary_dim_ids:
        totals[dim_id] = totals.get(dim_id, 0) + 1
    return totals


def evaluate(manifest_path: Path, adapter_name: str, out_dir: Path) -> RunSummary:
    manifest = load_manifest(manifest_path)
    adapter = ADAPTERS[adapter_name]
    dim_weights = load_dimension_weights(manifest.dimension_weights)
    summary_dim_ids = build_summary_dimension_ids(manifest, manifest_path)
    case_dim_totals = summarize_dimension_totals(summary_dim_ids)
    suite_context = None
    if hasattr(adapter, "prepare_suite"):
        suite_context = adapter.prepare_suite()

    out_dir.mkdir(parents=True, exist_ok=True)
    results_dir = out_dir / "cases"
    results_dir.mkdir(parents=True, exist_ok=True)

    case_results: list[CaseResult] = []
    dimension_counts: dict[str, dict[str, int]] = {}

    def write_summary_snapshot() -> None:
        graded = [item for item in case_results if item.status in {"pass", "fail"}]
        weighted_score = None
        if dim_weights and case_dim_totals:
            weighted_score = 0.0
            for dim_id, weight in dim_weights.items():
                total = case_dim_totals.get(dim_id, 0)
                passed = dimension_counts.get(dim_id, {}).get("pass", 0)
                if total <= 0:
                    continue
                weighted_score += weight * (passed / total)
            weighted_score = round(weighted_score, 1)
        snapshot = RunSummary(
            suite_name=manifest.suite_name,
            suite_version=manifest.suite_version,
            adapter=adapter_name,
            total_cases=len(case_results),
            graded_cases=len(graded),
            invalid_cases=len([item for item in case_results if item.status == "invalid"]),
            total_score=sum(item.score or 0 for item in graded),
            total_possible=len(graded),
            weighted_score=weighted_score,
            locale=manifest.locale,
            dimensions=dimension_counts,
            out_dir=str(out_dir),
        )
        summary_path = out_dir / "summary.partial.json"
        summary_path.write_text(json.dumps(snapshot.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        for index, case_rel in enumerate(manifest.cases):
            case_path = resolve_case_path(manifest_path, case_rel)
            case_dir = case_path.parent
            case = load_case(case_path)
            case.locale = manifest.locale
            if hasattr(adapter, "run_case"):
                trace = adapter.run_case(case, case_dir, suite_context)
            else:
                trace = adapter(case, case_dir)
            verdict = common_constraint_verdict(case, trace)
            if verdict is None:
                verdict = run_checker(case, trace, case_dir)

            case_out_dir = results_dir / case.case_id
            case_out_dir.mkdir(parents=True, exist_ok=True)
            trace_path = case_out_dir / "trace.json"
            result_path = case_out_dir / "case_result.json"
            trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            verdict.trace_file = relpath(out_dir, trace_path)
            result_path.write_text(json.dumps(verdict.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            case_results.append(verdict)

            dim_id = summary_dim_ids[index]
            dim = dimension_counts.setdefault(dim_id, {"pass": 0, "fail": 0, "invalid": 0})
            dim[verdict.status] += 1
            write_summary_snapshot()
    finally:
        if hasattr(adapter, "cleanup_suite"):
            adapter.cleanup_suite(suite_context)

    graded = [item for item in case_results if item.status in {"pass", "fail"}]
    total_score = sum(item.score or 0 for item in graded)
    total_possible = len(graded)
    weighted_score = None
    if dim_weights and case_dim_totals:
        weighted_score = 0.0
        for dim_id, weight in dim_weights.items():
            total = case_dim_totals.get(dim_id, 0)
            passed = dimension_counts.get(dim_id, {}).get("pass", 0)
            if total <= 0:
                continue
            weighted_score += weight * (passed / total)
        weighted_score = round(weighted_score, 1)
    summary = RunSummary(
        suite_name=manifest.suite_name,
        suite_version=manifest.suite_version,
        locale=manifest.locale,
        adapter=adapter_name,
        total_cases=len(case_results),
        graded_cases=len(graded),
        invalid_cases=len([item for item in case_results if item.status == "invalid"]),
        total_score=total_score,
        total_possible=total_possible,
        weighted_score=weighted_score,
        dimensions=dimension_counts,
        out_dir=str(out_dir),
    )
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary

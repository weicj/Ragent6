#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragent6.checkers import run_checker
from ragent6.constraints import common_constraint_verdict
from ragent6.loader import load_case, load_manifest
from ragent6.models import RunSummary, relpath
from ragent6.runner import build_summary_dimension_ids, resolve_case_path, load_dimension_weights, summarize_dimension_totals


def main() -> int:
    parser = argparse.ArgumentParser(description="Regrade an existing Ragent6 results directory using current constraints/checkers.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--adapter-label", default=None, help="Adapter label to keep in rewritten summary.json. Defaults to previous summary adapter or regraded.")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    result_dir = args.result_dir.resolve()
    if not manifest_path.is_file():
        raise SystemExit(f"manifest not found: {manifest_path}")
    if not result_dir.is_dir():
        raise SystemExit(f"result dir not found: {result_dir}")
    previous_adapter = "regraded"
    previous_summary_path = result_dir / "summary.json"
    if previous_summary_path.is_file():
        try:
            previous_summary = json.loads(previous_summary_path.read_text(encoding="utf-8"))
            previous_adapter = str(previous_summary.get("adapter") or previous_adapter)
        except Exception:
            previous_adapter = "regraded"

    manifest = load_manifest(manifest_path)
    case_results = []
    dimensions: dict[str, dict[str, int]] = {}
    dim_weights = load_dimension_weights(manifest.dimension_weights)
    summary_dim_ids = build_summary_dimension_ids(manifest, manifest_path)
    case_dim_totals = summarize_dimension_totals(summary_dim_ids)

    for index, case_rel in enumerate(manifest.cases):
        case_path = resolve_case_path(manifest_path, case_rel)
        case = load_case(case_path)
        case.locale = manifest.locale
        trace_path = result_dir / "cases" / case.case_id / "trace.json"
        if not trace_path.exists():
            raise SystemExit(f"missing trace for {case.case_id}: {trace_path}")
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        verdict = common_constraint_verdict(case, trace)
        if verdict is None:
            verdict = run_checker(case, trace, case_path.parent)
        verdict.trace_file = relpath(result_dir, trace_path)
        result_path = trace_path.parent / "case_result.json"
        result_path.write_text(json.dumps(verdict.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        case_results.append(verdict)
        dim_id = summary_dim_ids[index]
        dim = dimensions.setdefault(dim_id, {"pass": 0, "fail": 0, "invalid": 0})
        dim[verdict.status] += 1

    graded = [item for item in case_results if item.status in {"pass", "fail"}]
    weighted_score = None
    if dim_weights and case_dim_totals:
        weighted_score = 0.0
        for dim_id, weight in dim_weights.items():
            total = case_dim_totals.get(dim_id, 0)
            passed = dimensions.get(dim_id, {}).get("pass", 0)
            if total <= 0:
                continue
            weighted_score += weight * (passed / total)
        weighted_score = round(weighted_score, 1)
    summary = RunSummary(
        suite_name=manifest.suite_name,
        suite_version=manifest.suite_version,
        locale=manifest.locale,
        adapter=args.adapter_label or previous_adapter,
        total_cases=len(case_results),
        graded_cases=len(graded),
        invalid_cases=len([item for item in case_results if item.status == "invalid"]),
        total_score=sum(item.score or 0 for item in graded),
        total_possible=len(graded),
        weighted_score=weighted_score,
        dimensions=dimensions,
        out_dir=str(result_dir),
    )
    summary_path = result_dir / "summary.json"
    summary_path.write_text(json.dumps(summary.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"{manifest.suite_name} {manifest.suite_version} {manifest.locale}: "
        f"{summary.total_score}/{summary.total_possible} "
        f"(invalid={summary.invalid_cases}) -> {summary_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

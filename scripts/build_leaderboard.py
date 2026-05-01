#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from release_audit import (
    DEFAULT_EXCLUDE_FILE,
    DEFAULT_LOCALE,
    DEFAULT_MANIFEST,
    DEFAULT_RESULTS_ROOT,
    DEFAULT_SUITE_NAME,
    DEFAULT_SUITE_VERSION,
    case_quality,
    load_result_exclusions,
    scan_results,
    validate_manifest,
)


def load_run_metadata(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "runs" in data and isinstance(data["runs"], dict):
        return {str(key): value for key, value in data["runs"].items() if isinstance(value, dict)}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def dimension_string(dimensions: dict[str, dict[str, int]], dim_order: list[str]) -> str:
    return ", ".join(f"{dim} {dimensions.get(dim, {}).get('pass', 0)}/10" for dim in dim_order)


def leaderboard_rows(
    included_runs: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    dim_order: list[str],
    results_root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in included_runs:
        result_dir = Path(run["result_dir"])
        try:
            run_key = result_dir.relative_to(results_root).as_posix()
        except ValueError:
            run_key = result_dir.name
        meta = metadata.get(run_key) or metadata.get(result_dir.name) or metadata.get(str(result_dir)) or {}
        model = meta.get("model") or meta.get("name") or run_key
        rows.append(
            {
                "run_id": run_key,
                "result_dir": str(result_dir),
                "model": model,
                "params": meta.get("params", ""),
                "quant": meta.get("quant", ""),
                "device": meta.get("device", ""),
                "score": float(run["weighted_score"]),
                "passed": int(run["total_score"]),
                "total": int(run["total_possible"]),
                "dimensions": {dim: run["dimensions"].get(dim, {"pass": 0, "fail": 0, "invalid": 0}) for dim in dim_order},
                "dimension_summary": dimension_string(run["dimensions"], dim_order),
            }
        )
    return sorted(rows, key=lambda item: (-item["score"], -item["passed"], item["model"]))


def render_markdown(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    result_payload: dict[str, Any],
    quality_payload: dict[str, Any],
) -> str:
    labels = manifest.get("dimension_labels") or {}
    lines = [
        f"# Ragent6 {manifest.get('suite_version')} {manifest.get('locale', '')} Leaderboard",
        "",
        f"- Suite: `{manifest.get('suite_name')}`",
        f"- Version: `{manifest.get('suite_version')}`",
        f"- Locale: `{manifest.get('locale', '')}`",
        f"- Eligible runs: `{len(rows)}`",
        f"- Excluded runs: `{len(result_payload.get('excluded_runs') or [])}`",
        f"- Summary mismatches recomputed from per-case results: `{len(result_payload.get('summary_mismatches') or [])}`",
        f"- Saturated cases: `{len(quality_payload.get('saturated_cases') or [])}/60`",
        "",
        "Scores below are recomputed from `cases/<case_id>/case_result.json`, not trusted from historical `summary.json`.",
        "",
        "## Dimension Key",
        "",
        "| Dimension | Name | Weight |",
        "|---|---|---:|",
    ]
    weights = manifest.get("dimension_weights") or {}
    for dim, label in labels.items():
        lines.append(f"| {dim} | {label} | {weights.get(dim, '')} |")

    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Rank | Model / Run | Params | Quant | Score | Passed | R1 | R2 | R3 | R4 | R5 | R6 | Device |",
            "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    dim_order = list(labels.keys())
    for rank, row in enumerate(rows, start=1):
        dim_values = [str(row["dimensions"].get(dim, {}).get("pass", 0)) for dim in dim_order]
        lines.append(
            "| {rank} | {model} | {params} | {quant} | {score:.1f} | {passed}/{total} | {dims} | {device} |".format(
                rank=rank,
                model=str(row["model"]).replace("|", "\\|"),
                params=str(row["params"]).replace("|", "\\|"),
                quant=str(row["quant"]).replace("|", "\\|"),
                score=row["score"],
                passed=row["passed"],
                total=row["total"],
                dims=" | ".join(dim_values),
                device=str(row["device"]).replace("|", "\\|"),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Ragent6 leaderboard from audited per-case results.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--exclude-file", type=Path, default=DEFAULT_EXCLUDE_FILE)
    parser.add_argument("--suite-name", default=DEFAULT_SUITE_NAME)
    parser.add_argument("--suite-version", default=DEFAULT_SUITE_VERSION)
    parser.add_argument("--locale", default=DEFAULT_LOCALE)
    parser.add_argument("--case-count", type=int, default=60)
    parser.add_argument("--metadata", type=Path, help="Optional JSON mapping result directory names to model metadata.")
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest, public_cases, manifest_errors = validate_manifest(
        manifest_path,
        expected_suite_name=args.suite_name,
        expected_suite_version=args.suite_version,
        expected_locale=args.locale or None,
        expected_case_count=args.case_count,
    )
    if manifest_errors:
        for error in manifest_errors:
            print(f"ERROR: {error}")
        return 1

    result_payload = scan_results(
        args.results_root.resolve(),
        public_cases,
        manifest.get("dimension_weights") or {},
        load_result_exclusions(args.exclude_file.resolve() if args.exclude_file else None),
        expected_suite_name=args.suite_name,
        expected_suite_version=args.suite_version,
        expected_locale=args.locale or None,
        expected_case_count=args.case_count,
    )
    if result_payload["result_errors"]:
        for item in result_payload["result_errors"]:
            print(f"ERROR: {item}")
        return 1

    dim_order = list((manifest.get("dimension_labels") or {}).keys())
    metadata = load_run_metadata(args.metadata)
    rows = leaderboard_rows(result_payload["included_runs"], metadata, dim_order, args.results_root.resolve())
    quality_payload = case_quality(result_payload["included_runs"], public_cases)
    json_payload = {
        "suite_name": manifest.get("suite_name"),
        "suite_version": manifest.get("suite_version"),
        "locale": manifest.get("locale"),
        "manifest": str(manifest_path),
        "results_root": str(args.results_root.resolve()),
        "leaderboard": rows,
        "excluded_runs": result_payload["excluded_runs"],
        "summary_mismatches": result_payload["summary_mismatches"],
        "case_quality": quality_payload,
    }

    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(manifest, rows, result_payload, quality_payload), encoding="utf-8")
        print(f"wrote {args.md_out}")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.json_out}")
    if not args.md_out and not args.json_out:
        print(render_markdown(manifest, rows, result_payload, quality_payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "ragent6.json"
DEFAULT_SUITE_NAME = "Ragent6"
DEFAULT_SUITE_VERSION = "1.1.0"
DEFAULT_RESULTS_ROOT = ROOT / "results"
DEFAULT_EXCLUDE_FILE = ROOT / "metadata" / "ragent6_result_exclusions.json"


EXCLUDE_RESULT_NAME_RE = re.compile(
    r"(mock|thinking|pilot|partial|bad|crash|"
    r"diagnostic|debug|repro|control|newbackend|noquantvec|nocompress|cuda132|"
    r"driver595|graphs|swafull|noctxcp|illegal|rtx-ab)",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_result_exclusions(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    data = load_json(path)
    if "runs" in data and isinstance(data["runs"], dict):
        data = data["runs"]
    out: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out[str(key)] = str(value.get("reason") or "excluded by release metadata")
        else:
            out[str(key)] = str(value)
    return out


def resolve_case_path(manifest_path: Path, case_rel: str) -> Path:
    candidates = [
        manifest_path.parent / case_rel,
        manifest_path.parent.parent / case_rel,
        ROOT / case_rel,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def manifest_public_blocks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    labels = manifest.get("dimension_labels") or {}
    weights = manifest.get("dimension_weights") or {}
    cases = list(manifest.get("cases") or [])
    public_dims = list(labels.keys())
    if not public_dims:
        return []
    block_size = len(cases) // len(public_dims) if public_dims else 0
    blocks: list[dict[str, Any]] = []
    for index, case_rel in enumerate(cases):
        dim = public_dims[index // block_size]
        blocks.append(
            {
                "case_rel": case_rel,
                "public_id": f"{dim}-{(index % block_size) + 1:02d}",
                "dimension": dim,
                "dimension_label": labels.get(dim, dim),
                "weight": float(weights.get(dim, 0)),
            }
        )
    return blocks


def validate_manifest(
    manifest_path: Path,
    expected_suite_name: str = DEFAULT_SUITE_NAME,
    expected_suite_version: str = DEFAULT_SUITE_VERSION,
    expected_case_count: int = 60,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    manifest = load_json(manifest_path)
    cases = list(manifest.get("cases") or [])
    labels = manifest.get("dimension_labels") or {}
    weights = manifest.get("dimension_weights") or {}
    public_dims = list(labels.keys())

    if manifest.get("suite_name") != expected_suite_name:
        errors.append(f"manifest suite_name must be {expected_suite_name}")
    if manifest.get("suite_version") != expected_suite_version:
        errors.append(f"manifest suite_version must be {expected_suite_version}")
    if len(cases) != expected_case_count:
        errors.append(f"manifest must contain {expected_case_count} cases, got {len(cases)}")
    if len(public_dims) != 6:
        errors.append(f"manifest must contain 6 public dimensions, got {len(public_dims)}")
    if set(public_dims) != set(weights.keys()):
        errors.append("dimension_labels and dimension_weights keys must match")
    if round(sum(float(v) for v in weights.values()), 6) != 100.0:
        errors.append("dimension weights must sum to 100")
    if public_dims and len(cases) % len(public_dims) != 0:
        errors.append("case count must divide evenly across public dimensions")
    if public_dims and len(cases) // len(public_dims) != expected_case_count // max(1, len(public_dims)):
        errors.append("each public dimension must contain the expected case count")

    seen_case_ids: set[str] = set()
    public_cases: list[dict[str, Any]] = []
    for item in manifest_public_blocks(manifest):
        case_path = resolve_case_path(manifest_path, str(item["case_rel"]))
        if not case_path.is_file():
            errors.append(f"case file not found: {item['case_rel']}")
            continue
        try:
            case = load_json(case_path)
        except Exception as exc:
            errors.append(f"case file is not valid JSON: {item['case_rel']}: {exc}")
            continue

        case_id = str(case.get("case_id") or "")
        if not case_id:
            errors.append(f"case missing case_id: {item['case_rel']}")
        elif case_id in seen_case_ids:
            errors.append(f"duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)

        for required in ("dimension_id", "title", "objective", "prompt_file", "checker"):
            if not case.get(required):
                errors.append(f"{case_id or item['case_rel']} missing {required}")

        prompt_file = case_path.parent / str(case.get("prompt_file") or "")
        if case.get("prompt_file") and not prompt_file.is_file():
            errors.append(f"{case_id} prompt file not found: {case.get('prompt_file')}")

        mock_trace_file = case.get("mock_trace_file")
        if mock_trace_file and not (case_path.parent / str(mock_trace_file)).is_file():
            errors.append(f"{case_id} mock trace not found: {mock_trace_file}")

        for fixture in case.get("fixtures") or []:
            rel = fixture.get("path") if isinstance(fixture, dict) else None
            if rel and not (case_path.parent / str(rel)).exists():
                errors.append(f"{case_id} fixture not found: {rel}")

        public_cases.append(
            {
                **item,
                "case_id": case_id,
                "internal_dimension": case.get("dimension_id", ""),
                "title": case.get("title", ""),
                "objective": case.get("objective", ""),
                "audit_tier": case.get("audit_tier", "discriminative"),
                "checker": case.get("checker", ""),
                "allowed_tools": case.get("allowed_tools", []),
            }
        )

    return manifest, public_cases, errors


def eligible_summary(
    summary: dict[str, Any],
    expected_suite_name: str = DEFAULT_SUITE_NAME,
    expected_suite_version: str = DEFAULT_SUITE_VERSION,
    expected_case_count: int = 60,
) -> bool:
    return (
        summary.get("suite_name") == expected_suite_name
        and summary.get("suite_version") == expected_suite_version
        and summary.get("total_cases") == expected_case_count
        and summary.get("graded_cases") == expected_case_count
        and summary.get("invalid_cases") == 0
    )


def recompute_result(
    result_dir: Path,
    public_cases: list[dict[str, Any]],
    weights: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    dims: dict[str, dict[str, int]] = {}
    total_score = 0
    invalid = 0
    aborted = 0

    for item in public_cases:
        case_id = item["case_id"]
        result_path = result_dir / "cases" / case_id / "case_result.json"
        trace_path = result_dir / "cases" / case_id / "trace.json"
        if not result_path.is_file():
            errors.append(f"missing case_result: {case_id}")
            continue
        if not trace_path.is_file():
            errors.append(f"missing trace: {case_id}")
            continue
        try:
            result = load_json(result_path)
        except Exception as exc:
            errors.append(f"invalid case_result JSON {case_id}: {exc}")
            continue
        try:
            trace = load_json(trace_path)
        except Exception as exc:
            errors.append(f"invalid trace JSON {case_id}: {exc}")
            continue
        if trace.get("aborted") is True:
            aborted += 1
        status = result.get("status")
        score = result.get("score")
        dim = item["dimension"]
        dim_counts = dims.setdefault(dim, {"pass": 0, "fail": 0, "invalid": 0})
        if status == "pass":
            dim_counts["pass"] += 1
            total_score += int(score if score is not None else 1)
        elif status == "fail":
            dim_counts["fail"] += 1
        else:
            dim_counts["invalid"] += 1
            invalid += 1

    if errors:
        return None, errors

    weighted = 0.0
    for dim, weight in weights.items():
        counts = dims.get(dim, {"pass": 0, "fail": 0, "invalid": 0})
        total = counts["pass"] + counts["fail"] + counts["invalid"]
        if total:
            weighted += float(weight) * (counts["pass"] / total)

    return {
        "result_dir": str(result_dir),
        "total_score": total_score,
        "total_possible": len(public_cases) - invalid,
        "invalid_cases": invalid,
        "aborted_cases": aborted,
        "weighted_score": round(weighted, 1),
        "dimensions": dims,
    }, []


def scan_results(
    results_root: Path,
    public_cases: list[dict[str, Any]],
    weights: dict[str, Any],
    result_exclusions: dict[str, str] | None = None,
    expected_suite_name: str = DEFAULT_SUITE_NAME,
    expected_suite_version: str = DEFAULT_SUITE_VERSION,
    expected_case_count: int = 60,
) -> dict[str, Any]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    errors: list[dict[str, Any]] = []
    summary_mismatches: list[dict[str, Any]] = []
    exclusions = result_exclusions or {}

    for summary_path in sorted(results_root.glob("*/summary.json")):
        result_dir = summary_path.parent
        name = result_dir.name
        try:
            summary = load_json(summary_path)
        except Exception as exc:
            errors.append({"result_dir": str(result_dir), "error": f"invalid summary JSON: {exc}"})
            continue
        if EXCLUDE_RESULT_NAME_RE.search(name):
            excluded.append({"result_dir": str(result_dir), "reason": "excluded by result directory name"})
            continue
        if name in exclusions:
            excluded.append({"result_dir": str(result_dir), "reason": exclusions[name]})
            continue
        if not eligible_summary(summary, expected_suite_name, expected_suite_version, expected_case_count):
            excluded.append({"result_dir": str(result_dir), "reason": f"not an eligible {expected_suite_name} {expected_suite_version} full run"})
            continue

        recomputed, recompute_errors = recompute_result(result_dir, public_cases, weights)
        if recompute_errors or recomputed is None:
            errors.append({"result_dir": str(result_dir), "errors": recompute_errors})
            continue
        if recomputed.get("aborted_cases", 0):
            excluded.append({"result_dir": str(result_dir), "reason": f"trace aborted in {recomputed['aborted_cases']} case(s)"})
            continue

        summary_weighted = summary.get("weighted_score")
        if isinstance(summary_weighted, (int, float)):
            if abs(float(summary_weighted) - float(recomputed["weighted_score"])) > 0.05:
                summary_mismatches.append(
                    {
                        "result_dir": str(result_dir),
                        "summary_weighted_score": summary_weighted,
                        "recomputed_weighted_score": recomputed["weighted_score"],
                    }
                )
        included.append(recomputed)

    return {
        "included_runs": included,
        "excluded_runs": excluded,
        "result_errors": errors,
        "summary_mismatches": summary_mismatches,
    }


def case_quality(included_runs: list[dict[str, Any]], public_cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not included_runs:
        return {
            "checked_runs": 0,
            "checked_cases": len(public_cases),
            "saturated_cases": [],
            "saturated_ratio": None,
        }

    pass_counts = {item["case_id"]: 0 for item in public_cases}
    graded_counts = {item["case_id"]: 0 for item in public_cases}
    by_public_id = {item["case_id"]: item["public_id"] for item in public_cases}

    for run in included_runs:
        result_dir = Path(run["result_dir"])
        for item in public_cases:
            result_path = result_dir / "cases" / item["case_id"] / "case_result.json"
            if not result_path.is_file():
                continue
            result = load_json(result_path)
            if result.get("status") in {"pass", "fail"}:
                graded_counts[item["case_id"]] += 1
            if result.get("status") == "pass":
                pass_counts[item["case_id"]] += 1

    stats = []
    saturated = []
    for item in public_cases:
        case_id = item["case_id"]
        graded = graded_counts[case_id]
        passed = pass_counts[case_id]
        rate = passed / graded if graded else 0.0
        row = {
            "public_id": by_public_id[case_id],
            "case_id": case_id,
            "passed_runs": passed,
            "graded_runs": graded,
            "pass_rate": round(rate, 4),
        }
        stats.append(row)
        if graded and (rate < 0.10 or rate > 0.90):
            saturated.append(row)

    return {
        "checked_runs": len(included_runs),
        "checked_cases": len(public_cases),
        "saturated_cases": saturated,
        "saturated_ratio": round(len(saturated) / len(public_cases), 4) if public_cases else None,
        "case_stats": stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Ragent6 release assets and recompute eligible result summaries.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--results-root", type=Path, default=None)
    parser.add_argument("--exclude-file", type=Path, default=DEFAULT_EXCLUDE_FILE)
    parser.add_argument("--suite-name", default=DEFAULT_SUITE_NAME)
    parser.add_argument("--suite-version", default=DEFAULT_SUITE_VERSION)
    parser.add_argument("--case-count", type=int, default=60)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-summary-mismatch", action="store_true")
    parser.add_argument(
        "--max-saturated-ratio",
        type=float,
        default=None,
        help=(
            "Optional strict pass/fail saturation limit. Ragent6 scoring is partial-primary, "
            "so strict saturation is reported but not enforced unless this or "
            "--enforce-strict-saturation is provided."
        ),
    )
    parser.add_argument(
        "--enforce-strict-saturation",
        action="store_true",
        help="Fail when strict pass/fail saturation exceeds the configured limit.",
    )
    parser.add_argument("--min-quality-runs", type=int, default=8)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest, public_cases, manifest_errors = validate_manifest(
        manifest_path,
        expected_suite_name=args.suite_name,
        expected_suite_version=args.suite_version,
        expected_case_count=args.case_count,
    )
    result_payload: dict[str, Any] | None = None
    quality_payload: dict[str, Any] | None = None
    release_errors = list(manifest_errors)

    if args.results_root is not None:
        result_payload = scan_results(
            args.results_root.resolve(),
            public_cases,
            manifest.get("dimension_weights") or {},
            load_result_exclusions(args.exclude_file.resolve() if args.exclude_file else None),
            expected_suite_name=args.suite_name,
            expected_suite_version=args.suite_version,
            expected_case_count=args.case_count,
        )
        if result_payload["result_errors"]:
            release_errors.append("one or more result directories are missing required case outputs")
        if args.fail_on_summary_mismatch and result_payload["summary_mismatches"]:
            release_errors.append("one or more summary.json weighted scores differ from recomputed scores")
        quality_payload = case_quality(result_payload["included_runs"], public_cases)
        saturated_ratio = quality_payload.get("saturated_ratio")
        checked_runs = int(quality_payload.get("checked_runs") or 0)
        strict_saturation_enforced = args.enforce_strict_saturation or args.max_saturated_ratio is not None
        strict_saturation_limit = args.max_saturated_ratio if args.max_saturated_ratio is not None else 0.10
        quality_payload["strict_saturation_gate"] = {
            "enforced": strict_saturation_enforced,
            "limit": strict_saturation_limit,
            "reason": (
                "strict 0/1 saturation is auxiliary; primary signal health comes from "
                "partial-score audit and candidate gate"
            ),
        }
        if (
            strict_saturation_enforced
            and
            checked_runs >= args.min_quality_runs
            and isinstance(saturated_ratio, (int, float))
            and saturated_ratio > strict_saturation_limit
        ):
            release_errors.append(
                f"saturated case ratio {saturated_ratio:.4f} exceeds max {strict_saturation_limit:.4f} "
                f"across {checked_runs} eligible runs"
            )

    payload = {
        "status": "pass" if not release_errors else "fail",
        "suite_name": manifest.get("suite_name"),
        "suite_version": manifest.get("suite_version"),
        "manifest_path": str(manifest_path),
        "release_errors": release_errors,
        "manifest_info": {
            "case_count": len(public_cases),
            "public_dimensions": manifest.get("dimension_labels") or {},
            "dimension_weights": manifest.get("dimension_weights") or {},
            "errors": manifest_errors,
        },
        "results": result_payload,
        "case_quality": quality_payload,
    }

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not release_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

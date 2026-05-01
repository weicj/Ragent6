#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
import statistics
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragent6.loader import load_case, load_manifest  # noqa: E402
from ragent6.runner import resolve_case_path  # noqa: E402


@dataclass
class ModelRun:
    name: str
    result_dir: Path
    audit_group: str
    family: str
    generation: str
    generation_rank: int
    arch: str
    original: bool
    size_rank: int
    precision_group: str
    precision_rank: int
    score: float
    strict_score: float
    partial_raw: float
    strict_raw: int
    cases: dict[str, float | None]


def load_case_meta(manifest_path: Path) -> dict[str, dict[str, str]]:
    manifest = load_manifest(manifest_path)
    out: dict[str, dict[str, str]] = {}
    for case_rel in manifest.cases:
        case_path = resolve_case_path(manifest_path, case_rel)
        case = load_case(case_path)
        out[case.case_id] = {
            "dimension_id": case.dimension_id,
            "title": case.title,
            "audit_tier": case.audit_tier,
            "checker": case.checker,
        }
    return out


def suite_payload(partial_json: Path, suite_key: str) -> dict[str, Any]:
    data = json.loads(partial_json.read_text(encoding="utf-8"))
    for suite in data.get("suites", []):
        if suite.get("suite_key") == suite_key:
            return suite
    raise SystemExit(f"suite {suite_key!r} not found in {partial_json}")


def load_runs(suite: dict[str, Any], *, include_excluded: bool = False) -> list[ModelRun]:
    runs: list[ModelRun] = []
    for item in suite.get("models", []):
        if item.get("status") != "ok":
            continue
        meta = item.get("metadata") or {}
        exclude = str(meta.get("audit_exclude_reason", "")).strip()
        if exclude and not include_excluded:
            continue
        cases: dict[str, float | None] = {}
        for case in item.get("case_scores", []):
            cases[str(case.get("case_id", ""))] = case.get("partial_score")
        runs.append(
            ModelRun(
                name=str(item.get("name", "")),
                result_dir=Path(str(item.get("result_dir", ""))),
                audit_group=str(meta.get("audit_group", suite.get("suite_key", "default"))),
                family=str(meta.get("family", "")),
                generation=str(meta.get("generation", "")),
                generation_rank=int(meta.get("generation_rank", 0)),
                arch=str(meta.get("arch", "")),
                original=bool(meta.get("original", False)),
                size_rank=int(meta.get("size_rank", 0)),
                precision_group=str(meta.get("precision_group", "")),
                precision_rank=int(meta.get("precision_rank", 0)),
                score=float(item.get("partial_weighted", 0.0)),
                strict_score=float(item.get("strict_weighted", 0.0)),
                partial_raw=float(item.get("partial_raw", 0.0)),
                strict_raw=int(item.get("strict_raw", 0)),
                cases=cases,
            )
        )
    return runs


def same_group(left: ModelRun, right: ModelRun) -> bool:
    return left.audit_group == right.audit_group


def expected_pairs(runs: list[ModelRun]) -> list[tuple[str, ModelRun, ModelRun]]:
    pairs: list[tuple[str, ModelRun, ModelRun]] = []
    dense_original = [r for r in runs if r.original and r.arch == "dense"]
    for bigger in dense_original:
        for smaller in dense_original:
            if not same_group(bigger, smaller):
                continue
            if bigger.family != smaller.family or bigger.generation != smaller.generation:
                continue
            if bigger.precision_rank != smaller.precision_rank:
                continue
            if bigger.size_rank > smaller.size_rank:
                pairs.append(("size_priority", bigger, smaller))

    for higher in runs:
        for lower in runs:
            if not same_group(higher, lower):
                continue
            if higher.precision_group and higher.precision_group == lower.precision_group:
                if higher.precision_rank > lower.precision_rank:
                    pairs.append(("precision_priority", higher, lower))

    originals = [r for r in runs if r.original]
    for newer in originals:
        for older in originals:
            if not same_group(newer, older):
                continue
            if newer.family != older.family or newer.arch != older.arch:
                continue
            if newer.size_rank != older.size_rank or newer.precision_rank != older.precision_rank:
                continue
            if newer.generation_rank > older.generation_rank:
                pairs.append(("generation_priority", newer, older))

    dense = [r for r in runs if r.original and r.arch == "dense"]
    moe = [r for r in runs if r.original and r.arch == "moe"]
    for d in dense:
        for m in moe:
            if not same_group(d, m):
                continue
            if d.family != m.family or d.generation != m.generation:
                continue
            if d.precision_rank != m.precision_rank:
                continue
            if d.size_rank >= m.size_rank:
                pairs.append(("dense_priority", d, m))

    seen: set[tuple[str, str, str]] = set()
    out: list[tuple[str, ModelRun, ModelRun]] = []
    for rule, stronger, weaker in pairs:
        key = (rule, stronger.name, weaker.name)
        if key in seen:
            continue
        seen.add(key)
        out.append((rule, stronger, weaker))
    return out


def total_order_issues(pairs: list[tuple[str, ModelRun, ModelRun]], tolerance: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for rule, stronger, weaker in pairs:
        if stronger.score >= weaker.score:
            continue
        row = {
            "rule": rule,
            "stronger": stronger.name,
            "weaker": weaker.name,
            "stronger_score": round(stronger.score, 3),
            "weaker_score": round(weaker.score, 3),
            "delta": round(stronger.score - weaker.score, 3),
        }
        if stronger.score + tolerance < weaker.score:
            issues.append(row)
        else:
            warnings.append(row)
    return issues, warnings


def case_order_issues(
    pairs: list[tuple[str, ModelRun, ModelRun]],
    case_meta: dict[str, dict[str, str]],
    epsilon: float,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for rule, stronger, weaker in pairs:
        shared = sorted(set(stronger.cases) & set(weaker.cases))
        for case_id in shared:
            info = case_meta.get(case_id, {})
            if info.get("audit_tier") == "foundational":
                continue
            sval = stronger.cases.get(case_id)
            wval = weaker.cases.get(case_id)
            if sval is None or wval is None:
                continue
            if float(sval) + epsilon >= float(wval):
                continue
            issues.append(
                {
                    "rule": rule,
                    "case_id": case_id,
                    "title": info.get("title", ""),
                    "audit_tier": info.get("audit_tier", "discriminative"),
                    "checker": info.get("checker", ""),
                    "stronger": stronger.name,
                    "weaker": weaker.name,
                    "stronger_case_score": round(float(sval), 3),
                    "weaker_case_score": round(float(wval), 3),
                    "delta": round(float(sval) - float(wval), 3),
                }
            )
    return issues


def case_signal_stats(runs: list[ModelRun], case_meta: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    case_ids = sorted({case_id for run in runs for case_id in run.cases})
    stats: list[dict[str, Any]] = []
    for case_id in case_ids:
        values = [float(run.cases[case_id]) for run in runs if run.cases.get(case_id) is not None]
        if not values:
            continue
        mean = statistics.fmean(values)
        stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
        info = case_meta.get(case_id, {})
        stats.append(
            {
                "case_id": case_id,
                "title": info.get("title", ""),
                "dimension_id": info.get("dimension_id", ""),
                "audit_tier": info.get("audit_tier", "discriminative"),
                "checker": info.get("checker", ""),
                "models": len(values),
                "mean_partial": round(mean, 4),
                "stdev_partial": round(stdev, 4),
                "min_partial": round(min(values), 4),
                "max_partial": round(max(values), 4),
            }
        )
    return stats


def precision_chain_gaps(runs: list[ModelRun]) -> list[dict[str, Any]]:
    by_group: dict[tuple[str, str], list[ModelRun]] = {}
    for run in runs:
        if not run.precision_group:
            continue
        by_group.setdefault((run.audit_group, run.precision_group), []).append(run)
    rows: list[dict[str, Any]] = []
    for (_audit_group, group), members in sorted(by_group.items()):
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda item: item.precision_rank)
        for lower, higher in zip(members, members[1:]):
            rows.append(
                {
                    "precision_group": group,
                    "lower": lower.name,
                    "higher": higher.name,
                    "lower_score": round(lower.score, 3),
                    "higher_score": round(higher.score, 3),
                    "gap": round(higher.score - lower.score, 3),
                }
            )
    return rows


def score_distribution(runs: list[ModelRun]) -> dict[str, Any]:
    if not runs:
        return {
            "top_score": None,
            "bottom_score": None,
            "spread": None,
            "mean_score": None,
            "models": [],
        }
    ordered = sorted(runs, key=lambda item: item.score, reverse=True)
    scores = [run.score for run in ordered]
    return {
        "top_score": round(scores[0], 3),
        "top_model": ordered[0].name,
        "bottom_score": round(scores[-1], 3),
        "bottom_model": ordered[-1].name,
        "spread": round(scores[0] - scores[-1], 3),
        "mean_score": round(statistics.fmean(scores), 3),
        "models": [
            {
                "name": run.name,
                "score": round(run.score, 3),
                "strict_score": round(run.strict_score, 3),
                "partial_raw": round(run.partial_raw, 3),
                "strict_raw": run.strict_raw,
            }
            for run in ordered
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ragent6 audit over deterministic partial scores.")
    parser.add_argument("--partial-json", type=Path, default=ROOT / "results" / "ragent6_scores.json")
    parser.add_argument("--suite", default="ragent6_0_2_0_en_US")
    parser.add_argument("--manifest", type=Path, default=ROOT / "manifests" / "ragent6.json")
    parser.add_argument("--score-tolerance", type=float, default=1.0)
    parser.add_argument("--case-epsilon", type=float, default=0.05)
    parser.add_argument("--low-signal-stdev", type=float, default=0.08)
    parser.add_argument("--easy-mean", type=float, default=0.95)
    parser.add_argument("--hard-mean", type=float, default=0.10)
    parser.add_argument("--include-excluded", action="store_true")
    args = parser.parse_args()

    suite = suite_payload(args.partial_json, args.suite)
    runs = load_runs(suite, include_excluded=args.include_excluded)
    case_meta = load_case_meta(args.manifest)
    pairs = expected_pairs(runs)
    total_issues, total_warnings = total_order_issues(pairs, args.score_tolerance)
    case_issues = case_order_issues(pairs, case_meta, args.case_epsilon)
    stats = case_signal_stats(runs, case_meta)
    discriminative = [item for item in stats if item.get("audit_tier") != "foundational"]
    saturated = [
        item for item in discriminative
        if float(item["mean_partial"]) >= args.easy_mean or float(item["mean_partial"]) <= args.hard_mean
    ]
    low_signal = [
        item for item in discriminative
        if float(item["stdev_partial"]) < args.low_signal_stdev
    ]
    precision_gaps = precision_chain_gaps(runs)
    weak_precision_gaps = [item for item in precision_gaps if 0 <= float(item["gap"]) < args.score_tolerance]
    inverted_precision_gaps = [item for item in precision_gaps if float(item["gap"]) < 0]
    hard_precision_inversions = [item for item in inverted_precision_gaps if float(item["gap"]) < -args.score_tolerance]

    signal_reasons: list[str] = []
    if saturated:
        signal_reasons.append("saturated discriminative cases detected")
    if low_signal:
        signal_reasons.append("low-signal discriminative cases detected")

    release_reasons: list[str] = []
    if total_issues:
        release_reasons.append("partial-score single-variable audit failed")
    if hard_precision_inversions:
        release_reasons.append("precision chain inverted beyond tolerance under partial score")

    payload = {
        "status": "pass" if not release_reasons else "fail",
        "audit_role": "diagnostic_only_not_optimization_target",
        "validity_priority": [
            "fairness",
            "signal_strength",
            "reproducibility",
            "audit_sanity",
        ],
        "release_gate_reasons": release_reasons,
        "signal_health_reasons": signal_reasons,
        "partial_json": str(args.partial_json),
        "suite": args.suite,
        "manifest": str(args.manifest),
        "checked_models": len(runs),
        "checked_cases": len(stats),
        "score_metric": "partial_weighted",
        "score_tolerance": args.score_tolerance,
        "case_epsilon": args.case_epsilon,
        "total_order_issues": total_issues,
        "total_order_warnings": total_warnings,
        "case_order_issues": case_issues,
        "score_distribution": score_distribution(runs),
        "case_signal": {
            "discriminative_cases": len(discriminative),
            "saturated_cases": len(saturated),
            "saturated_ratio": round(len(saturated) / len(discriminative), 4) if discriminative else 1.0,
            "low_signal_cases": len(low_signal),
            "low_signal_ratio": round(len(low_signal) / len(discriminative), 4) if discriminative else 1.0,
            "saturated_case_ids": [item["case_id"] for item in saturated],
            "low_signal_case_ids": [item["case_id"] for item in low_signal],
        },
        "precision_gaps": precision_gaps,
        "weak_precision_gaps": weak_precision_gaps,
        "inverted_precision_gaps": inverted_precision_gaps,
        "hard_precision_inversions": hard_precision_inversions,
        "case_stats": stats,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not release_reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def case_signal(payload: dict[str, Any]) -> dict[str, Any]:
    signal = payload.get("case_signal")
    if not isinstance(signal, dict):
        raise SystemExit(f"{payload.get('suite', '<unknown>')}: missing case_signal")
    return signal


def ratio(signal: dict[str, Any], key: str) -> float:
    value = signal.get(key)
    if not isinstance(value, (int, float)):
        raise SystemExit(f"case_signal missing numeric {key}")
    return float(value)


def count(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, list):
        return len(value)
    raise SystemExit(f"missing list {key}")


def score_distribution(payload: dict[str, Any]) -> dict[str, Any]:
    dist = payload.get("score_distribution")
    if not isinstance(dist, dict):
        raise SystemExit(f"{payload.get('suite', '<unknown>')}: missing score_distribution")
    return dist


def numeric_from(mapping: dict[str, Any], key: str) -> float:
    value = mapping.get(key)
    if not isinstance(value, (int, float)):
        raise SystemExit(f"score_distribution missing numeric {key}")
    return float(value)


def score_delta(candidate: dict[str, Any], baseline: dict[str, Any], key: str) -> int:
    return count(candidate, key) - count(baseline, key)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate a Ragent6 candidate audit against a baseline audit without treating audit ordering as the optimization target.",
    )
    parser.add_argument("--baseline-audit", type=Path, required=True)
    parser.add_argument("--candidate-audit", type=Path, required=True)
    parser.add_argument("--max-saturated-regression", type=float, default=0.0)
    parser.add_argument("--max-low-signal-regression", type=float, default=0.0)
    parser.add_argument("--max-top-score-increase", type=float, default=1.0)
    parser.add_argument("--min-spread-delta", type=float, default=-1.0)
    args = parser.parse_args()

    baseline = load_json(args.baseline_audit)
    candidate = load_json(args.candidate_audit)
    base_signal = case_signal(baseline)
    cand_signal = case_signal(candidate)
    base_dist = score_distribution(baseline)
    cand_dist = score_distribution(candidate)

    base_sat = ratio(base_signal, "saturated_ratio")
    cand_sat = ratio(cand_signal, "saturated_ratio")
    base_low = ratio(base_signal, "low_signal_ratio")
    cand_low = ratio(cand_signal, "low_signal_ratio")

    total_issue_delta = score_delta(candidate, baseline, "total_order_issues")
    hard_precision_delta = score_delta(candidate, baseline, "hard_precision_inversions")
    case_issue_delta = score_delta(candidate, baseline, "case_order_issues")
    top_score_delta = numeric_from(cand_dist, "top_score") - numeric_from(base_dist, "top_score")
    spread_delta = numeric_from(cand_dist, "spread") - numeric_from(base_dist, "spread")

    failures: list[str] = []
    warnings: list[str] = []

    saturated_delta = cand_sat - base_sat
    low_signal_delta = cand_low - base_low
    if saturated_delta > args.max_saturated_regression:
        failures.append(
            f"saturated ratio regressed from {base_sat:.4f} to {cand_sat:.4f}"
        )
    if low_signal_delta > args.max_low_signal_regression:
        failures.append(
            f"low-signal ratio regressed from {base_low:.4f} to {cand_low:.4f}"
        )
    if top_score_delta > args.max_top_score_increase:
        message = f"top score increased from {numeric_from(base_dist, 'top_score'):.3f} to {numeric_from(cand_dist, 'top_score'):.3f}"
        if spread_delta > 0 and saturated_delta <= 0 and low_signal_delta <= 0:
            warnings.append(message)
        else:
            failures.append(message)
    if spread_delta < args.min_spread_delta:
        failures.append(
            f"score spread shrank from {numeric_from(base_dist, 'spread'):.3f} to {numeric_from(cand_dist, 'spread'):.3f}"
        )

    if candidate.get("release_gate_reasons"):
        failures.append("candidate has release gate failures")
    if total_issue_delta > 0:
        warnings.append(f"total order issues increased by {total_issue_delta}")
    if hard_precision_delta > 0:
        warnings.append(f"hard precision inversions increased by {hard_precision_delta}")
    if case_issue_delta > 0:
        warnings.append(f"case-level diagnostic inversions increased by {case_issue_delta}")

    if (
        total_issue_delta < 0 or hard_precision_delta < 0 or case_issue_delta < 0
    ) and (saturated_delta > 0 or low_signal_delta > 0):
        failures.append("audit ordering improved while signal health regressed")

    payload = {
        "status": "pass" if not failures else "fail",
        "gate_role": "candidate_signal_gate_not_audit_optimizer",
        "baseline": {
            "suite": baseline.get("suite"),
            "status": baseline.get("status"),
            "saturated_ratio": round(base_sat, 4),
            "low_signal_ratio": round(base_low, 4),
            "total_order_issues": count(baseline, "total_order_issues"),
            "hard_precision_inversions": count(baseline, "hard_precision_inversions"),
            "case_order_issues": count(baseline, "case_order_issues"),
            "top_score": numeric_from(base_dist, "top_score"),
            "spread": numeric_from(base_dist, "spread"),
        },
        "candidate": {
            "suite": candidate.get("suite"),
            "status": candidate.get("status"),
            "saturated_ratio": round(cand_sat, 4),
            "low_signal_ratio": round(cand_low, 4),
            "total_order_issues": count(candidate, "total_order_issues"),
            "hard_precision_inversions": count(candidate, "hard_precision_inversions"),
            "case_order_issues": count(candidate, "case_order_issues"),
            "top_score": numeric_from(cand_dist, "top_score"),
            "spread": numeric_from(cand_dist, "spread"),
        },
        "deltas": {
            "saturated_ratio": round(saturated_delta, 4),
            "low_signal_ratio": round(low_signal_delta, 4),
            "total_order_issues": total_issue_delta,
            "hard_precision_inversions": hard_precision_delta,
            "case_order_issues": case_issue_delta,
            "top_score": round(top_score_delta, 3),
            "spread": round(spread_delta, 3),
        },
        "failures": failures,
        "warnings": warnings,
        "interpretation": (
            "A candidate cannot be promoted by improving expected-order audit metrics "
            "if it reduces signal health. Audit is diagnostic; signal and fairness are primary."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

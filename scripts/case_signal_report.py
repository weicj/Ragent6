#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suite_payload(partial_json: Path, suite_key: str | None) -> dict[str, Any]:
    data = load_json(partial_json)
    suites = data.get("suites") or []
    if not suites:
        raise SystemExit(f"no suites in {partial_json}")
    if suite_key is None:
        if len(suites) != 1:
            raise SystemExit("multiple suites found; pass --suite")
        return suites[0]
    for suite in suites:
        if suite.get("suite_key") == suite_key:
            return suite
    raise SystemExit(f"suite {suite_key!r} not found")


def classify(values: list[float], stdev: float, easy_mean: float, hard_mean: float, low_signal_stdev: float) -> list[str]:
    tags: list[str] = []
    if not values:
        return ["missing"]
    mean = statistics.fmean(values)
    unique = len({round(value, 4) for value in values})
    if unique == 1:
        tags.append("all_same")
    if mean >= easy_mean:
        tags.append("near_all_pass")
    if mean <= hard_mean:
        tags.append("near_all_fail")
    if stdev < low_signal_stdev:
        tags.append("low_variance")
    if 0.35 <= mean <= 0.75 and stdev >= low_signal_stdev:
        tags.append("useful_spread")
    return tags or ["ok"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank Ragent6 cases by signal quality from a partial-score panel.")
    parser.add_argument("--partial-json", type=Path, required=True)
    parser.add_argument("--suite")
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--low-signal-stdev", type=float, default=0.08)
    parser.add_argument("--easy-mean", type=float, default=0.95)
    parser.add_argument("--hard-mean", type=float, default=0.10)
    args = parser.parse_args()

    suite = suite_payload(args.partial_json, args.suite)
    cases: dict[str, dict[str, Any]] = {}
    for model in suite.get("models", []):
        if model.get("status") != "ok":
            continue
        model_name = str(model.get("name", ""))
        for item in model.get("case_scores", []):
            case_id = str(item.get("case_id", ""))
            if not case_id:
                continue
            row = cases.setdefault(
                case_id,
                {
                    "case_id": case_id,
                    "title": item.get("title", ""),
                    "dimension": item.get("dimension", ""),
                    "checker": item.get("checker", ""),
                    "scores": [],
                    "strict": Counter(),
                    "reasons": Counter(),
                    "models": [],
                },
            )
            score = item.get("partial_score")
            if isinstance(score, (int, float)):
                row["scores"].append(float(score))
            row["strict"][str(item.get("strict_status", "unknown"))] += 1
            row["reasons"][str(item.get("reason_code", "unknown"))] += 1
            row["models"].append(
                {
                    "model": model_name,
                    "partial_score": score,
                    "strict_status": item.get("strict_status"),
                    "reason_code": item.get("reason_code"),
                }
            )

    rows: list[dict[str, Any]] = []
    for row in cases.values():
        values = row["scores"]
        mean = statistics.fmean(values) if values else 0.0
        stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
        tags = classify(values, stdev, args.easy_mean, args.hard_mean, args.low_signal_stdev)
        if "near_all_pass" in tags or "near_all_fail" in tags or "all_same" in tags:
            priority = "replace_or_redesign"
        elif "low_variance" in tags:
            priority = "inspect"
        elif "useful_spread" in tags:
            priority = "keep"
        else:
            priority = "monitor"
        rows.append(
            {
                "case_id": row["case_id"],
                "title": row["title"],
                "dimension": row["dimension"],
                "checker": row["checker"],
                "models": len(values),
                "mean": round(mean, 4),
                "stdev": round(stdev, 4),
                "min": round(min(values), 4) if values else None,
                "max": round(max(values), 4) if values else None,
                "unique_scores": len({round(value, 4) for value in values}),
                "tags": tags,
                "priority": priority,
                "strict_counts": dict(row["strict"]),
                "top_reasons": dict(row["reasons"].most_common(5)),
            }
        )

    priority_order = {
        "replace_or_redesign": 0,
        "inspect": 1,
        "monitor": 2,
        "keep": 3,
    }
    rows.sort(
        key=lambda item: (
            priority_order.get(str(item["priority"]), 9),
            float(item["stdev"]),
            -abs(float(item["mean"]) - 0.5),
            str(item["dimension"]),
            str(item["case_id"]),
        )
    )

    payload = {
        "suite_key": suite.get("suite_key"),
        "suite_version": suite.get("suite_version"),
        "source": str(args.partial_json),
        "thresholds": {
            "low_signal_stdev": args.low_signal_stdev,
            "easy_mean": args.easy_mean,
            "hard_mean": args.hard_mean,
        },
        "summary": {
            "cases": len(rows),
            "replace_or_redesign": sum(1 for row in rows if row["priority"] == "replace_or_redesign"),
            "inspect": sum(1 for row in rows if row["priority"] == "inspect"),
            "keep": sum(1 for row in rows if row["priority"] == "keep"),
        },
        "cases": rows,
    }

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Ragent6 Case Signal Report",
            "",
            f"- Suite: `{payload['suite_key']}`",
            f"- Source: `{args.partial_json}`",
            f"- Replace/redesign: `{payload['summary']['replace_or_redesign']}`",
            f"- Inspect: `{payload['summary']['inspect']}`",
            f"- Keep: `{payload['summary']['keep']}`",
            "",
            "| Priority | Case | Dim | Mean | Stdev | Tags | Top Reasons |",
            "|---|---|---|---:|---:|---|---|",
        ]
        for row in rows:
            if row["priority"] == "keep":
                continue
            reasons = ", ".join(f"{k}:{v}" for k, v in row["top_reasons"].items())
            lines.append(
                f"| {row['priority']} | {row['case_id']} {row['title']} | {row['dimension']} | "
                f"{row['mean']:.4f} | {row['stdev']:.4f} | {', '.join(row['tags'])} | {reasons} |"
            )
        args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragent6.runner import evaluate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--adapter", default="mock")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if not args.manifest and not args.case:
        parser.error("either --manifest or --case is required")
    if args.manifest and args.case:
        parser.error("use either --manifest or --case, not both")

    manifest_path = Path(args.manifest) if args.manifest else None
    if manifest_path is None:
        synthetic_manifest = Path(args.out).with_suffix(".manifest.json")
        synthetic_manifest.parent.mkdir(parents=True, exist_ok=True)
        synthetic_manifest.write_text(
            (
                __import__("json").dumps(
                    {
                        "suite_name": "ragent6-ad-hoc",
                        "suite_version": "1.1.0",
                        "cases": args.case,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            ),
            encoding="utf-8",
        )
        manifest_path = synthetic_manifest

    summary = evaluate(manifest_path, args.adapter, Path(args.out))
    print(
        f"{summary.suite_name} {summary.suite_version}: "
        f"{summary.total_score}/{summary.total_possible} "
        f"(invalid={summary.invalid_cases}) -> {summary.out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Run FPS α probe analyses (frame overlap + statepoint coverage).

Usage
-----
  cd models/fps_alpha_probe
  python run_probe.py
  python run_probe.py --retentions 0.10 0.20
"""

from __future__ import annotations

import argparse
from pathlib import Path

from overlap_across_alpha import run as run_overlap
from probe_data import (
    DEFAULT_SAMPLING_RESULTS,
    DEFAULT_STATEPOINTS_JSON,
    build_frame_statepoint_table,
    load_fps_selections,
    load_statepoints,
)
from statepoint_coverage import run as run_coverage

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sampling-results",
        type=Path,
        default=DEFAULT_SAMPLING_RESULTS,
    )
    parser.add_argument(
        "--statepoints-json",
        type=Path,
        default=DEFAULT_STATEPOINTS_JSON,
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--retentions",
        type=float,
        nargs="+",
        default=[0.01, 0.10, 0.20],
    )
    parser.add_argument("--overlap-only", action="store_true")
    parser.add_argument("--coverage-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    retentions = tuple(args.retentions)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    selections = load_fps_selections(
        args.sampling_results, retention_fractions=retentions
    )
    print(
        f"Loaded {len(selections)} FPS selections "
        f"({len(retentions)} retention level(s))"
    )

    if not args.coverage_only:
        summary = run_overlap(
            selections, args.output_dir, retention_fractions=retentions
        )
        print(f"Overlap: {len(summary)} pairwise rows")

    if not args.overlap_only:
        statepoints = load_statepoints(args.statepoints_json)
        frame_table = build_frame_statepoint_table(statepoints)
        cov_dir = args.output_dir / "coverage"
        cov_dir.mkdir(parents=True, exist_ok=True)
        frame_table.to_csv(cov_dir / "frame_statepoint_map.csv", index=False)
        counts_long, metrics_df = run_coverage(
            selections,
            frame_table,
            args.output_dir,
            retention_fractions=retentions,
        )
        print(f"Coverage: {len(counts_long)} count rows, {len(metrics_df)} metric rows")

    print(f"Done. Outputs under {args.output_dir}")


if __name__ == "__main__":
    main()

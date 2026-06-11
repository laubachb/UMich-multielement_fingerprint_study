#!/usr/bin/env python3
"""HEA convergence diagnostics: overlap and composition coverage vs retention."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from composition_coverage import counts_for_selection, uniformity_metrics
from probe_data import (
    ALPHAS,
    COMPOSITION_ORDER,
    DEFAULT_CONVERGENCE_RESULTS,
    alpha_label,
    build_frame_composition_table,
    load_fps_selections,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def jaccard(a: set[int], b: set[int]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def jaccard_alpha0_vs_alpha1(selections: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (retention, rep), group in selections.groupby(
        ["retention_fraction", "replicate"], sort=True
    ):
        sets = {r.fps_alpha: set(r.frame_ids) for r in group.itertuples(index=False)}
        if 0.0 not in sets or 1.0 not in sets:
            continue
        rows.append(
            {
                "retention_fraction": retention,
                "retention_pct": int(round(retention * 100)),
                "replicate": rep,
                "jaccard_0_vs_1": jaccard(sets[0.0], sets[1.0]),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return (
        df.groupby(["retention_fraction", "retention_pct"])["jaccard_0_vs_1"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .sort_values("retention_pct")
    )


def uniformity_vs_retention(
    selections: pd.DataFrame,
    frame_table: pd.DataFrame,
) -> pd.DataFrame:
    n_cases = len(COMPOSITION_ORDER)
    rows: list[dict] = []
    for row in selections.itertuples(index=False):
        counts = counts_for_selection(row.frame_ids, frame_table)
        metrics = uniformity_metrics(counts, n_cases)
        rows.append(
            {
                "fps_alpha": row.fps_alpha,
                "retention_fraction": row.retention_fraction,
                "retention_pct": row.retention_pct,
                "replicate": row.replicate,
                **metrics,
            }
        )
    df = pd.DataFrame(rows)
    agg = (
        df.groupby(["fps_alpha", "retention_fraction", "retention_pct"])[
            ["coverage_fraction", "entropy_norm", "cv_count", "n_cases_covered"]
        ]
        .agg(["mean", "std"])
        .reset_index()
        .sort_values(["fps_alpha", "retention_pct"])
    )
    agg.columns = [f"{a}_{b}" if b else a for a, b in agg.columns.to_flat_index()]
    return agg


def run(
    selections: pd.DataFrame,
    frame_table: pd.DataFrame,
    output_dir: Path,
) -> None:
    conv_dir = output_dir / "convergence"
    conv_dir.mkdir(parents=True, exist_ok=True)

    jacc = jaccard_alpha0_vs_alpha1(selections)
    jacc.to_csv(conv_dir / "jaccard_alpha0_vs_alpha1.csv", index=False)

    uni = uniformity_vs_retention(selections, frame_table)
    uni.to_csv(conv_dir / "uniformity_vs_retention.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampling-results", type=Path, default=DEFAULT_CONVERGENCE_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selections = load_fps_selections(args.sampling_results)
    frame_table = build_frame_composition_table()
    run(selections, frame_table, args.output_dir)
    print(f"Wrote HEA convergence tables to {args.output_dir}")


if __name__ == "__main__":
    main()
